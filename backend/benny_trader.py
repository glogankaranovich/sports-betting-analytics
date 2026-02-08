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
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
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
        response = table.get_item(Key={"pk": "BENNY", "sk": "BANKROLL"})

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
                "pk": "BENNY",
                "sk": "BANKROLL",
                "amount": self.WEEKLY_BUDGET,
                "last_reset": week_start,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

    def _update_bankroll(self, amount: Decimal):
        """Update bankroll amount and store history"""
        self.bankroll = amount
        timestamp = datetime.utcnow().isoformat()

        # Update current bankroll
        table.put_item(
            Item={
                "pk": "BENNY",
                "sk": "BANKROLL",
                "amount": amount,
                "last_reset": self.week_start,
                "updated_at": timestamp,
            }
        )

        # Store history snapshot
        table.put_item(
            Item={
                "pk": "BENNY",
                "sk": f"BANKROLL#{timestamp}",
                "amount": amount,
                "updated_at": timestamp,
            }
        )

    def analyze_games(self) -> List[Dict[str, Any]]:
        """Analyze upcoming games and identify betting opportunities"""
        # Get games in next 24 hours
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)

        # Query ensemble predictions from all sports
        # GSI1PK format: ANALYSIS#{sport}#{bookmaker}#{model}#game
        opportunities = []

        for sport in [
            "basketball_nba",
            "americanfootball_nfl",
            "baseball_mlb",
            "icehockey_nhl",
            "soccer_epl",
        ]:
            response = table.query(
                IndexName="AnalysisTimeGSI",
                KeyConditionExpression=Key("analysis_time_pk").eq(
                    f"ANALYSIS#{sport}#fanduel#ensemble#game"
                )
                & Key("commence_time").between(now.isoformat(), tomorrow.isoformat()),
                FilterExpression="attribute_exists(latest) AND latest = :true",
                ExpressionAttributeValues={":true": True},
                Limit=20,
            )

            predictions = response.get("Items", [])

            # Filter high confidence predictions
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

    def get_ai_reasoning(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI reasoning and confidence adjustment from Claude"""
        try:
            # Fetch recent team stats
            home_stats = self._get_team_stats(
                opportunity["home_team"], opportunity["sport"]
            )
            away_stats = self._get_team_stats(
                opportunity["away_team"], opportunity["sport"]
            )

            # Build prompt
            prompt = f"""You are Benny, an expert sports betting analyst. Analyze this betting opportunity:

Game: {opportunity['away_team']} @ {opportunity['home_team']}
Sport: {opportunity['sport']}
Ensemble Model Prediction: {opportunity['prediction']}
Model Confidence: {opportunity['confidence']:.1%}

Home Team Recent Stats: {json.dumps(home_stats, indent=2) if home_stats else 'No data'}
Away Team Recent Stats: {json.dumps(away_stats, indent=2) if away_stats else 'No data'}

Provide:
1. Your analysis (2-3 sentences max)
2. Confidence adjustment (-0.1 to +0.1) based on context the model might miss
3. Key factors influencing your decision

Format as JSON:
{{"reasoning": "...", "confidence_adjustment": 0.0, "key_factors": ["factor1", "factor2"]}}"""

            response = bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            content = result["content"][0]["text"]

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            ai_response = json.loads(content)

            return {
                "reasoning": ai_response.get("reasoning", ""),
                "confidence_adjustment": float(
                    ai_response.get("confidence_adjustment", 0)
                ),
                "key_factors": ai_response.get("key_factors", []),
                "adjusted_confidence": min(
                    1.0,
                    max(
                        0.0,
                        opportunity["confidence"]
                        + ai_response.get("confidence_adjustment", 0),
                    ),
                ),
            }
        except Exception as e:
            print(f"AI reasoning failed: {e}")
            return {
                "reasoning": "AI analysis unavailable",
                "confidence_adjustment": 0,
                "key_factors": [],
                "adjusted_confidence": opportunity["confidence"],
            }

    def _get_team_stats(self, team: str, sport: str) -> Dict[str, Any]:
        """Fetch recent team stats from DynamoDB"""
        try:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(f"TEAM#{sport}#{team}")
                & Key("SK").begins_with("STATS#"),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else {}
        except Exception:
            return {}

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
        """Place a virtual bet with AI reasoning"""
        # Get AI reasoning and adjusted confidence
        ai_analysis = self.get_ai_reasoning(opportunity)
        adjusted_confidence = ai_analysis["adjusted_confidence"]

        # Use adjusted confidence for bet sizing
        bet_size = self.calculate_bet_size(adjusted_confidence)

        # Check if we have enough bankroll
        if bet_size > self.bankroll:
            return {"success": False, "reason": "Insufficient bankroll"}

        bet_id = f"BET#{datetime.utcnow().isoformat()}#{opportunity['game_id']}"

        bet = {
            "pk": "BENNY",
            "sk": bet_id,
            "GSI1PK": "BENNY#BETS",
            "GSI1SK": opportunity["commence_time"],
            "bet_id": bet_id,
            "game_id": opportunity["game_id"],
            "sport": opportunity["sport"],
            "home_team": opportunity["home_team"],
            "away_team": opportunity["away_team"],
            "prediction": opportunity["prediction"],
            "ensemble_confidence": Decimal(str(opportunity["confidence"])),
            "ai_confidence_adjustment": Decimal(
                str(ai_analysis["confidence_adjustment"])
            ),
            "final_confidence": Decimal(str(adjusted_confidence)),
            "ai_reasoning": ai_analysis["reasoning"],
            "ai_key_factors": ai_analysis["key_factors"],
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
            "ai_reasoning": ai_analysis["reasoning"],
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
        response = table.get_item(Key={"pk": "BENNY", "sk": "BANKROLL"})
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

        # Performance by sport
        sports_performance = {}
        for bet in settled_bets:
            sport = bet.get("sport", "unknown")
            if sport not in sports_performance:
                sports_performance[sport] = {
                    "wins": 0,
                    "losses": 0,
                    "wagered": 0,
                    "returned": 0,
                }

            if bet.get("status") == "won":
                sports_performance[sport]["wins"] += 1
                sports_performance[sport]["returned"] += float(bet.get("payout", 0))
            else:
                sports_performance[sport]["losses"] += 1
            sports_performance[sport]["wagered"] += float(bet.get("bet_amount", 0))

        # Confidence calibration
        confidence_buckets = {"60-70%": [], "70-80%": [], "80-90%": [], "90-100%": []}
        for bet in settled_bets:
            conf = float(bet.get("final_confidence", bet.get("confidence", 0)))
            won = bet.get("status") == "won"
            if 0.6 <= conf < 0.7:
                confidence_buckets["60-70%"].append(won)
            elif 0.7 <= conf < 0.8:
                confidence_buckets["70-80%"].append(won)
            elif 0.8 <= conf < 0.9:
                confidence_buckets["80-90%"].append(won)
            elif conf >= 0.9:
                confidence_buckets["90-100%"].append(won)

        confidence_accuracy = {}
        for bucket, results in confidence_buckets.items():
            if results:
                confidence_accuracy[bucket] = {
                    "actual_win_rate": round(sum(results) / len(results), 3),
                    "count": len(results),
                }

        # Best and worst bets
        best_bet = max(
            settled_bets,
            key=lambda b: float(b.get("payout", 0)) - float(b.get("bet_amount", 0)),
            default=None,
        )
        worst_bet = min(
            settled_bets,
            key=lambda b: float(b.get("payout", 0)) - float(b.get("bet_amount", 0)),
            default=None,
        )

        # AI adjustment impact
        ai_adjusted_bets = [
            b for b in settled_bets if b.get("ai_confidence_adjustment")
        ]
        if ai_adjusted_bets:
            ai_wins = sum(1 for b in ai_adjusted_bets if b.get("status") == "won")
            ai_win_rate = ai_wins / len(ai_adjusted_bets)
        else:
            ai_win_rate = None

        # Bankroll history (get all bankroll updates)
        bankroll_response = table.query(
            KeyConditionExpression=Key("PK").eq("BENNY")
            & Key("SK").begins_with("BANKROLL#"),
            ScanIndexForward=True,
            Limit=50,
        )
        bankroll_history = [
            {
                "timestamp": item.get("updated_at"),
                "amount": float(item.get("amount", 0)),
            }
            for item in bankroll_response.get("Items", [])
        ]

        return {
            "current_bankroll": current_bankroll,
            "weekly_budget": 100.0,
            "total_bets": total_bets,
            "pending_bets": len(pending_bets),
            "win_rate": round(win_rate, 3),
            "roi": round(roi, 3),
            "sports_performance": {
                sport: {
                    "record": f"{stats['wins']}-{stats['losses']}",
                    "win_rate": round(
                        stats["wins"] / (stats["wins"] + stats["losses"]), 3
                    )
                    if (stats["wins"] + stats["losses"]) > 0
                    else 0,
                    "roi": round(
                        (stats["returned"] - stats["wagered"]) / stats["wagered"], 3
                    )
                    if stats["wagered"] > 0
                    else 0,
                }
                for sport, stats in sports_performance.items()
            },
            "confidence_accuracy": confidence_accuracy,
            "best_bet": {
                "game": f"{best_bet.get('away_team')} @ {best_bet.get('home_team')}",
                "profit": float(best_bet.get("payout", 0))
                - float(best_bet.get("bet_amount", 0)),
            }
            if best_bet
            else None,
            "worst_bet": {
                "game": f"{worst_bet.get('away_team')} @ {worst_bet.get('home_team')}",
                "loss": float(worst_bet.get("bet_amount", 0)),
            }
            if worst_bet
            else None,
            "ai_impact": {
                "win_rate": round(ai_win_rate, 3) if ai_win_rate is not None else None,
                "bets_count": len(ai_adjusted_bets),
            },
            "bankroll_history": bankroll_history,
            "recent_bets": [
                {
                    "bet_id": b.get("bet_id"),
                    "game": f"{b.get('away_team')} @ {b.get('home_team')}",
                    "prediction": b.get("prediction"),
                    "ensemble_confidence": float(
                        b.get("ensemble_confidence", b.get("confidence", 0))
                    ),
                    "final_confidence": float(
                        b.get("final_confidence", b.get("confidence", 0))
                    ),
                    "ai_reasoning": b.get("ai_reasoning", ""),
                    "ai_key_factors": b.get("ai_key_factors", []),
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
