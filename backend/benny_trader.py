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

from constants import SUPPORTED_SPORTS
from benny.position_manager import PositionManager
from benny.bankroll_manager import BankrollManager
from benny.learning_engine import LearningEngine
from benny.opportunity_analyzer import OpportunityAnalyzer
from benny.feature_extractor import FeatureExtractor
from benny.outcome_analyzer import OutcomeAnalyzer
from benny.threshold_optimizer import ThresholdOptimizer
from benny.bet_executor import BetExecutor
from benny.parlay_engine import ParlayEngine

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
# Default table for module-level usage (supports both env var names)
table = dynamodb.Table(
    os.environ.get(
        "BETS_TABLE", os.environ.get("DYNAMODB_TABLE", "carpool-bets-v2-dev")
    )
)


class BennyTrader:
    """Autonomous trading agent for sports betting"""

    WEEKLY_BUDGET = Decimal("100.00")
    BASE_MIN_CONFIDENCE = 0.70
    MIN_EV = 0.05
    TARGET_ROI = 0.15
    MAX_BET_PERCENTAGE = 0.20
    MIN_SAMPLE_SIZE = 30

    def __init__(self, table_name=None, version="v1"):
        if table_name:
            self.table = dynamodb.Table(table_name)
        else:
            self.table = table

        self.version = version
        self.pk = "BENNY" if version == "v1" else "BENNY_V2"

        # Initialize composition classes
        self.bankroll_manager = BankrollManager(self.table, self.pk)
        self.learning_engine = LearningEngine(self.table, self.pk)
        self.opportunity_analyzer = OpportunityAnalyzer(self.learning_engine)

        sqs = boto3.client("sqs")
        notification_queue_url = os.environ.get("NOTIFICATION_QUEUE_URL")
        self.bet_executor = BetExecutor(
            self.table, sqs, notification_queue_url, version
        )
        self.parlay_engine = ParlayEngine()

        self.position_manager = PositionManager(self.table, bedrock)

        # Caches built during analysis, shared across methods
        self.game_teams = {}  # game_id -> {home_team, away_team}
        self.player_teams = {}  # player_name -> team_name

        # Delegate to managers
        self.bankroll = self.bankroll_manager.bankroll
        self.week_start = self.bankroll_manager.week_start
        self.learning_params = self.learning_engine.params

    def _get_adaptive_threshold(self, sport: str, market: str) -> float:
        """Get confidence threshold based on historical performance"""
        return self.learning_engine.get_adaptive_threshold(sport, market)

    def _get_performance_warnings(self, current_sport: str = None) -> str:
        """Generate performance warnings for AI prompt"""
        return self.learning_engine.get_performance_warnings(current_sport)

    def _acquire_lock(self) -> bool:
        return "YOUR TRACK RECORD: Insufficient data to assess performance by category"

    def _acquire_lock(self) -> bool:
        """Acquire distributed lock for Benny execution. Returns True if acquired."""
        try:
            self.table.put_item(
                Item={
                    "pk": self.pk,
                    "sk": "LOCK",
                    "locked_at": datetime.utcnow().isoformat(),
                    "ttl": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
            return True
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return False

    def _release_lock(self):
        """Release distributed lock"""
        print("Releasing lock...")
        try:
            self.table.delete_item(Key={"pk": self.pk, "sk": "LOCK"})
            print("Lock released successfully")
        except Exception as e:
            print(f"Failed to release lock: {e}")

    def _get_learning_parameters(self) -> Dict[str, Any]:
        """Get Benny's learned parameters from DynamoDB"""
        try:
            response = self.table.get_item(
                Key={"pk": "BENNY#LEARNING", "sk": "PARAMETERS"}
            )
            if "Item" in response:
                return response["Item"]

            # Initialize default parameters
            default_params = {
                "pk": "BENNY#LEARNING",
                "sk": "PARAMETERS",
                "min_confidence_adjustment": Decimal(
                    "0.0"
                ),  # Added to BASE_MIN_CONFIDENCE (reference only)
                "kelly_fraction": Decimal(
                    "0.5"
                ),  # Half Kelly for more aggressive sizing
                "target_roi": Decimal("0.15"),  # Target 15% ROI
                "performance_by_sport": {},
                "performance_by_market": {},
                "last_updated": datetime.utcnow().isoformat(),
            }
            self.table.put_item(Item=default_params)
            return default_params
        except Exception as e:
            print(f"Error loading learning parameters: {e}")
            return {
                "min_confidence_adjustment": 0.0,
                "kelly_fraction": 0.5,
                "target_roi": 0.15,
                "performance_by_sport": {},
                "performance_by_market": {},
            }

    def _get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get Benny's historical performance stats for learning"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND sk > :sk",
                ExpressionAttributeValues={":pk": "BENNY", ":sk": f"BET#{cutoff}"},
            )
            bets = [
                b
                for b in response.get("Items", [])
                if b.get("status") in ["won", "lost"]
            ]

            if not bets:
                return {"message": "No settled bets yet"}

            # Overall stats
            won = [b for b in bets if b["status"] == "won"]
            total_wagered = sum(Decimal(str(b.get("stake", 0))) for b in bets)
            total_profit = sum(Decimal(str(b.get("profit", 0))) for b in bets)

            stats = {
                "overall": {
                    "win_rate": f"{len(won)/len(bets):.1%}",
                    "roi": f"{(total_profit/total_wagered*100):.1f}%"
                    if total_wagered > 0
                    else "0%",
                    "total_bets": len(bets),
                },
                "by_sport": {},
                "by_market": {},
                "notable": {"best": None, "worst": None},
            }

            # By sport
            for sport in set(b.get("sport", "unknown") for b in bets):
                sport_bets = [b for b in bets if b.get("sport") == sport]
                if sport_bets:
                    sport_won = [b for b in sport_bets if b["status"] == "won"]
                    stats["by_sport"][
                        sport
                    ] = f"{len(sport_won)}/{len(sport_bets)} ({len(sport_won)/len(sport_bets):.1%})"

            # By market type
            for market in set(b.get("market_type", "unknown") for b in bets):
                market_bets = [b for b in bets if b.get("market_type") == market]
                if market_bets:
                    market_won = [b for b in market_bets if b["status"] == "won"]
                    stats["by_market"][
                        market
                    ] = f"{len(market_won)}/{len(market_bets)} ({len(market_won)/len(market_bets):.1%})"

            # Notable bets
            if bets:
                stats["notable"]["best"] = max(
                    bets, key=lambda b: Decimal(str(b.get("profit", 0)))
                )
                stats["notable"]["worst"] = min(
                    bets, key=lambda b: Decimal(str(b.get("profit", 0)))
                )

            return stats
        except Exception as e:
            print(f"Error fetching performance stats: {e}")
            return {"message": "Error loading stats"}

    def _get_what_works_analysis(self) -> str:
        """Identify patterns in winning bets"""
        perf_by_sport = self.learning_params.get("performance_by_sport", {})
        perf_by_market = self.learning_params.get("performance_by_market", {})

        insights = []

        for sport, stats in perf_by_sport.items():
            if stats["total"] >= 5:
                wr = stats["wins"] / stats["total"]
                if wr > 0.55:
                    insights.append(
                        f"✓ {sport}: {wr:.1%} win rate ({stats['wins']}/{stats['total']})"
                    )

        for market, stats in perf_by_market.items():
            if stats["total"] >= 5:
                wr = stats["wins"] / stats["total"]
                if wr > 0.55:
                    insights.append(
                        f"✓ {market}: {wr:.1%} win rate ({stats['wins']}/{stats['total']})"
                    )

        return (
            "\n".join(insights)
            if insights
            else "Not enough data yet (need 5+ bets per category)"
        )

    def _get_what_fails_analysis(self) -> str:
        """Identify patterns in losing bets"""
        perf_by_sport = self.learning_params.get("performance_by_sport", {})
        perf_by_market = self.learning_params.get("performance_by_market", {})

        warnings = []

        for sport, stats in perf_by_sport.items():
            if stats["total"] >= 5:
                wr = stats["wins"] / stats["total"]
                if wr < 0.45:
                    warnings.append(
                        f"✗ {sport}: {wr:.1%} win rate ({stats['wins']}/{stats['total']}) - be very selective, require higher confidence"
                    )

        for market, stats in perf_by_market.items():
            if stats["total"] >= 5:
                wr = stats["wins"] / stats["total"]
                if wr < 0.45:
                    warnings.append(
                        f"✗ {market}: {wr:.1%} win rate ({stats['wins']}/{stats['total']}) - be very selective, require higher confidence"
                    )

        return "\n".join(warnings) if warnings else "No clear failure patterns yet"

    def _analyze_recent_mistakes(self, limit: int = 10) -> str:
        """Analyze recent losing bets to identify patterns"""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                ScanIndexForward=False,
                Limit=200,  # Get more bets, then filter
            )

            all_bets = response.get("Items", [])
            losses = [b for b in all_bets if b.get("status") == "lost"][:limit]

            if not losses:
                return "No recent losses to analyze"

            patterns = []

            # Check if overconfident
            high_conf_losses = [
                b for b in losses if float(b.get("confidence", 0)) > 0.75
            ]
            if len(high_conf_losses) > len(losses) * 0.5:
                patterns.append(
                    f"⚠️ {len(high_conf_losses)}/{len(losses)} losses were high confidence (>75%) - may be overconfident"
                )

            # Check if betting on underdogs too much
            underdog_losses = [b for b in losses if float(b.get("odds", 0)) > 0]
            if len(underdog_losses) > len(losses) * 0.6:
                patterns.append(
                    f"⚠️ {len(underdog_losses)}/{len(losses)} losses were underdogs (+odds) - may be chasing value"
                )

            # Check specific sports
            sport_losses = {}
            for bet in losses:
                sport = bet.get("sport", "unknown")
                sport_losses[sport] = sport_losses.get(sport, 0) + 1

            for sport, count in sport_losses.items():
                if count >= 3:
                    patterns.append(f"⚠️ {count} recent losses in {sport}")

            return (
                "\n".join(patterns)
                if patterns
                else "No clear patterns in recent losses"
            )
        except Exception as e:
            print(f"Error analyzing mistakes: {e}")
            return "Error analyzing recent mistakes"

    def _get_winning_examples(self, sport: str, limit: int = 3) -> str:
        """Get recent winning bets for the specific sport being analyzed"""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                ScanIndexForward=False,
                Limit=200,  # Get more bets, then filter
            )

            all_bets = response.get("Items", [])
            wins = [
                b
                for b in all_bets
                if b.get("status") == "won" and b.get("sport") == sport
            ][:limit]

            if not wins:
                return f"No winning bets yet for {sport}"

            examples = []
            for bet in wins:
                profit = float(bet.get("profit", 0))
                confidence = float(bet.get("confidence", 0))
                reasoning = bet.get("ai_reasoning", "N/A")[:100]
                examples.append(
                    f"✓ {bet.get('prediction')} ({confidence:.0%} conf) - Won ${profit:.2f}\n  Reasoning: {reasoning}"
                )

            return "\n\n".join(examples)
        except Exception as e:
            print(f"Error getting winning examples: {e}")
            return f"Error loading winning examples for {sport}"

    def _extract_winning_factors(self) -> str:
        """Extract which key_factors correlate with wins vs losses"""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                FilterExpression="#status IN (:won, :lost)",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":won": "won", ":lost": "lost"},
                Limit=100,
            )

            bets = response.get("Items", [])
            if len(bets) < 10:
                return "Not enough settled bets to analyze factors (need 10+)"

            factor_performance = {}

            for bet in bets:
                won = bet.get("status") == "won"
                factors = bet.get("ai_key_factors", [])

                for factor in factors:
                    if factor not in factor_performance:
                        factor_performance[factor] = {"wins": 0, "total": 0}
                    factor_performance[factor]["total"] += 1
                    if won:
                        factor_performance[factor]["wins"] += 1

            # Calculate win rate per factor (min 3 occurrences)
            insights = []
            for factor, stats in sorted(
                factor_performance.items(),
                key=lambda x: x[1]["wins"] / max(x[1]["total"], 1),
                reverse=True,
            ):
                if stats["total"] >= 3:
                    wr = stats["wins"] / stats["total"]
                    if wr >= 0.60:
                        insights.append(
                            f"✓ {factor}: {wr:.0%} ({stats['wins']}/{stats['total']})"
                        )
                    elif wr <= 0.40:
                        insights.append(
                            f"✗ {factor}: {wr:.0%} ({stats['wins']}/{stats['total']})"
                        )

            return (
                "\n".join(insights)
                if insights
                else "No clear factor patterns yet (need factors with 3+ occurrences)"
            )
        except Exception as e:
            print(f"Error extracting winning factors: {e}")
            return "Error analyzing winning factors"

    def _get_model_benchmarks(self, sport: str) -> str:
        """Get how other models perform on this sport"""
        try:
            from constants import SYSTEM_MODELS

            benchmarks = []

            for model in SYSTEM_MODELS:
                response = self.table.query(
                    IndexName="VerifiedAnalysisGSI",
                    KeyConditionExpression=Key("verified_analysis_pk").eq(
                        f"VERIFIED#{model}#{sport}#game"
                    ),
                    ScanIndexForward=False,
                    Limit=50,
                )

                preds = response.get("Items", [])
                if len(preds) >= 10:
                    correct = sum(1 for p in preds if p.get("analysis_correct"))
                    accuracy = correct / len(preds)
                    benchmarks.append(
                        f"{model}: {accuracy:.1%} ({correct}/{len(preds)})"
                    )

            return (
                "\n".join(benchmarks)
                if benchmarks
                else f"No benchmark data for {sport}"
            )
        except Exception as e:
            print(f"Error getting model benchmarks: {e}")
            return f"Error loading benchmarks for {sport}"

    def _normalize_prediction(self, prediction: str) -> str:
        """Normalize prediction for agreement checking.

        Spreads: "Team +5.0" -> "Team spread"
        Totals: "Over 220.5" -> "Over"
        Moneyline: "Team" -> "Team"
        """
        pred = prediction.strip()

        # Handle spreads (e.g., "Patriots +5.0 @ draftkings" or "Patriots +5.0")
        if "+" in pred or "-" in pred:
            # Extract team name before the +/- sign
            parts = pred.split()
            team_parts = []
            for part in parts:
                if "+" in part or "-" in part or "@" in part:
                    break
                team_parts.append(part)
            team = " ".join(team_parts)
            return f"{team} spread"

        # Handle totals (e.g., "Over 220.5" or "Under 45.5")
        if pred.startswith("Over") or pred.startswith("Under"):
            return pred.split()[0]  # Just "Over" or "Under"

        # Moneyline - return as-is (team name)
        return pred

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

        self.table.put_item(
            Item={
                "pk": "BENNY",
                "sk": "BANKROLL",
                "amount": self.WEEKLY_BUDGET,
                "last_reset": week_start,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

    def _update_bankroll(self, amount: Decimal):
        """Update bankroll amount"""
        self.bankroll_manager.update_bankroll(amount)
        self.bankroll = amount

    def _get_learning_parameters(self) -> Dict[str, Any]:
        # Store history snapshot
        self.table.put_item(
            Item={
                "pk": "BENNY",
                "sk": f"BANKROLL#{timestamp}",
                "amount": amount,
                "updated_at": timestamp,
            }
        )

    def _get_total_deposits(self) -> Decimal:
        """Get total deposits made (excluding initial bankroll)"""
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={":pk": "BENNY", ":sk": "DEPOSIT#"},
            )
            deposits = response.get("Items", [])
            return sum(Decimal(str(d.get("amount", 0))) for d in deposits)
        except:
            return Decimal("0")

    def _add_deposit(self, amount: Decimal, reason: str = "manual"):
        """Add deposit to bankroll and track separately"""
        timestamp = datetime.utcnow().isoformat()

        # Record deposit
        self.table.put_item(
            Item={
                "pk": "BENNY",
                "sk": f"DEPOSIT#{timestamp}",
                "amount": amount,
                "reason": reason,
                "created_at": timestamp,
            }
        )

        # Update bankroll
        new_bankroll = self.bankroll + amount
        self._update_bankroll(new_bankroll)
        print(f"Added ${amount} deposit ({reason}). New bankroll: ${new_bankroll}")

    def _check_auto_deposit_conditions(self) -> bool:
        """Check if auto-deposit should trigger"""
        MIN_BANKROLL_THRESHOLD = Decimal("50.00")
        MIN_WIN_RATE = 0.50
        DEPOSIT_COOLDOWN_DAYS = 7

        # Check bankroll threshold
        if self.bankroll >= MIN_BANKROLL_THRESHOLD:
            return False

        # Check recent win rate
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={":pk": "BENNY", ":sk": "BET#"},
                ScanIndexForward=False,
                Limit=50,
            )

            bets = response.get("Items", [])
            settled_bets = [b for b in bets if b.get("status") in ["won", "lost"]]

            if len(settled_bets) < 10:  # Need at least 10 bets
                return False

            won_bets = [b for b in settled_bets if b.get("status") == "won"]
            win_rate = len(won_bets) / len(settled_bets)

            if win_rate < MIN_WIN_RATE:
                print(f"Win rate too low ({win_rate:.1%}) for auto-deposit")
                return False
        except:
            return False

        # Check cooldown period
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={":pk": "BENNY", ":sk": "DEPOSIT#"},
                ScanIndexForward=False,
                Limit=1,
            )

            deposits = response.get("Items", [])
            if deposits:
                last_deposit = deposits[0]
                last_deposit_time = datetime.fromisoformat(last_deposit["created_at"])
                days_since = (datetime.utcnow() - last_deposit_time).days

                if days_since < DEPOSIT_COOLDOWN_DAYS:
                    print(f"Cooldown active: {days_since} days since last deposit")
                    return False
        except:
            pass

        return True

    def _auto_deposit_if_needed(self):
        """Automatically deposit funds if conditions are met"""
        AUTO_DEPOSIT_AMOUNT = Decimal("100.00")

        if self._check_auto_deposit_conditions():
            print(
                f"Auto-deposit triggered: bankroll=${self.bankroll}, adding ${AUTO_DEPOSIT_AMOUNT}"
            )
            self._add_deposit(AUTO_DEPOSIT_AMOUNT, reason="auto-refill")
            return True
        return False

    # _get_top_models removed - dead code, never called

    def analyze_games(self) -> List[Dict[str, Any]]:
        """Analyze upcoming games independently using raw data and AI"""
        now = datetime.utcnow()
        three_days_out = now + timedelta(days=3)

        opportunities = []

        for sport in SUPPORTED_SPORTS:
            # Get upcoming games with odds for all markets
            response = self.table.query(
                IndexName="ActiveBetsIndexV2",
                KeyConditionExpression=Key("active_bet_pk").eq(f"GAME#{sport}")
                & Key("commence_time").between(
                    now.isoformat(), three_days_out.isoformat()
                ),
                FilterExpression="attribute_exists(latest) AND latest = :true",
                ExpressionAttributeValues={":true": True},
                Limit=200,
            )

            print(
                f"Checking {sport}: found {len(response.get('Items', []))} odds items"
            )

            games = {}
            for item in response.get("Items", []):
                game_id = item.get("pk", "")[5:]  # Remove GAME# prefix
                if game_id not in games:
                    games[game_id] = {
                        "game_id": game_id,
                        "sport": sport,
                        "home_team": item.get("home_team"),
                        "away_team": item.get("away_team"),
                        "commence_time": item.get("commence_time"),
                        "h2h_odds": [],
                        "spread_odds": [],
                        "total_odds": [],
                    }
                    self.game_teams[game_id] = {"home_team": item.get("home_team"), "away_team": item.get("away_team")}

                market_key = item.get("market_key")
                outcomes = item.get("outcomes", [])

                if market_key == "h2h" and len(outcomes) >= 2:
                    odds_entry = {
                        "bookmaker": item.get("bookmaker"),
                        "home_price": None,
                        "away_price": None,
                        "draw_price": None,
                    }

                    home_team = item.get("home_team")
                    away_team = item.get("away_team")

                    for outcome in outcomes:
                        outcome_name = outcome.get("name", "").lower()
                        if outcome.get("name") == home_team:
                            odds_entry["home_price"] = outcome.get("price")
                        elif outcome.get("name") == away_team:
                            odds_entry["away_price"] = outcome.get("price")
                        elif "draw" in outcome_name or "tie" in outcome_name:
                            odds_entry["draw_price"] = outcome.get("price")

                    if odds_entry["home_price"] and odds_entry["away_price"]:
                        games[game_id]["h2h_odds"].append(odds_entry)

                elif market_key == "spreads" and len(outcomes) >= 2:
                    home_team = item.get("home_team")
                    away_team = item.get("away_team")

                    odds_entry = {
                        "bookmaker": item.get("bookmaker"),
                        "home_point": None,
                        "home_price": None,
                        "away_point": None,
                        "away_price": None,
                    }

                    for outcome in outcomes:
                        if outcome.get("name") == home_team:
                            odds_entry["home_point"] = outcome.get("point")
                            odds_entry["home_price"] = outcome.get("price")
                        elif outcome.get("name") == away_team:
                            odds_entry["away_point"] = outcome.get("point")
                            odds_entry["away_price"] = outcome.get("price")

                    if odds_entry["home_price"] and odds_entry["away_price"]:
                        games[game_id]["spread_odds"].append(odds_entry)

                elif market_key == "totals" and len(outcomes) >= 2:
                    odds_entry = {
                        "bookmaker": item.get("bookmaker"),
                        "over_point": None,
                        "over_price": None,
                        "under_point": None,
                        "under_price": None,
                    }

                    for outcome in outcomes:
                        outcome_name = outcome.get("name", "").lower()
                        if "over" in outcome_name:
                            odds_entry["over_point"] = outcome.get("point")
                            odds_entry["over_price"] = outcome.get("price")
                        elif "under" in outcome_name:
                            odds_entry["under_point"] = outcome.get("point")
                            odds_entry["under_price"] = outcome.get("price")

                    if odds_entry["over_price"] and odds_entry["under_price"]:
                        games[game_id]["total_odds"].append(odds_entry)

            print(f"  Parsed {len(games)} unique games for {sport}")

            # Analyze each game with AI
            for game_id, game_data in games.items():
                if len(game_data["h2h_odds"]) < 2:
                    print(
                        f"  Skipping {game_data['home_team']} vs {game_data['away_team']}: insufficient odds"
                    )
                    continue

                print(
                    f"  Analyzing {game_data['home_team']} vs {game_data['away_team']}"
                )

                # Gather essential data
                home_stats = self._get_team_stats(game_data["home_team"], sport)
                away_stats = self._get_team_stats(game_data["away_team"], sport)
                home_injuries = self._get_team_injuries(game_data["home_team"], sport)
                away_injuries = self._get_team_injuries(game_data["away_team"], sport)
                h2h_history = self._get_head_to_head(
                    game_data["home_team"], game_data["away_team"], sport
                )
                home_form = self._get_recent_form(game_data["home_team"], sport)
                away_form = self._get_recent_form(game_data["away_team"], sport)
                home_news = self._get_team_news_sentiment(game_data["home_team"], sport)
                away_news = self._get_team_news_sentiment(game_data["away_team"], sport)
                home_elo = self._get_elo_rating(game_data["home_team"], sport)
                away_elo = self._get_elo_rating(game_data["away_team"], sport)
                print(
                    f"Elo ratings: {game_data['home_team']} {home_elo:.0f} vs {game_data['away_team']} {away_elo:.0f}"
                )
                home_adjusted = self._get_adjusted_metrics(
                    game_data["home_team"], sport
                )
                away_adjusted = self._get_adjusted_metrics(
                    game_data["away_team"], sport
                )
                weather = self._get_weather_data(game_id)
                fatigue = self._get_fatigue_data(game_id)

                # Calculate average odds for all markets
                avg_h2h = {
                    "home": sum(o["home_price"] for o in game_data["h2h_odds"])
                    / len(game_data["h2h_odds"]),
                    "away": sum(o["away_price"] for o in game_data["h2h_odds"])
                    / len(game_data["h2h_odds"]),
                }
                draw_prices = [
                    o["draw_price"]
                    for o in game_data["h2h_odds"]
                    if o.get("draw_price")
                ]
                if draw_prices:
                    avg_h2h["draw"] = sum(draw_prices) / len(draw_prices)

                avg_spread = None
                if game_data["spread_odds"]:
                    avg_spread = {
                        "home_point": sum(
                            o["home_point"] for o in game_data["spread_odds"]
                        )
                        / len(game_data["spread_odds"]),
                        "home_price": sum(
                            o["home_price"] for o in game_data["spread_odds"]
                        )
                        / len(game_data["spread_odds"]),
                        "away_point": sum(
                            o["away_point"] for o in game_data["spread_odds"]
                        )
                        / len(game_data["spread_odds"]),
                        "away_price": sum(
                            o["away_price"] for o in game_data["spread_odds"]
                        )
                        / len(game_data["spread_odds"]),
                    }

                avg_total = None
                if game_data["total_odds"]:
                    avg_total = {
                        "point": sum(o["over_point"] for o in game_data["total_odds"])
                        / len(game_data["total_odds"]),
                        "over_price": sum(
                            o["over_price"] for o in game_data["total_odds"]
                        )
                        / len(game_data["total_odds"]),
                        "under_price": sum(
                            o["under_price"] for o in game_data["total_odds"]
                        )
                        / len(game_data["total_odds"]),
                    }

                # Let AI analyze all markets
                analysis = self._ai_analyze_game(
                    game_data,
                    home_stats,
                    away_stats,
                    home_injuries,
                    away_injuries,
                    h2h_history,
                    home_form,
                    away_form,
                    home_news,
                    away_news,
                    home_elo,
                    away_elo,
                    home_adjusted,
                    away_adjusted,
                    weather,
                    fatigue,
                    avg_spread,
                    avg_total,
                )

                if analysis:
                    # Create opportunities for each market prediction
                    for market_type, prediction_data in analysis.items():
                        # Skip if AI didn't provide prediction for this market
                        if not prediction_data or not isinstance(prediction_data, dict):
                            continue

                        if market_type == "h2h":
                            predicted_team = prediction_data["prediction"].lower()
                            if game_data["home_team"].lower() in predicted_team:
                                odds = avg_h2h["home"]
                            elif game_data["away_team"].lower() in predicted_team:
                                odds = avg_h2h["away"]
                            elif "draw" in predicted_team and "draw" in avg_h2h:
                                odds = avg_h2h["draw"]
                            else:
                                continue

                        elif market_type == "spread" and avg_spread:
                            if (
                                game_data["home_team"].lower()
                                in prediction_data["prediction"].lower()
                            ):
                                odds = avg_spread["home_price"]
                            else:
                                odds = avg_spread["away_price"]

                        elif market_type == "total" and avg_total:
                            if "over" in prediction_data["prediction"].lower():
                                odds = avg_total["over_price"]
                            else:
                                odds = avg_total["under_price"]

                        else:
                            continue

                        # Calculate EV
                        odds = float(odds)
                        if odds > 0:
                            payout_multiplier = 1 + (odds / 100)
                        else:
                            payout_multiplier = 1 + (100 / abs(odds))

                        expected_value = (
                            float(prediction_data["confidence"]) * payout_multiplier
                        ) - 1
                        print(f"  {market_type.upper()} EV: {expected_value:.3f}")

                        opportunity = {
                            "game_id": game_id,
                            "sport": sport,
                            "home_team": game_data["home_team"],
                            "away_team": game_data["away_team"],
                            "prediction": prediction_data["prediction"],
                            "confidence": prediction_data["confidence"],
                            "reasoning": prediction_data["reasoning"],
                            "key_factors": prediction_data["key_factors"],
                            "commence_time": game_data["commence_time"],
                            "market_key": market_type,
                            "odds": odds,
                            "expected_value": expected_value,
                        }

                        # Extract features for v2
                        if self.version == "v2":
                            features = FeatureExtractor.extract_features(
                                game_data=game_data,
                                home_elo=home_elo,
                                away_elo=away_elo,
                                fatigue=fatigue,
                                home_injuries=home_injuries,
                                away_injuries=away_injuries,
                                home_form=home_form,
                                away_form=away_form,
                                weather=weather,
                                h2h_history=h2h_history,
                                odds=odds,
                                market_key=market_type,
                                prediction=prediction_data["prediction"],
                            )
                            opportunity["features"] = features

                        opportunities.append(opportunity)

        return opportunities

    def analyze_props(self) -> List[Dict[str, Any]]:
        """Analyze upcoming player props using AI"""
        now = datetime.utcnow()
        three_days_out = now + timedelta(days=3)
        opportunities = []

        # Only analyze props for sports that support them
        props_sports = [
            s
            for s in SUPPORTED_SPORTS
            if s
            in [
                "basketball_nba",
                "americanfootball_nfl",
                "baseball_mlb",
                "icehockey_nhl",
                "basketball_ncaab",
            ]
        ]

        for sport in props_sports:
            # Get upcoming props
            response = self.table.query(
                IndexName="ActiveBetsIndexV2",
                KeyConditionExpression=Key("active_bet_pk").eq(f"PROP#{sport}")
                & Key("commence_time").between(
                    now.isoformat(), three_days_out.isoformat()
                ),
                FilterExpression="attribute_exists(latest) AND latest = :true",
                ExpressionAttributeValues={":true": True},
                Limit=100,
            )

            print(
                f"Checking {sport} props: found {len(response.get('Items', []))} items"
            )

            # Group props by player and market
            props_by_player = {}
            for item in response.get("Items", []):
                player = item.get("player_name")
                market = item.get("market_key")
                if not player or not market:
                    continue

                key = f"{player}#{market}"
                if key not in props_by_player:
                    game_id = item.get("event_id")
                    props_by_player[key] = {
                        "player": player,
                        "market": market,
                        "sport": sport,
                        "game_id": game_id,
                        "team": self._get_player_team(player, sport),
                        "opponent": self._get_player_opponent(player, sport, game_id),
                        "commence_time": item.get("commence_time"),
                        "line": item.get("point"),
                        "odds": [],
                    }

                # Each item is a single outcome (Over or Under)
                props_by_player[key]["odds"].append(
                    {
                        "bookmaker": item.get("bookmaker"),
                        "side": item.get("outcome"),  # Over/Under
                        "price": item.get("price"),
                        "point": item.get("point"),
                    }
                )

            print(f"  Parsed {len(props_by_player)} unique props for {sport}")

            # Analyze top props (limit to prevent timeout)
            for prop_key, prop_data in list(props_by_player.items())[:20]:
                if len(prop_data["odds"]) < 2:
                    continue

                print(f"  Analyzing {prop_data['player']} {prop_data['market']}")

                # Get player data
                player_stats = self._get_player_stats(prop_data["player"], sport)
                player_trends = self._get_player_trends(
                    prop_data["player"], sport, prop_data["market"]
                )
                matchup_data = self._get_player_matchup(
                    prop_data["player"], prop_data["opponent"], sport
                )

                if player_stats:
                    print(f"    Player stats: {list(player_stats.keys())[:5]}")
                else:
                    print(f"    No player stats found")

                # AI analysis
                analysis = self._ai_analyze_prop(
                    prop_data, player_stats, player_trends, matchup_data
                )

                if analysis:
                    print(f"    Confidence: {analysis['confidence']:.2f}")
                    # Find odds for predicted side
                    predicted_side = (
                        "Over" if "over" in analysis["prediction"].lower() else "Under"
                    )
                    matching_odds = [
                        o for o in prop_data["odds"] if o["side"] == predicted_side
                    ]

                    if not matching_odds:
                        print(
                            f"    No odds available for predicted side: {predicted_side}"
                        )
                        continue

                    avg_odds = sum(o["price"] for o in matching_odds) / len(
                        matching_odds
                    )

                    # Calculate EV for props
                    avg_odds_float = float(avg_odds)
                    if avg_odds_float > 0:
                        payout_multiplier = 1 + (avg_odds_float / 100)
                    else:
                        payout_multiplier = 1 + (100 / abs(avg_odds_float))

                    expected_value = (
                        float(analysis["confidence"]) * payout_multiplier
                    ) - 1
                    print(f"    EV: {expected_value:.3f}")

                    opportunities.append(
                        {
                            "game_id": prop_data["game_id"],
                            "sport": sport,
                            "player": prop_data["player"],
                            "market": prop_data["market"],
                            "line": prop_data["line"],
                            "prediction": analysis["prediction"],
                            "confidence": analysis["confidence"],
                            "reasoning": analysis["reasoning"],
                            "key_factors": analysis["key_factors"],
                            "commence_time": prop_data["commence_time"],
                            "market_key": prop_data["market"],
                            "odds": avg_odds,
                            "expected_value": expected_value,
                        }
                    )
                elif analysis:
                    print(
                        f"    ✗ Confidence {analysis['confidence']:.2f} < {min_confidence:.2f}"
                    )
                else:
                    print(f"    ✗ AI analysis failed")

        return opportunities

    def _ai_analyze_prop(
        self,
        prop_data: Dict,
        player_stats: Dict,
        player_trends: Dict,
        matchup_data: Dict,
    ) -> Dict[str, Any]:
        """AI analysis for player props"""
        try:
            # Calculate average line and odds
            over_odds = [o for o in prop_data["odds"] if o["side"] == "Over"]
            under_odds = [o for o in prop_data["odds"] if o["side"] == "Under"]

            avg_over = (
                sum(o["price"] for o in over_odds) / len(over_odds) if over_odds else 0
            )
            avg_under = (
                sum(o["price"] for o in under_odds) / len(under_odds)
                if under_odds
                else 0
            )

            over_prob = self._american_to_probability(avg_over) if avg_over else 0
            under_prob = self._american_to_probability(avg_under) if avg_under else 0

            perf_stats = self._get_performance_stats()
            print(f"[PROP] Performance stats: {perf_stats}")

            # Build performance warnings
            perf_warnings = self._get_performance_warnings(prop_data["sport"])

            perf_context = ""
            if "overall" in perf_stats:
                perf_context = f"""
BENNY'S HISTORICAL PERFORMANCE (Last 30 days):
Overall: {perf_stats['overall']['win_rate']} win rate, {perf_stats['overall']['roi']} ROI ({perf_stats['overall']['total_bets']} bets)
By Sport: {', '.join(f"{s}: {r}" for s, r in perf_stats['by_sport'].items())}
By Market: {', '.join(f"{m}: {r}" for m, r in perf_stats['by_market'].items())}

{perf_warnings}

Note: Use this to inform confidence - be more conservative in markets where you've struggled."""
                print(f"[PROP] Including performance context in AI prompt")

            # Add new learning feedback
            sport = prop_data["sport"]
            what_works = self._get_what_works_analysis()
            what_fails = self._get_what_fails_analysis()
            recent_mistakes = self._analyze_recent_mistakes()
            winning_examples = self._get_winning_examples(sport, limit=2)
            winning_factors = self._extract_winning_factors()

            prompt = f"""You are Benny, an expert sports betting analyst. Your goal is to achieve 15%+ ROI through strategic betting decisions.

RISK PARAMETERS:
- Kelly Fraction: {self.learning_params.get('kelly_fraction', 0.5)} (bet sizing multiplier)
- Max Bet Size: {self.MAX_BET_PERCENTAGE*100:.0f}% of bankroll (${float(self.bankroll * Decimal(str(self.MAX_BET_PERCENTAGE))):.2f})
- Target ROI: {self.learning_params.get('target_roi', 0.15)*100:.0f}%
- Current Bankroll: ${float(self.bankroll):.2f}
{perf_context}

WHAT'S WORKING FOR YOU:
{what_works}

WHAT'S NOT WORKING:
{what_fails}

RECENT MISTAKE PATTERNS:
{recent_mistakes}

YOUR RECENT WINS IN {sport.upper()}:
{winning_examples}

FACTORS THAT PREDICT SUCCESS:
{winning_factors}

Player: {prop_data['player']} ({prop_data['team']})
Opponent: {prop_data['opponent']}
Market: {prop_data['market']}
Line: {prop_data['line']}
Sport: {prop_data['sport']}

MARKET ODDS:
Over {prop_data['line']}: {avg_over} ({over_prob:.1%} implied)
Under {prop_data['line']}: {avg_under} ({under_prob:.1%} implied)

PLAYER SEASON STATS (Last 20 games):
{json.dumps(player_stats, indent=2) if player_stats else 'No season data available'}

RECENT TRENDS (Last 10 games for this market):
{json.dumps(player_trends, indent=2) if player_trends else 'No trend data available'}

MATCHUP HISTORY vs {prop_data['opponent']}:
{json.dumps(matchup_data, indent=2) if matchup_data else 'No matchup history available'}

BENNY'S PROP PERFORMANCE:
{self._get_prop_market_performance(prop_data['market'])}

ANALYSIS INSTRUCTIONS:
1. Compare player's season average and last 5 games to the line
2. Consider recent trends - is player hot or cold?
3. Factor in matchup history against this opponent
4. Look for value where the line doesn't match recent performance
5. Consider Benny's historical accuracy on this prop type
6. CRITICAL BETTING THRESHOLDS:
   - Minimum Confidence: {self.BASE_MIN_CONFIDENCE} (65%) - Do not bet below this
   - Minimum Expected Value/ROI: {self.MIN_EV} (5%) - Only bet when expected ROI > 5%
   - Calculate EV/Expected ROI = (confidence × payout) - 1
   - Example: -110 odds (payout 1.909) at 65% confidence = EV of 0.24 (24% expected ROI) ✓
   - Example: -110 odds (payout 1.909) at 55% confidence = EV of 0.05 (5% expected ROI) ✓
   - Example: -110 odds (payout 1.909) at 52% confidence = EV of -0.007 (negative ROI) ✗
   - NEVER bet on negative expected ROI - you will lose money over time
7. Be highly selective - props are harder to predict than games
8. Skip if player data is limited or matchup is unclear

Respond with JSON only:
{{"prediction": "Over/Under X.X (Player Market)", "confidence": 0.70, "reasoning": "Brief explanation", "key_factors": ["factor1", "factor2"]}}

IMPORTANT: 
- Include market type in prediction for clarity (e.g., "Over 25.5 (Points)", "Under 8.5 (Rebounds)")
- Only bet when confidence >= {self.BASE_MIN_CONFIDENCE} AND expected ROI >= {self.MIN_EV}
- Expected ROI = (confidence × payout) - 1 must be positive and > 5%
- When in doubt, skip - protecting bankroll is priority #1"""

            response = bedrock.invoke_model(
                modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 400,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            content = result["content"][0]["text"]

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception as e:
            print(f"Error in prop AI analysis: {e}")
            return None

    def _get_player_team(self, player_name: str, sport: str) -> str:
        """Get player's team name, cached across calls"""
        if player_name in self.player_teams:
            return self.player_teams[player_name]
        # Will be populated by _get_player_stats; do a minimal lookup if needed
        try:
            normalized = player_name.lower().replace(" ", "_")
            resp = self.table.query(
                KeyConditionExpression=Key("pk").eq(f"PLAYER_STATS#{sport}#{normalized}"),
                ScanIndexForward=False, Limit=1,
            )
            items = resp.get("Items", [])
            team = items[0].get("stats", {}).get("team") if items else None
            self.player_teams[player_name] = team
            return team
        except Exception:
            self.player_teams[player_name] = None
            return None

    def _get_player_opponent(self, player_name: str, sport: str, game_id: str) -> str:
        """Derive opponent from player's team + game data"""
        game = self.game_teams.get(game_id)
        if not game:
            return None
        team = self._get_player_team(player_name, sport)
        if not team:
            return None
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        if team.lower() in home.lower() or home.lower() in team.lower():
            return away
        elif team.lower() in away.lower() or away.lower() in team.lower():
            return home
        return None

    def _get_player_stats(self, player_name: str, sport: str) -> Dict:
        """Get player season stats by aggregating recent games"""
        try:
            normalized = player_name.lower().replace(" ", "_")
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(
                    f"PLAYER_STATS#{sport}#{normalized}"
                ),
                ScanIndexForward=False,
                Limit=20,  # Last 20 games for season average
            )
            games = response.get("Items", [])
            if not games:
                return {}

            # Cache player team from most recent game
            if player_name not in self.player_teams:
                self.player_teams[player_name] = games[0].get("stats", {}).get("team")

            # Sport-specific stat keys
            stat_keys_by_sport = {
                "basketball_nba": ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO"],
                "americanfootball_nfl": [
                    "passing_yards",
                    "rushing_yards",
                    "receiving_yards",
                    "touchdowns",
                    "receptions",
                ],
                "baseball_mlb": ["hits", "runs", "RBI", "home_runs", "strikeouts"],
                "icehockey_nhl": ["goals", "assists", "shots", "plus_minus"],
            }

            stat_keys = stat_keys_by_sport.get(sport, [])
            if not stat_keys:
                return {}

            # Aggregate stats across games
            aggregated = {}
            for key in stat_keys:
                values = [
                    float(g.get("stats", {}).get(key, 0))
                    for g in games
                    if g.get("stats", {}).get(key)
                ]
                if values:
                    aggregated[f"{key}_avg"] = round(sum(values) / len(values), 2)
                    aggregated[f"{key}_last5"] = round(
                        sum(values[:5]) / min(5, len(values)), 2
                    )

            aggregated["games_played"] = len(games)
            return aggregated
        except Exception as e:
            print(f"Error fetching player stats: {e}")
            return {}

    def _get_player_trends(self, player_name: str, sport: str, market: str) -> Dict:
        """Get player recent performance trends for specific market"""
        try:
            normalized = player_name.lower().replace(" ", "_")
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(
                    f"PLAYER_STATS#{sport}#{normalized}"
                ),
                ScanIndexForward=False,
                Limit=10,
            )
            games = response.get("Items", [])
            if not games:
                return {}

            # Map market to stat key
            market_to_stat = {
                "player_points": "PTS",
                "player_rebounds": "REB",
                "player_assists": "AST",
                "player_threes": "3PM",
                "player_steals": "STL",
                "player_blocks": "BLK",
            }

            stat_key = market_to_stat.get(market)
            if not stat_key:
                return {}

            values = [
                float(g.get("stats", {}).get(stat_key, 0))
                for g in games
                if g.get("stats", {}).get(stat_key)
            ]
            if not values:
                return {}

            avg = sum(values) / len(values)
            last3_avg = sum(values[:3]) / min(3, len(values))

            return {
                "last_10_avg": round(avg, 2),
                "last_3_avg": round(last3_avg, 2),
                "trend": "hot" if last3_avg > avg else "cold",
                "games": values,
            }
        except Exception as e:
            print(f"Error fetching player trends: {e}")
            return {}

    def _get_player_matchup(self, player_name: str, opponent: str, sport: str) -> Dict:
        """Get player performance vs specific opponent"""
        if not player_name or not opponent:
            return {}
        try:
            normalized_player = player_name.lower().replace(" ", "_")
            normalized_opp = opponent.lower().replace(" ", "_")

            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(
                    f"PLAYER_STATS#{sport}#{normalized_player}"
                ),
                ScanIndexForward=False,
                Limit=20,
            )

            # Filter for games against this opponent
            matchup_games = [
                g
                for g in response.get("Items", [])
                if normalized_opp in g.get("sk", "").lower()
            ]

            if not matchup_games:
                return {"games_vs_opponent": 0}

            return {
                "games_vs_opponent": len(matchup_games),
                "recent_games": matchup_games[:5],
            }
        except Exception as e:
            print(f"Error fetching player matchup: {e}")
            return {}

    def _get_prop_market_performance(self, market_key: str) -> str:
        """Get Benny's historical performance on this prop market"""
        perf = self.learning_params.get("performance_by_prop_market", {})
        if market_key in perf:
            stats = perf[market_key]
            wr = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
            return f"Benny's {market_key} record: {stats['wins']}/{stats['total']} ({wr:.1%})"
        return f"No historical data for {market_key}"

    def _ai_analyze_game(
        self,
        game_data: Dict[str, Any],
        home_stats: Dict,
        away_stats: Dict,
        home_injuries: List[Dict],
        away_injuries: List[Dict],
        h2h_history: List[Dict],
        home_form: Dict,
        away_form: Dict,
        home_news: Dict,
        away_news: Dict,
        home_elo: float,
        away_elo: float,
        home_adjusted: Dict,
        away_adjusted: Dict,
        weather: Dict,
        fatigue: Dict,
        avg_spread: Dict = None,
        avg_total: Dict = None,
    ) -> Dict[str, Any]:
        """Have AI analyze game data and make independent prediction"""
        try:
            # Calculate average h2h odds
            avg_home_price = sum(o["home_price"] for o in game_data["h2h_odds"]) / len(
                game_data["h2h_odds"]
            )
            avg_away_price = sum(o["away_price"] for o in game_data["h2h_odds"]) / len(
                game_data["h2h_odds"]
            )
            draw_prices = [
                o["draw_price"] for o in game_data["h2h_odds"] if o.get("draw_price")
            ]
            avg_draw_price = (
                sum(draw_prices) / len(draw_prices) if draw_prices else None
            )

            # Convert to implied probabilities
            home_prob = self._american_to_probability(avg_home_price)
            away_prob = self._american_to_probability(avg_away_price)
            draw_prob = (
                self._american_to_probability(avg_draw_price)
                if avg_draw_price
                else None
            )

            # Build market odds section
            market_odds = f"""MONEYLINE (H2H):
Home: {avg_home_price} ({home_prob:.1%} implied)
Away: {avg_away_price} ({away_prob:.1%} implied)"""
            if draw_prob:
                market_odds += f"\nDraw: {avg_draw_price} ({draw_prob:.1%} implied)"

            if avg_spread:
                spread_home_prob = self._american_to_probability(
                    avg_spread["home_price"]
                )
                spread_away_prob = self._american_to_probability(
                    avg_spread["away_price"]
                )
                market_odds += f"""

SPREAD:
Home {avg_spread['home_point']:+.1f}: {avg_spread['home_price']} ({spread_home_prob:.1%} implied)
Away {avg_spread['away_point']:+.1f}: {avg_spread['away_price']} ({spread_away_prob:.1%} implied)"""

            if avg_total:
                total_over_prob = self._american_to_probability(avg_total["over_price"])
                total_under_prob = self._american_to_probability(
                    avg_total["under_price"]
                )
                market_odds += f"""

TOTAL:
Over {avg_total['point']:.1f}: {avg_total['over_price']} ({total_over_prob:.1%} implied)
Under {avg_total['point']:.1f}: {avg_total['under_price']} ({total_under_prob:.1%} implied)"""

            perf_stats = self._get_performance_stats()
            print(f"[GAME] Performance stats: {perf_stats}")
            perf_context = ""
            if "overall" in perf_stats:
                perf_context = f"""
BENNY'S HISTORICAL PERFORMANCE (Last 30 days):
Overall: {perf_stats['overall']['win_rate']} win rate, {perf_stats['overall']['roi']} ROI ({perf_stats['overall']['total_bets']} bets)
By Sport: {', '.join(f"{s}: {r}" for s, r in perf_stats['by_sport'].items())}
By Market: {', '.join(f"{m}: {r}" for m, r in perf_stats['by_market'].items())}
Note: Use this to inform confidence - be more conservative in markets where you've struggled."""
                print(f"[GAME] Including performance context in AI prompt")

            # Add new learning feedback
            sport = game_data["sport"]
            perf_warnings = self._get_performance_warnings(sport)
            what_works = self._get_what_works_analysis()
            what_fails = self._get_what_fails_analysis()
            recent_mistakes = self._analyze_recent_mistakes()
            winning_examples = self._get_winning_examples(sport, limit=2)
            winning_factors = self._extract_winning_factors()
            model_benchmarks = self._get_model_benchmarks(sport)
            feature_insights = self._get_feature_insights()

            prompt = f"""You are Benny, an expert sports betting analyst. Your goal is to achieve 15%+ ROI through strategic betting decisions.

RISK PARAMETERS:
- Kelly Fraction: {self.learning_params.get('kelly_fraction', 0.5)} (bet sizing multiplier)
- Max Bet Size: {self.MAX_BET_PERCENTAGE*100:.0f}% of bankroll (${float(self.bankroll * Decimal(str(self.MAX_BET_PERCENTAGE))):.2f})
- Target ROI: {self.learning_params.get('target_roi', 0.15)*100:.0f}%
- Current Bankroll: ${float(self.bankroll):.2f}
{perf_context}

{perf_warnings}

{feature_insights}

WHAT'S WORKING FOR YOU:
{what_works}

WHAT'S NOT WORKING:
{what_fails}

RECENT MISTAKE PATTERNS:
{recent_mistakes}

YOUR RECENT WINS IN {sport.upper()}:
{winning_examples}

FACTORS THAT PREDICT SUCCESS:
{winning_factors}

OTHER MODELS' PERFORMANCE ON {sport.upper()}:
{model_benchmarks}
Note: You should aim to match or beat the best models. If you're underperforming, learn from their approach.

Game: {game_data['away_team']} @ {game_data['home_team']}
Sport: {game_data['sport']}
Time: {game_data['commence_time']}

MARKET ODDS:
{market_odds}

ELO RATINGS (Team Strength):
Home: {home_elo:.0f} | Away: {away_elo:.0f} | Difference: {home_elo - away_elo:+.0f}
Note: Higher = stronger. Difference >50 = significant edge. Average team = 1500.

OPPONENT-ADJUSTED EFFICIENCY:
Home: {json.dumps(home_adjusted, indent=2) if home_adjusted else 'No data'}
Away: {json.dumps(away_adjusted, indent=2) if away_adjusted else 'No data'}
Note: Adjusted for opponent strength - more accurate than raw stats.

TRAVEL & FATIGUE:
{json.dumps(fatigue, indent=2) if fatigue else 'No data'}
Note: Fatigue score 0-100 where <30=fresh, 30-60=moderate, >60=tired. High fatigue hurts performance.

WEATHER CONDITIONS:
{json.dumps(weather, indent=2) if weather else 'Indoor venue or no data'}
Note: Impact levels - high=significant effect, moderate=some effect, low=minimal.

RECENT FORM (Last 5 games):
Home: {home_form.get('record', 'Unknown')} - {home_form.get('streak', '')}
Away: {away_form.get('record', 'Unknown')} - {away_form.get('streak', '')}

HEAD-TO-HEAD (Last 3 meetings):
{json.dumps(h2h_history, indent=2) if h2h_history else 'No history'}

KEY INJURIES:
Home: {json.dumps(home_injuries, indent=2) if home_injuries else 'None'}
Away: {json.dumps(away_injuries, indent=2) if away_injuries else 'None'}

NEWS SENTIMENT (Last 48 hours):
Home: Sentiment={home_news.get('sentiment_score', 0):.2f}, Impact={home_news.get('impact_score', 0):.1f}, Articles={home_news.get('news_count', 0)}
Away: Sentiment={away_news.get('sentiment_score', 0):.2f}, Impact={away_news.get('impact_score', 0):.1f}, Articles={away_news.get('news_count', 0)}

RAW TEAM STATS (Season Averages):
Home: {json.dumps(home_stats, indent=2) if home_stats else 'No data'}
Away: {json.dumps(away_stats, indent=2) if away_stats else 'No data'}

ANALYSIS INSTRUCTIONS:
1. Analyze ALL available markets (moneyline, spread, total)
2. Prioritize Elo ratings and opponent-adjusted metrics
3. Factor in fatigue if either team has score >50 or traveled >1000 miles
4. Consider weather impact if marked as "high" or "moderate"
5. CRITICAL BETTING THRESHOLDS:
   - Minimum Confidence: {self.BASE_MIN_CONFIDENCE} (65%) - Do not bet below this
   - Minimum Expected Value/ROI: {self.MIN_EV} (5%) - Only bet when expected ROI > 5%
   - Calculate EV/Expected ROI = (confidence × payout) - 1
   - Example: -110 odds (payout 1.909) at 65% confidence = EV of 0.24 (24% expected ROI) ✓
   - Example: -110 odds (payout 1.909) at 55% confidence = EV of 0.05 (5% expected ROI) ✓
   - Example: -110 odds (payout 1.909) at 52% confidence = EV of -0.007 (negative ROI) ✗
   - NEVER bet on negative expected ROI - you will lose money over time
6. For spreads: Consider if favorite can cover the spread, not just win
7. For totals: Analyze pace, defense, and scoring trends
8. Be highly selective - quality over quantity. Skip games where edge is unclear.
9. Learn from your performance by sport - adjust confidence accordingly

Respond with JSON only - include ALL markets you want to bet on:
{{"h2h": {{"prediction": "Team Name (Moneyline)", "confidence": 0.75, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}, "spread": {{"prediction": "Team Name -X.X (Spread)", "confidence": 0.70, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}, "total": {{"prediction": "Over/Under XXX.X (Total)", "confidence": 0.65, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}}}

IMPORTANT: 
- Include market type in prediction text for clarity
- Only include markets where confidence >= {self.BASE_MIN_CONFIDENCE} AND expected ROI >= {self.MIN_EV}
- Expected ROI = (confidence × payout) - 1 must be positive and > 5%
- When in doubt, skip the bet - protecting bankroll is priority #1"""

            response = bedrock.invoke_model(
                modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 800,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            content = result["content"][0]["text"]

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            analysis = json.loads(content)
            return analysis

        except Exception as e:
            print(f"Error in AI analysis: {e}")
            return None

    def _american_to_probability(self, american_odds: float) -> float:
        """Convert American odds to implied probability"""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)

    def _get_team_injuries(self, team_name: str, sport: str) -> List[Dict]:
        """Get current injuries for a team"""
        try:
            normalized_team = team_name.lower().replace(" ", "_")
            response = table.query(
                KeyConditionExpression=Key("pk").eq(
                    f"INJURIES#{sport}#{normalized_team}"
                ),
                ScanIndexForward=False,
                Limit=10,
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"Error fetching injuries: {e}")
            return []

    def _get_team_news_sentiment(self, team_name: str, sport: str) -> Dict:
        """Get news sentiment for a team"""
        try:
            from news_features import get_team_sentiment

            return get_team_sentiment(sport, team_name)
        except Exception as e:
            print(f"Error fetching news sentiment: {e}")
            return {"sentiment_score": 0.0, "impact_score": 0.0, "news_count": 0}

    def _get_elo_rating(self, team_name: str, sport: str) -> float:
        """Get current Elo rating for a team"""
        try:
            normalized_team = team_name.strip().replace(" ", "_").upper()
            response = table.query(
                KeyConditionExpression=Key("pk").eq(f"ELO#{sport}#{normalized_team}"),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            return float(items[0].get("rating", 1500)) if items else 1500.0
        except Exception as e:
            print(f"Error fetching Elo: {e}")
            return 1500.0

    def _get_adjusted_metrics(self, team_name: str, sport: str) -> Dict:
        """Get opponent-adjusted metrics for a team"""
        try:
            normalized_team = team_name.lower().replace(" ", "_")
            response = table.query(
                KeyConditionExpression=Key("pk").eq(
                    f"ADJUSTED_METRICS#{sport}#{normalized_team}"
                ),
                FilterExpression="attribute_exists(latest) AND latest = :true",
                ExpressionAttributeValues={":true": True},
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0].get("metrics", {}) if items else {}
        except Exception as e:
            print(f"Error fetching adjusted metrics: {e}")
            return {}

    def _get_weather_data(self, game_id: str) -> Dict:
        """Get weather data for a game"""
        try:
            response = table.query(
                KeyConditionExpression=Key("pk").eq(f"WEATHER#{game_id}"),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            if items:
                return {
                    "temp_f": float(items[0].get("temp_f", 0)),
                    "wind_mph": float(items[0].get("wind_mph", 0)),
                    "precip_in": float(items[0].get("precip_in", 0)),
                    "impact": items[0].get("impact", "low"),
                }
            return {}
        except Exception as e:
            print(f"Error fetching weather: {e}")
            return {}

    def _get_fatigue_data(self, game_id: str) -> Dict:
        """Get travel/fatigue data for a game"""
        try:
            response = table.query(
                KeyConditionExpression=Key("pk").eq(f"FATIGUE#{game_id}"),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            if items:
                return {
                    "home_fatigue": float(items[0].get("home_fatigue_score", 0)),
                    "home_miles": float(items[0].get("home_total_miles", 0)),
                    "home_rest": int(items[0].get("home_days_rest", 0)),
                    "away_fatigue": float(items[0].get("away_fatigue_score", 0)),
                    "away_miles": float(items[0].get("away_total_miles", 0)),
                    "away_rest": int(items[0].get("away_days_rest", 0)),
                }
            return {}
        except Exception as e:
            print(f"Error fetching fatigue: {e}")
            return {}

    def _get_head_to_head(
        self, home_team: str, away_team: str, sport: str
    ) -> List[Dict]:
        """Get last 3 H2H matchups"""
        try:
            home_norm = home_team.lower().replace(" ", "_")
            away_norm = away_team.lower().replace(" ", "_")
            teams_sorted = sorted([home_norm, away_norm])

            response = table.query(
                KeyConditionExpression=Key("pk").eq(
                    f"H2H#{sport}#{teams_sorted[0]}#{teams_sorted[1]}"
                ),
                ScanIndexForward=False,
                Limit=3,
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"Error fetching H2H: {e}")
            return []

    def _get_recent_form(self, team_name: str, sport: str) -> Dict:
        """Get last 5 games record and streak from outcomes"""
        try:
            normalized_team = team_name.lower().replace(" ", "_")

            response = table.query(
                IndexName="TeamOutcomesIndex",
                KeyConditionExpression=Key("team_outcome_pk").eq(
                    f"TEAM#{sport}#{normalized_team}"
                ),
                ScanIndexForward=False,
                Limit=5,
            )

            games = response.get("Items", [])
            if not games:
                return {}

            wins = sum(1 for g in games if g.get("winner") == team_name)
            losses = len(games) - wins

            # Calculate streak
            streak = ""
            if games:
                current_result = "W" if games[0].get("winner") == team_name else "L"
                streak_count = 1
                for g in games[1:]:
                    result = "W" if g.get("winner") == team_name else "L"
                    if result == current_result:
                        streak_count += 1
                    else:
                        break
                streak = f"{current_result}{streak_count}"

            return {
                "record": f"{wins}-{losses}",
                "streak": streak,
            }
        except Exception as e:
            print(f"Error fetching recent form: {e}")
            return {}

    def _get_team_stats(self, team: str, sport: str) -> Dict[str, Any]:
        """Fetch recent team stats from DynamoDB"""
        try:
            normalized_team = team.lower().replace(" ", "_")
            response = table.query(
                KeyConditionExpression=Key("pk").eq(
                    f"TEAM_STATS#{sport}#{normalized_team}"
                ),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0].get("stats", {}) if items else {}
        except Exception as e:
            print(f"Error fetching team stats: {e}")
            return {}

    def _get_feature_insights(self) -> str:
        """Get learned feature importance insights for AI prompt (v2 only)"""
        if self.version != "v2":
            return "No learned insights available (v1)"

        try:
            response = self.table.get_item(
                Key={"pk": f"{self.pk}#LEARNING", "sk": "FEATURES"}
            )
            insights = response.get("Item", {}).get("insights", {})

            if not insights or "strongest_predictors" not in insights:
                return "Insufficient data to determine feature importance"

            lines = []
            lines.append("LEARNED FEATURE IMPORTANCE (What Actually Predicts Wins):")

            # Top predictive features
            for pred in insights["strongest_predictors"][:3]:
                feature = pred["feature"]
                lines.append(
                    f"\n{feature.upper()} (predictive power: {pred['spread']:.1%} spread)"
                )

                # Get specific insights for this feature
                feature_data = insights.get("insights", {}).get(feature, {})
                if feature_data:
                    for range_key, data in sorted(
                        feature_data.items(),
                        key=lambda x: x[1].get("win_rate", 0),
                        reverse=True,
                    )[:3]:
                        if data.get("count", 0) >= 5:
                            lines.append(
                                f"  • {range_key}: {data['win_rate']:.1%} win rate ({data['count']} bets)"
                            )

            return "\n".join(lines)
        except:
            return "Error loading feature insights"

    def calculate_bet_size(self, confidence: float, odds: float = None) -> Decimal:
        """Calculate bet size using Kelly Criterion"""
        return self.bankroll_manager.calculate_bet_size(confidence, odds)

    def analyze_feature_performance(self):
        """Analyze which features predict wins (v2 only)"""
        if self.version != "v2":
            print("Feature analysis only available for v2")
            return

        from datetime import datetime

        analyzer = OutcomeAnalyzer(self.table, self.pk)

        # Analyze features
        insights = analyzer.analyze_features()

        if "error" in insights:
            print(
                f"Feature analysis: {insights['error']} ({insights.get('bet_count', 0)} bets)"
            )
        else:
            print(f"\n=== FEATURE ANALYSIS ({insights['total_bets']} bets) ===")
            print("\nStrongest Predictors:")
            for pred in insights["strongest_predictors"][:5]:
                print(
                    f"  {pred['feature']}: {pred['spread']:.1%} spread (max: {pred['max_win_rate']:.1%}, min: {pred['min_win_rate']:.1%})"
                )

            insights["timestamp"] = datetime.utcnow().isoformat()
            analyzer.save_insights(insights)
            print("Feature insights saved")

        # Analyze confidence calibration
        calibration = analyzer.analyze_confidence_calibration()

        if "error" in calibration:
            print(
                f"Calibration analysis: {calibration['error']} ({calibration.get('bet_count', 0)} bets)"
            )
        else:
            print(
                f"\n=== CONFIDENCE CALIBRATION ({calibration['total_bets']} bets) ==="
            )
            print(
                f"Average calibration error: {calibration['avg_calibration_error']:.1%}"
            )
            print(f"Well calibrated: {calibration['is_well_calibrated']}")

            print("\nCalibration by bucket:")
            for bucket, data in calibration["calibration"].items():
                print(
                    f"  {bucket}%: {data['actual_win_rate']:.1%} actual vs {data['expected_confidence']:.1%} expected ({data['count']} bets)"
                )

            calibration["timestamp"] = datetime.utcnow().isoformat()
            analyzer.save_calibration(calibration)
            print("Calibration data saved")

        # Optimize thresholds
        optimizer = ThresholdOptimizer(self.table, self.pk)
        thresholds = optimizer.optimize_thresholds()

        if "error" in thresholds:
            print(
                f"Threshold optimization: {thresholds['error']} ({thresholds.get('bet_count', 0)} bets)"
            )
        else:
            print(f"\n=== THRESHOLD OPTIMIZATION ({thresholds['total_bets']} bets) ===")
            print(
                f"Global optimal: confidence={thresholds['global']['optimal_min_confidence']:.0%}, EV={thresholds['global']['optimal_min_ev']:.1%}"
            )
            print(
                f"  Expected ROI: {thresholds['global']['expected_roi']:.1%} ({thresholds['global']['sample_size']} bets)"
            )

            if thresholds.get("by_sport"):
                print("\nOptimal by sport:")
                for sport, opt in thresholds["by_sport"].items():
                    print(
                        f"  {sport}: conf={opt['optimal_min_confidence']:.0%}, ROI={opt['expected_roi']:.1%}"
                    )

            thresholds["timestamp"] = datetime.utcnow().isoformat()
            optimizer.save_optimal_thresholds(thresholds)
            print("Optimal thresholds saved")

    def update_learning_parameters(self):
        """Update Benny's learning parameters based on recent performance"""
        try:
            # Get recent settled bets (last 30 days)
            from datetime import timedelta

            cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()

            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                FilterExpression="settled_at > :cutoff AND #status IN (:won, :lost)",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":cutoff": cutoff,
                    ":won": "won",
                    ":lost": "lost",
                },
            )

            bets = response.get("Items", [])
            if len(bets) < self.MIN_SAMPLE_SIZE:  # Need minimum sample size to learn
                print(
                    f"Insufficient data for learning: {len(bets)} bets (need {self.MIN_SAMPLE_SIZE})"
                )
                return

            # Calculate overall win rate
            wins = sum(1 for b in bets if b.get("status") == "won")
            win_rate = wins / len(bets)

            # Calculate true profit (excluding deposits)
            total_deposits = self._get_total_deposits()
            true_profit = self.bankroll - self.WEEKLY_BUDGET - total_deposits

            # Calculate ROI based on actual betting, not deposits
            settled_bets = [b for b in bets if b.get("status") in ["won", "lost"]]
            won_bets = [b for b in settled_bets if b.get("status") == "won"]

            total_wagered = sum(
                Decimal(str(b.get("bet_amount", 0))) for b in settled_bets
            )
            total_profit = sum(Decimal(str(b.get("profit", 0))) for b in settled_bets)
            roi = (
                (total_profit / total_wagered * 100)
                if total_wagered > 0
                else Decimal("0")
            )

            # Adjust MIN_CONFIDENCE based on performance
            if win_rate > 0.60:
                # Performing well, can lower threshold slightly
                adjustment = -0.02
            elif win_rate < 0.45:
                # Performing poorly, raise threshold
                adjustment = 0.05
            else:
                # Acceptable performance, small adjustment toward 0
                current_adj = float(
                    self.learning_params.get("min_confidence_adjustment", 0)
                )
                adjustment = -current_adj * 0.1  # Slowly return to baseline

            # Calculate performance by sport and market
            perf_by_sport = {}
            perf_by_market = {}
            perf_by_prop_market = {}

            for bet in bets:
                sport = bet.get("sport", "unknown")
                market_key = bet.get("market_key", "unknown")
                won = bet.get("status") == "won"

                if sport not in perf_by_sport:
                    perf_by_sport[sport] = {"wins": 0, "total": 0}
                perf_by_sport[sport]["total"] += 1
                if won:
                    perf_by_sport[sport]["wins"] += 1

                if market_key not in perf_by_market:
                    perf_by_market[market_key] = {"wins": 0, "total": 0, "wagered": 0, "returned": 0}
                perf_by_market[market_key]["total"] += 1
                bet_amt = float(bet.get("bet_amount", 0))
                perf_by_market[market_key]["wagered"] += bet_amt
                if won:
                    perf_by_market[market_key]["wins"] += 1
                    perf_by_market[market_key]["returned"] += float(bet.get("payout", 0))

                # Track prop market performance (player_points, player_rebounds, etc.)
                if market_key.startswith("player_"):
                    if market_key not in perf_by_prop_market:
                        perf_by_prop_market[market_key] = {"wins": 0, "total": 0}
                    perf_by_prop_market[market_key]["total"] += 1
                    if won:
                        perf_by_prop_market[market_key]["wins"] += 1

            # Update learning parameters
            self.learning_params.update(
                {
                    "min_confidence_adjustment": Decimal(str(adjustment)),
                    "performance_by_sport": perf_by_sport,
                    "performance_by_market": perf_by_market,
                    "performance_by_prop_market": perf_by_prop_market,
                    "overall_win_rate": Decimal(str(win_rate)),
                    "total_bets_analyzed": len(bets),
                    "total_deposits": total_deposits,
                    "true_profit": true_profit,
                    "roi_percentage": roi,
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )

            self.table.put_item(Item=self.learning_params)
            print(
                f"Updated Benny learning: win_rate={win_rate:.2%}, adjustment={adjustment:+.3f}"
            )

            # Log prop market performance
            if perf_by_prop_market:
                print("Prop market performance:")
                for market, stats in sorted(
                    perf_by_prop_market.items(),
                    key=lambda x: x[1]["wins"] / max(x[1]["total"], 1),
                    reverse=True,
                ):
                    wr = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
                    print(f"  {market}: {stats['wins']}/{stats['total']} ({wr:.1%})")

        except Exception as e:
            print(f"Error updating learning parameters: {e}")

    def place_bet(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Place a virtual bet"""
        # Check adaptive threshold
        sport = opportunity["sport"]
        market = opportunity["market_key"]
        required_confidence = self._get_adaptive_threshold(sport, market)

        if opportunity["confidence"] < required_confidence:
            print(
                f"  Skipping: confidence {opportunity['confidence']:.2f} < required {required_confidence:.2f}"
            )
            return {"success": False, "reason": f"Confidence below threshold"}

        # Check for existing bet
        game_id = opportunity["game_id"]
        market_key = opportunity["market_key"]
        existing_bets = self.table.query(
            KeyConditionExpression=Key("pk").eq(self.pk)
            & Key("sk").begins_with("BET#"),
            FilterExpression="game_id = :gid AND market_key = :mk AND #status = :pending",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":gid": game_id,
                ":mk": market_key,
                ":pending": "pending",
            },
        )

        if existing_bets.get("Items"):
            print(f"  Skipping: already have pending bet")
            return {"success": False, "reason": "Already have pending bet"}

        # Calculate bet size
        confidence = opportunity["confidence"]
        odds = opportunity.get("odds")
        bet_size = self.bankroll_manager.calculate_bet_size(confidence, odds)

        # Check minimum bet size
        MIN_BET = Decimal("5.00")
        if bet_size < MIN_BET:
            print(f"  Skipping: bet size ${bet_size:.2f} < minimum ${MIN_BET}")
            return {"success": False, "reason": f"Bet size below ${MIN_BET} minimum"}

        if bet_size > self.bankroll:
            return {"success": False, "reason": "Insufficient bankroll"}

        # Extract features for v2
        features = opportunity.get("features") if self.version == "v2" else None

        # Place bet via executor
        result = self.bet_executor.place_bet(
            opportunity, bet_size, self.bankroll, features
        )

        # Update bankroll
        new_bankroll = self.bankroll - bet_size
        self._update_bankroll(new_bankroll)

        return {
            "success": True,
            "bet_id": result["bet_id"],
            "bet_amount": result["bet_amount"],
            "remaining_bankroll": float(new_bankroll),
            "ai_reasoning": result["ai_reasoning"],
            "market_key": opportunity["market_key"],
        }
        if not self.notification_queue_url:
            return

        message = {
            "type": "bet_placed",
            "data": {
                "sport": opportunity["sport"],
                "game": f"{opportunity['away_team']} @ {opportunity['home_team']}",
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
            # Log but don't fail bet placement
            print(f"Failed to send notification event: {e}")

    def run_daily_analysis(self) -> Dict[str, Any]:
        """Run daily analysis for games and props"""
        print(
            f"Starting Benny Trader {self.version} analysis. Current bankroll: ${self.bankroll}"
        )

        # Check if auto-deposit is needed
        auto_deposited = self._auto_deposit_if_needed()

        # Update learning parameters before analyzing
        self.update_learning_parameters()

        # Run feature analysis for v2
        if self.version == "v2":
            self.analyze_feature_performance()

        # 1. Evaluate existing positions for cash-out/double-down
        position_actions = self._manage_positions()

        # 2. Analyze all games and props
        game_opportunities = self.analyze_games()
        print(f"Found {len(game_opportunities)} game opportunities")

        prop_opportunities = []
        if self.bankroll > Decimal("20.00"):
            prop_opportunities = self.analyze_props()
            print(f"Found {len(prop_opportunities)} prop opportunities")

        # 3. Build and place parlays from prop opportunities
        parlay_bets = []
        if prop_opportunities:
            eligible = [o for o in prop_opportunities if o.get("confidence", 0) >= 0.70]
            game_ids = [o.get("game_id") for o in eligible]
            print(f"Parlay candidates: {len(eligible)} legs with ≥0.70 conf, {len(set(game_ids))} unique games")
            parlays = self.parlay_engine.build_parlays(prop_opportunities)
            for parlay in parlays:
                if self.bankroll < Decimal("10.00"):
                    break
                bet_size = self.parlay_engine.calculate_parlay_bet_size(
                    parlay, self.bankroll
                )
                if bet_size < Decimal("5.00"):
                    continue
                result = self.bet_executor.place_parlay(
                    parlay, bet_size, self.bankroll
                )
                if result["success"]:
                    self._update_bankroll(self.bankroll - bet_size)
                    parlay_bets.append(result)
                    total_bet += Decimal(str(result["bet_amount"]))
                    print(
                        f"Placed {parlay['num_legs']}-leg parlay for ${result['bet_amount']} "
                        f"(odds: {parlay['combined_american_odds']:+d})"
                    )
            print(f"Placed {len(parlay_bets)} parlays")

        # 4. Combine and sort by confidence * edge (best opportunities first)
        all_opportunities = game_opportunities + prop_opportunities
        all_opportunities.sort(
            key=lambda x: x.get("confidence", 0) * x.get("edge", 0), reverse=True
        )

        # 5. Place bets in priority order
        placed_bets = []
        total_bet = Decimal("0")

        for opp in all_opportunities:
            if self.bankroll < Decimal("10.00"):
                print(f"Bankroll too low (${self.bankroll}), stopping")
                break

            result = self.place_bet(opp)
            if result["success"]:
                placed_bets.append(result)
                total_bet += Decimal(str(result["bet_amount"]))
                print(f"Placed bet: {opp['prediction']} for ${result['bet_amount']}")

        game_bets = [
            b
            for b in placed_bets
            if b.get("market_key") in ["h2h", "spreads", "totals"]
        ]
        prop_bets = [
            b
            for b in placed_bets
            if b.get("market_key") not in ["h2h", "spreads", "totals"]
        ]

        print(
            f"Analysis complete. Placed {len(game_bets)} game bets, {len(prop_bets)} prop bets, "
            f"{len(parlay_bets)} parlays (${total_bet} total)"
        )

        return {
            "game_opportunities": len(game_opportunities),
            "prop_opportunities": len(prop_opportunities),
            "total_bets": len(placed_bets) + len(parlay_bets),
            "game_bets_placed": len(game_bets),
            "prop_bets_placed": len(prop_bets),
            "parlay_bets_placed": len(parlay_bets),
            "total_bet_amount": float(total_bet),
            "remaining_bankroll": float(self.bankroll),
            "bets": placed_bets,
            "parlay_bets": parlay_bets,
            "position_actions": position_actions,
        }

    def _manage_positions(self) -> Dict[str, Any]:
        """Manage existing positions - cash-out and double-down"""
        evaluations = self.position_manager.evaluate_pending_bets()

        cash_outs = []
        double_downs = []

        for eval in evaluations:
            # Check for cash-out
            should_cash, reason = self.position_manager.should_cash_out(eval)
            if should_cash:
                result = self.position_manager.execute_cash_out(eval["bet"], reason)
                if result["success"]:
                    # Return cash to bankroll
                    self._update_bankroll(
                        self.bankroll + Decimal(str(result["cash_out_value"]))
                    )
                    cash_outs.append(result)
                    print(
                        f"Cashed out bet: {reason}, returned ${result['cash_out_value']}"
                    )
                continue

            # Check for double-down
            (
                should_double,
                reason,
                additional_stake,
            ) = self.position_manager.should_double_down(eval, self.bankroll)
            if should_double and additional_stake <= self.bankroll:
                result = self.position_manager.execute_double_down(
                    eval["bet"], additional_stake, reason
                )
                if result["success"]:
                    # Deduct from bankroll
                    self._update_bankroll(self.bankroll - additional_stake)
                    double_downs.append(result)
                    print(f"Doubled down: {reason}, added ${additional_stake}")

        return {
            "cash_outs": len(cash_outs),
            "double_downs": len(double_downs),
            "details": {"cash_outs": cash_outs, "double_downs": double_downs},
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for Benny"""
        # Get current bankroll from main record
        response = self.table.get_item(Key={"pk": self.pk, "sk": "BANKROLL"})
        current_bankroll = (
            float(response.get("Item", {}).get("amount", 100.0))
            if "Item" in response
            else 100.0
        )
        print(f"[DASHBOARD] Read bankroll from main record: ${current_bankroll}")

        # Get ALL bets for stats calculation
        all_bets = []
        last_key = None
        while True:
            query_kwargs = {
                "KeyConditionExpression": Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                "ScanIndexForward": False,
            }
            if last_key:
                query_kwargs["ExclusiveStartKey"] = last_key

            response = self.table.query(**query_kwargs)
            all_bets.extend(response.get("Items", []))

            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break

        # Calculate stats from ALL bets
        total_bets = len(all_bets)
        pending_bets = [b for b in all_bets if b.get("status") == "pending"]
        settled_bets = [b for b in all_bets if b.get("status") in ["won", "lost"]]
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
        best_bet = (
            max(
                won_bets,
                key=lambda b: float(b.get("payout", 0)) - float(b.get("bet_amount", 0)),
                default=None,
            )
            if won_bets
            else None
        )

        lost_bets = [b for b in settled_bets if b.get("status") == "lost"]
        worst_bet = (
            max(
                lost_bets,
                key=lambda b: float(b.get("bet_amount", 0)),
                default=None,
            )
            if lost_bets
            else None
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
            KeyConditionExpression=Key("pk").eq(self.pk)
            & Key("sk").begins_with("BANKROLL#"),
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

        # Ensure current bankroll is the last point
        if bankroll_history:
            last_amount = bankroll_history[-1]["amount"]
            if abs(last_amount - current_bankroll) > 0.01:
                # Add current bankroll as final point if different
                bankroll_history.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "amount": current_bankroll,
                    }
                )
        else:
            # No history, add current as only point
            bankroll_history.append(
                {"timestamp": datetime.utcnow().isoformat(), "amount": current_bankroll}
            )

        # Get cash-out data
        cashout_response = table.query(
            KeyConditionExpression=Key("pk").eq("BENNY#CASHOUT"),
            ScanIndexForward=False,
            Limit=100,
        )
        cashouts = cashout_response.get("Items", [])

        # Calculate cash-out metrics
        evaluated_cashouts = [c for c in cashouts if c.get("actual_outcome")]
        correct_cashouts = [c for c in evaluated_cashouts if c.get("was_correct")]

        total_saved = sum(
            float(c.get("money_saved", 0))
            for c in evaluated_cashouts
            if c.get("money_saved", 0) > 0
        )
        total_left_on_table = sum(
            abs(float(c.get("money_saved", 0)))
            for c in evaluated_cashouts
            if c.get("money_saved", 0) < 0
        )

        cashout_stats = {
            "total_cashouts": len(cashouts),
            "accuracy_rate": round(len(correct_cashouts) / len(evaluated_cashouts), 3)
            if evaluated_cashouts
            else None,
            "money_saved": round(total_saved, 2),
            "money_left_on_table": round(total_left_on_table, 2),
            "net_impact": round(total_saved - total_left_on_table, 2),
            "recent_cashouts": [
                {
                    "bet_id": c.get("bet_id"),
                    "game_id": c.get("game_id"),
                    "original_stake": float(c.get("original_stake", 0)),
                    "cash_out_value": float(c.get("cash_out_value", 0)),
                    "reason": c.get("reason"),
                    "cashed_out_at": c.get("cashed_out_at"),
                    "was_correct": c.get("was_correct"),
                    "actual_outcome": c.get("actual_outcome"),
                    "money_saved": float(c.get("money_saved", 0))
                    if c.get("money_saved")
                    else None,
                }
                for c in cashouts[:20]
            ],
        }

        return {
            "current_bankroll": current_bankroll,
            "weekly_budget": 100.0,
            "total_bets": total_bets,
            "pending_bets": len(pending_bets),
            "win_rate": round(win_rate, 3),
            "roi": round(roi, 3),
            "bankroll_growth": round((current_bankroll - bankroll_history[0]["amount"]) / bankroll_history[0]["amount"], 3) if bankroll_history and bankroll_history[0]["amount"] > 0 else 0,
            "cashout_stats": cashout_stats,
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
                    "game": (
                        f"{b.get('player_name')} {b.get('market_key')}"
                        if b.get("player_name")
                        else f"{b.get('away_team')} @ {b.get('home_team')}"
                    ),
                    "prediction": b.get("prediction"),
                    "market": b.get("market_key", "h2h"),
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
                    "expected_roi": round(
                        (
                            float(b.get("expected_payout", 0))
                            - float(b.get("bet_amount", 0))
                        )
                        / float(b.get("bet_amount", 1)),
                        3,
                    )
                    if b.get("expected_payout") and float(b.get("bet_amount", 0)) > 0
                    else None,
                }
                # Return all pending bets + 20 most recent completed bets
                for b in (pending_bets + [b for b in settled_bets[:20]])
            ],
        }


def lambda_handler(event, context):
    """Lambda handler for Benny trader"""
    try:
        # Check if this is a scheduled run or API call
        if "source" in event and event["source"] == "aws.events":
            # Scheduled daily run
            trader = BennyTrader()

            # Try to acquire lock
            if not trader._acquire_lock():
                print("Another Benny execution is already running. Exiting.")
                return {
                    "statusCode": 200,
                    "body": json.dumps({"message": "Execution already in progress"}),
                }

            try:
                result = trader.run_daily_analysis()
                return {
                    "statusCode": 200,
                    "body": json.dumps(result, default=str),
                }
            finally:
                trader._release_lock()
        else:
            # API call for dashboard
            dashboard = BennyTrader.get_dashboard_data()

            return {
                "statusCode": 200,
                "body": json.dumps(dashboard, default=str),
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()

        # Emit CloudWatch metric
        try:
            import boto3

            cloudwatch = boto3.client("cloudwatch")
            cloudwatch.put_metric_data(
                Namespace="SportsAnalytics/BennyTrader",
                MetricData=[
                    {"MetricName": "TradingError", "Value": 1, "Unit": "Count"}
                ],
            )
        except:
            pass

        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    import sys

    trader_v1 = BennyTrader(version="v1")

    if not trader_v1._acquire_lock():
        print("Another Benny execution is already running. Exiting.")
        sys.exit(0)

    exit_code = 0
    try:
        print("Running Benny v1...")
        result_v1 = trader_v1.run_daily_analysis()
        print(f"Benny v1 complete: {result_v1}")

        print("\nRunning Benny v2...")
        trader_v2 = BennyTrader(version="v2")
        result_v2 = trader_v2.run_daily_analysis()
        print(f"Benny v2 complete: {result_v2}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        exit_code = 1
    finally:
        trader_v1._release_lock()

    sys.exit(exit_code)
