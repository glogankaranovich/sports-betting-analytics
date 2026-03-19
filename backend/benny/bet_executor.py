"""Bet execution and notification handling"""
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any


class BetExecutor:
    """Handles bet placement and notifications"""

    def __init__(self, table, sqs_client, notification_queue_url=None, version="v1"):
        self.table = table
        self.sqs = sqs_client
        self.notification_queue_url = notification_queue_url
        self.version = version

    def place_bet(
        self,
        opportunity: Dict[str, Any],
        bet_size: Decimal,
        bankroll: Decimal,
        features: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Place a bet and store in DynamoDB"""
        bet_id = f"{datetime.utcnow().isoformat()}#{opportunity['game_id']}"

        is_prop = "player" in opportunity
        pk = {"v1": "BENNY", "v3": "BENNY_V3"}.get(self.version, "BENNY")

        bet = {
            "pk": pk,
            "sk": f"BET#{bet_id}",
            "GSI1PK": f"{pk}#BETS",
            "GSI1SK": opportunity["commence_time"],
            "bet_id": bet_id,
            "game_id": opportunity["game_id"],
            "sport": opportunity["sport"],
            "prediction": opportunity["prediction"],
            "confidence": Decimal(str(opportunity["confidence"])),
            "ai_reasoning": opportunity["reasoning"],
            "ai_key_factors": opportunity["key_factors"],
            "bet_amount": bet_size,
            "market_key": opportunity["market_key"],
            "commence_time": opportunity["commence_time"],
            "placed_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "bankroll_before": bankroll,
            "odds": Decimal(str(opportunity.get("odds", 0)))
            if opportunity.get("odds")
            else None,
            "version": self.version,
        }

        # Add features for v2 (learning version)
        if features and self.version == "v2":
            bet["features"] = features

        if is_prop:
            bet["player_name"] = opportunity["player"]
            bet["line"] = opportunity.get("line")
        else:
            bet["home_team"] = opportunity["home_team"]
            bet["away_team"] = opportunity["away_team"]

        self.table.put_item(Item=bet)

        # Store analysis record (only for game bets, not props)
        if not is_prop:
            analysis_record = {
                "pk": f"ANALYSIS#{opportunity['sport']}#{opportunity['game_id']}#fanduel",
                "sk": "benny#game#LATEST",
                "model": "benny",
                "analysis_type": "game",
                "sport": opportunity["sport"],
                "bookmaker": "fanduel",
                "game_id": opportunity["game_id"],
                "home_team": opportunity["home_team"],
                "away_team": opportunity["away_team"],
                "prediction": opportunity["prediction"],
                "confidence": Decimal(str(opportunity["confidence"])),
                "reasoning": opportunity["reasoning"],
                "market_key": opportunity["market_key"],
                "commence_time": opportunity["commence_time"],
                "created_at": datetime.utcnow().isoformat(),
                "latest": True,
            }
            self.table.put_item(Item=analysis_record)

        # Send notification
        self._send_notification(bet, opportunity)

        return {
            "success": True,
            "bet_id": bet_id,
            "bet_amount": float(bet_size),
            "ai_reasoning": opportunity["reasoning"],
        }

    def place_parlay(
        self, parlay: Dict[str, Any], bet_size: Decimal, bankroll: Decimal
    ) -> Dict[str, Any]:
        """Place a parlay bet and store in DynamoDB."""
        bet_id = f"{datetime.utcnow().isoformat()}#PARLAY"
        pk = {"v1": "BENNY", "v3": "BENNY_V3"}.get(self.version, "BENNY")

        # Use earliest leg commence_time for GSI sorting
        commence_times = [
            l["commence_time"] for l in parlay["legs"] if l.get("commence_time")
        ]
        earliest = (
            min(commence_times) if commence_times else datetime.utcnow().isoformat()
        )

        # Convert legs for DynamoDB (Decimal-safe)
        legs_for_db = []
        for leg in parlay["legs"]:
            legs_for_db.append(
                {
                    "game_id": leg["game_id"],
                    "sport": leg["sport"],
                    "player": leg.get("player"),
                    "market": leg.get("market"),
                    "prediction": leg["prediction"],
                    "confidence": Decimal(str(leg["confidence"])),
                    "odds": Decimal(str(leg["odds"])),
                    "commence_time": leg.get("commence_time"),
                    "status": "pending",
                }
            )

        bet = {
            "pk": pk,
            "sk": f"BET#{bet_id}",
            "GSI1PK": f"{pk}#BETS",
            "GSI1SK": earliest,
            "bet_id": bet_id,
            "bet_type": "parlay",
            "sport": "mixed",
            "market_key": "parlay",
            "num_legs": parlay["num_legs"],
            "legs": legs_for_db,
            "combined_confidence": Decimal(str(parlay["combined_confidence"])),
            "combined_decimal_odds": Decimal(str(parlay["combined_decimal_odds"])),
            "combined_american_odds": parlay["combined_american_odds"],
            "bet_amount": bet_size,
            "placed_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "bankroll_before": bankroll,
            "version": self.version,
        }

        self.table.put_item(Item=bet)

        # Send notification
        self._send_parlay_notification(parlay, bet_size, bankroll)

        return {
            "success": True,
            "bet_id": bet_id,
            "bet_amount": float(bet_size),
            "bet_type": "parlay",
            "num_legs": parlay["num_legs"],
        }

    def _send_notification(self, bet: Dict, opportunity: Dict):
        """Send bet notification to SQS"""
        environment = os.environ.get("ENVIRONMENT", "dev")
        if environment != "dev" or not self.notification_queue_url:
            return

        is_prop = "player" in opportunity
        game_desc = (
            f"{opportunity['player']} {opportunity['market']}"
            if is_prop
            else f"{opportunity['away_team']} @ {opportunity['home_team']}"
        )

        message = {
            "type": "bet_placed",
            "data": {
                "version": self.version,
                "sport": opportunity["sport"],
                "game": game_desc,
                "market_key": opportunity["market_key"],
                "pick": opportunity["prediction"],
                "odds": float(opportunity.get("odds", 0)),
                "confidence": float(opportunity["confidence"]),
                "stake": float(bet["bet_amount"]),
                "bankroll_percentage": float(
                    bet["bet_amount"] / bet["bankroll_before"]
                ),
                "expected_roi": float(opportunity.get("expected_value", 0)),
                "reasoning": opportunity["reasoning"],
            },
        }

        try:
            self.sqs.send_message(
                QueueUrl=self.notification_queue_url, MessageBody=json.dumps(message)
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")

    def _send_parlay_notification(self, parlay: Dict, bet_size: Decimal, bankroll: Decimal):
        """Send parlay placement notification to SQS"""
        environment = os.environ.get("ENVIRONMENT", "dev")
        if environment != "dev" or not self.notification_queue_url:
            return

        legs_desc = []
        for leg in parlay["legs"]:
            player = leg.get("player", "")
            market = leg.get("market", "")
            pred = leg.get("prediction", "")
            legs_desc.append(f"{player} {market} {pred}".strip())

        message = {
            "type": "bet_placed",
            "data": {
                "version": self.version,
                "sport": parlay["legs"][0].get("sport", "Unknown"),
                "game": f"🎲 {parlay['num_legs']}-Leg Parlay",
                "market_key": "parlay",
                "pick": " + ".join(legs_desc),
                "odds": parlay.get("combined_american_odds", 0),
                "confidence": parlay.get("combined_confidence", 0),
                "stake": float(bet_size),
                "bankroll_percentage": float(bet_size / bankroll) if bankroll else 0,
                "expected_roi": 0,
                "reasoning": f"{parlay['num_legs']}-leg parlay at {parlay.get('combined_american_odds', '')} odds",
            },
        }

        try:
            self.sqs.send_message(
                QueueUrl=self.notification_queue_url, MessageBody=json.dumps(message)
            )
        except Exception as e:
            print(f"Failed to send parlay notification: {e}")
