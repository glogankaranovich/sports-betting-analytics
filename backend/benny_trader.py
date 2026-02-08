"""
Benny - Autonomous Sports Betting Trader

Benny is an AI agent that makes virtual bets using ensemble model predictions
and AI reasoning. Tracks a $100/week virtual bankroll and learns over time.
"""
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE", "carpool-bets-v2-dev"))


class BennyTrader:
    """Autonomous trading agent for sports betting"""

    WEEKLY_BUDGET = Decimal("100.00")
    MIN_CONFIDENCE = 0.65  # Only bet on high confidence predictions
    MAX_BET_PERCENTAGE = 0.20  # Max 20% of bankroll per bet

    def __init__(self):
        self.bankroll = self._get_current_bankroll()
        self.week_start = self._get_week_start()

    def _get_week_start(self) -> str:
        """Get start of current week (Monday)"""
        today = datetime.utcnow()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        return monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    def _get_current_bankroll(self) -> Decimal:
        """Get current bankroll, reset weekly"""
        week_start = self._get_week_start()

        # Check if we need to reset for new week
        response = table.get_item(Key={"PK": "BENNY", "SK": "BANKROLL"})

        if "Item" in response:
            item = response["Item"]
            last_reset = item.get("last_reset", "")

            # Reset if new week
            if last_reset < week_start:
                self._reset_bankroll()
                return self.WEEKLY_BUDGET
            else:
                return Decimal(str(item.get("amount", self.WEEKLY_BUDGET)))
        else:
            # First time - initialize
            self._reset_bankroll()
            return self.WEEKLY_BUDGET

    def _reset_bankroll(self):
        """Reset bankroll for new week"""
        week_start = self._get_week_start()

        table.put_item(
            Item={
                "PK": "BENNY",
                "SK": "BANKROLL",
                "amount": self.WEEKLY_BUDGET,
                "last_reset": week_start,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

    def _update_bankroll(self, amount: Decimal):
        """Update bankroll amount"""
        self.bankroll = amount

        table.put_item(
            Item={
                "PK": "BENNY",
                "SK": "BANKROLL",
                "amount": amount,
                "last_reset": self.week_start,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

    def analyze_games(self) -> List[Dict[str, Any]]:
        """Analyze upcoming games and identify betting opportunities"""
        # Get games in next 24 hours
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)

        # Query ensemble predictions
        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq("MODEL#ensemble")
            & Key("GSI1SK").between(now.isoformat(), tomorrow.isoformat()),
            FilterExpression="attribute_not_exists(outcome)",  # Only upcoming games
            Limit=50,
        )

        predictions = response.get("Items", [])

        # Filter high confidence predictions
        opportunities = []
        for pred in predictions:
            confidence = float(pred.get("confidence", 0))
            if confidence >= self.MIN_CONFIDENCE:
                opportunities.append(
                    {
                        "game_id": pred.get("game_id"),
                        "sport": pred.get("sport"),
                        "home_team": pred.get("home_team"),
                        "away_team": pred.get("away_team"),
                        "prediction": pred.get("prediction"),
                        "confidence": confidence,
                        "commence_time": pred.get("commence_time"),
                        "market_key": pred.get("market_key", "h2h"),
                    }
                )

        return opportunities

    def calculate_bet_size(self, confidence: float) -> Decimal:
        """Calculate bet size using Kelly Criterion (simplified)"""
        # Kelly Criterion: f = (bp - q) / b
        # where b = odds, p = probability of winning, q = probability of losing
        # Simplified: bet more on higher confidence, max 20% of bankroll

        kelly_fraction = Decimal(str((confidence - 0.5) * 2))  # 0 to 1 scale
        max_bet = self.bankroll * Decimal(str(self.MAX_BET_PERCENTAGE))

        bet_size = self.bankroll * kelly_fraction * Decimal("0.5")  # Half Kelly
        bet_size = min(bet_size, max_bet)  # Cap at max
        bet_size = max(bet_size, Decimal("5.00"))  # Minimum $5 bet

        return bet_size.quantize(Decimal("0.01"))

    def place_bet(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Place a virtual bet"""
        bet_size = self.calculate_bet_size(opportunity["confidence"])

        # Check if we have enough bankroll
        if bet_size > self.bankroll:
            return {"success": False, "reason": "Insufficient bankroll"}

        bet_id = f"BET#{datetime.utcnow().isoformat()}#{opportunity['game_id']}"

        bet = {
            "PK": "BENNY",
            "SK": bet_id,
            "GSI1PK": "BENNY#BETS",
            "GSI1SK": opportunity["commence_time"],
            "bet_id": bet_id,
            "game_id": opportunity["game_id"],
            "sport": opportunity["sport"],
            "home_team": opportunity["home_team"],
            "away_team": opportunity["away_team"],
            "prediction": opportunity["prediction"],
            "confidence": Decimal(str(opportunity["confidence"])),
            "bet_amount": bet_size,
            "market_key": opportunity["market_key"],
            "commence_time": opportunity["commence_time"],
            "placed_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "bankroll_before": self.bankroll,
        }

        # Store bet
        table.put_item(Item=bet)

        # Update bankroll
        new_bankroll = self.bankroll - bet_size
        self._update_bankroll(new_bankroll)

        return {
            "success": True,
            "bet_id": bet_id,
            "bet_amount": float(bet_size),
            "remaining_bankroll": float(new_bankroll),
        }

    def run_daily_analysis(self) -> Dict[str, Any]:
        """Run daily analysis and place bets"""
        opportunities = self.analyze_games()

        bets_placed = []
        total_bet = Decimal("0")

        for opp in opportunities:
            # Don't bet if bankroll too low
            if self.bankroll < Decimal("10.00"):
                break

            result = self.place_bet(opp)
            if result["success"]:
                bets_placed.append(result)
                total_bet += Decimal(str(result["bet_amount"]))

        return {
            "opportunities_found": len(opportunities),
            "bets_placed": len(bets_placed),
            "total_bet_amount": float(total_bet),
            "remaining_bankroll": float(self.bankroll),
            "bets": bets_placed,
        }

    @staticmethod
    def get_dashboard_data() -> Dict[str, Any]:
        """Get dashboard data for Benny"""
        # Get current bankroll
        response = table.get_item(Key={"PK": "BENNY", "SK": "BANKROLL"})
        bankroll_item = response.get("Item", {})
        current_bankroll = float(bankroll_item.get("amount", 100.0))

        # Get recent bets
        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq("BENNY#BETS"),
            ScanIndexForward=False,
            Limit=20,
        )
        recent_bets = response.get("Items", [])

        # Calculate stats
        total_bets = len(recent_bets)
        pending_bets = [b for b in recent_bets if b.get("status") == "pending"]
        settled_bets = [b for b in recent_bets if b.get("status") in ["won", "lost"]]
        won_bets = [b for b in settled_bets if b.get("status") == "won"]

        win_rate = len(won_bets) / len(settled_bets) if settled_bets else 0

        total_wagered = sum(float(b.get("bet_amount", 0)) for b in settled_bets)
        total_returned = sum(float(b.get("payout", 0)) for b in won_bets)
        roi = (
            ((total_returned - total_wagered) / total_wagered)
            if total_wagered > 0
            else 0
        )

        return {
            "current_bankroll": current_bankroll,
            "weekly_budget": 100.0,
            "total_bets": total_bets,
            "pending_bets": len(pending_bets),
            "win_rate": round(win_rate, 3),
            "roi": round(roi, 3),
            "recent_bets": [
                {
                    "bet_id": b.get("bet_id"),
                    "game": f"{b.get('away_team')} @ {b.get('home_team')}",
                    "prediction": b.get("prediction"),
                    "confidence": float(b.get("confidence", 0)),
                    "bet_amount": float(b.get("bet_amount", 0)),
                    "status": b.get("status"),
                    "payout": float(b.get("payout", 0)),
                    "placed_at": b.get("placed_at"),
                }
                for b in recent_bets[:10]
            ],
        }


def lambda_handler(event, context):
    """Lambda handler for Benny trader"""
    try:
        # Check if this is a scheduled run or API call
        if "source" in event and event["source"] == "aws.events":
            # Scheduled daily run
            trader = BennyTrader()
            result = trader.run_daily_analysis()

            return {
                "statusCode": 200,
                "body": json.dumps(result, default=str),
            }
        else:
            # API call for dashboard
            dashboard = BennyTrader.get_dashboard_data()

            return {
                "statusCode": 200,
                "body": json.dumps(dashboard, default=str),
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
