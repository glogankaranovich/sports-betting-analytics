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
        pk_map = {"v1": "BENNY", "v3": "BENNY_V3"}
        self.pk = pk_map.get(version, "BENNY")

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
        self._perf_stats_cache = None  # populated once per run

        # Model — each version has its own strategy class
        if version == "v3":
            from benny.models.v3 import BennyV3
            self.model = BennyV3(self.table)
        else:
            from benny.models.v1 import BennyV1
            self.model = BennyV1(self.table, self.learning_engine, self.bankroll_manager)

        # Delegate to managers
        self.bankroll = self.bankroll_manager.bankroll
        self.week_start = self.bankroll_manager.week_start
        self.learning_params = self.learning_engine.params

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
        """Get Benny's historical performance stats for learning (cached per run)"""
        if self._perf_stats_cache is not None:
            return self._perf_stats_cache

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
                self._perf_stats_cache = {"message": "No settled bets yet"}
                return self._perf_stats_cache

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

            self._perf_stats_cache = stats
            return self._perf_stats_cache
        except Exception as e:
            print(f"Error fetching performance stats: {e}")
            self._perf_stats_cache = {"message": "Error loading stats"}
            return self._perf_stats_cache

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
                    prediction = analysis.get("prediction", "")
                    if not prediction or "skip" in prediction.lower():
                        print(f"    AI recommended skip")
                        continue
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
                    elif avg_odds_float < 0:
                        payout_multiplier = 1 + (100 / abs(avg_odds_float))
                    else:
                        print(f"    Skipping: zero odds")
                        continue

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
            prompt = self.model.build_prop_prompt(prop_data, player_stats, player_trends, matchup_data)
            max_tokens = 300 if self.version == "v3" else 400

            response = bedrock.invoke_model(
                modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                }),
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
            avg_home_price = sum(o["home_price"] for o in game_data["h2h_odds"]) / len(game_data["h2h_odds"])
            avg_away_price = sum(o["away_price"] for o in game_data["h2h_odds"]) / len(game_data["h2h_odds"])
            draw_prices = [o["draw_price"] for o in game_data["h2h_odds"] if o.get("draw_price")]
            avg_draw_price = sum(draw_prices) / len(draw_prices) if draw_prices else None

            home_prob = self._american_to_probability(avg_home_price)
            away_prob = self._american_to_probability(avg_away_price)
            draw_prob = self._american_to_probability(avg_draw_price) if avg_draw_price else None

            # Build context dict for model
            context = {
                "avg_h2h": {"home": avg_home_price, "away": avg_away_price},
                "home_prob": home_prob,
                "away_prob": away_prob,
                "draw_prob": draw_prob,
                "avg_spread": avg_spread,
                "avg_total": avg_total,
                "home_elo": home_elo,
                "away_elo": away_elo,
                "home_form": home_form,
                "away_form": away_form,
                "home_injuries": home_injuries,
                "away_injuries": away_injuries,
                "h2h_history": h2h_history,
                "home_stats": home_stats,
                "away_stats": away_stats,
                "home_news": home_news,
                "away_news": away_news,
                "home_adjusted": home_adjusted,
                "away_adjusted": away_adjusted,
                "weather": weather,
                "fatigue": fatigue,
                "bankroll": self.bankroll,
                "perf_stats": self._get_performance_stats(),
            }
            if draw_prob and avg_draw_price:
                context["avg_h2h"]["draw"] = avg_draw_price

            # V1/V2 need pre-formatted market_odds string
            if self.version != "v3":
                market_odds = f"""MONEYLINE (H2H):
Home: {avg_home_price} ({home_prob:.1%} implied)
Away: {avg_away_price} ({away_prob:.1%} implied)"""
                if draw_prob:
                    market_odds += f"\nDraw: {avg_draw_price} ({draw_prob:.1%} implied)"
                if avg_spread:
                    sp_home = self._american_to_probability(avg_spread["home_price"])
                    sp_away = self._american_to_probability(avg_spread["away_price"])
                    market_odds += f"\n\nSPREAD:\nHome {avg_spread['home_point']:+.1f}: {avg_spread['home_price']} ({sp_home:.1%} implied)\nAway {avg_spread['away_point']:+.1f}: {avg_spread['away_price']} ({sp_away:.1%} implied)"
                if avg_total:
                    t_over = self._american_to_probability(avg_total["over_price"])
                    t_under = self._american_to_probability(avg_total["under_price"])
                    market_odds += f"\n\nTOTAL:\nOver {avg_total['point']:.1f}: {avg_total['over_price']} ({t_over:.1%} implied)\nUnder {avg_total['point']:.1f}: {avg_total['under_price']} ({t_under:.1%} implied)"
                context["market_odds"] = market_odds

            prompt = self.model.build_game_prompt(game_data, context)
            max_tokens = 500 if self.version == "v3" else 800

            response = bedrock.invoke_model(
                modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                }),
            )
            result = json.loads(response["body"].read())
            content = result["content"][0]["text"]

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)
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

    def place_bet(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Place a virtual bet"""
        sport = opportunity["sport"]
        market = opportunity["market_key"]
        confidence = opportunity["confidence"]
        odds = opportunity.get("odds")

        # Delegate to model for threshold/sizing
        implied_prob = self._american_to_probability(float(odds)) if odds else 0.5
        if not self.model.should_bet(confidence, opportunity.get("expected_value", 0), implied_prob, sport, market):
            print(f"  Skipping: model rejected (conf={confidence:.2f}, ev={opportunity.get('expected_value', 0):.3f})")
            return {"success": False, "reason": "Model rejected"}
        bet_size = self.model.calculate_bet_size(confidence, float(odds) if odds else 0, self.bankroll)

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

        # Check minimum bet size
        min_bet = self.model.get_min_bet()
        if bet_size < min_bet:
            print(f"  Skipping: bet size ${bet_size:.2f} < minimum ${min_bet}")
            return {"success": False, "reason": f"Bet size below ${min_bet} minimum"}

        if bet_size > self.bankroll:
            return {"success": False, "reason": "Insufficient bankroll"}

        # Place bet via executor
        result = self.bet_executor.place_bet(
            opportunity, bet_size, self.bankroll, None
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

        # 1. Evaluate existing positions for cash-out/double-down (V1/V2 only)
        position_actions = self._manage_positions() if self.version != "v3" else {"cash_outs": 0, "double_downs": 0, "details": {"cash_outs": [], "double_downs": []}}

        # 2. Analyze all games and props
        game_opportunities = self.analyze_games()
        print(f"Found {len(game_opportunities)} game opportunities")

        prop_opportunities = []
        if self.bankroll > Decimal("20.00"):
            prop_opportunities = self.analyze_props()
            print(f"Found {len(prop_opportunities)} prop opportunities")

        # 3. Build and place parlays from prop opportunities
        parlay_bets = []
        total_bet = Decimal("0")
        if prop_opportunities:
            eligible = [o for o in prop_opportunities if o.get("confidence", 0) >= 0.70]
            game_ids = [o.get("game_id") for o in eligible]
            print(f"Parlay candidates: {len(eligible)} legs with ≥0.70 conf, {len(set(game_ids))} unique games")
            parlays = self.parlay_engine.build_parlays(prop_opportunities)

            # Load existing pending parlays to avoid duplicates
            existing_parlays = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk) & Key("sk").begins_with("BET#"),
                FilterExpression="bet_type = :parlay AND #status = :pending",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":parlay": "parlay", ":pending": "pending"},
            )
            existing_sigs = set()
            for item in existing_parlays.get("Items", []):
                legs = item.get("legs", [])
                sig = frozenset(
                    (l.get("game_id", ""), l.get("player", ""), l.get("market", ""), l.get("prediction", ""))
                    for l in legs
                )
                existing_sigs.add(sig)

            for parlay in parlays:
                if self.bankroll < Decimal("10.00"):
                    break
                # Check for duplicate parlay
                sig = frozenset(
                    (l.get("game_id", ""), l.get("player", ""), l.get("market", ""), l.get("prediction", ""))
                    for l in parlay["legs"]
                )
                if sig in existing_sigs:
                    print(f"  Skipping parlay: duplicate of existing pending parlay")
                    continue
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

        # 4. Combine and sort by expected value (best opportunities first)
        all_opportunities = game_opportunities + prop_opportunities
        all_opportunities.sort(
            key=lambda x: x.get("expected_value", 0), reverse=True
        )

        # 5. Place bets in priority order
        placed_bets = []

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

        result = {
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

        # Post-run: learning updates, feature analysis, variance tracking
        self.model.post_run(result)

        return result

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

    def _format_bet_for_dashboard(self, b: Dict) -> Dict:
        """Format a bet record for the dashboard API response."""
        is_parlay = b.get("bet_type") == "parlay"

        if is_parlay:
            legs = b.get("legs", [])
            leg_summaries = [
                f"{l.get('player', '')} {l.get('market', '')} {l.get('prediction', '')}".strip()
                for l in legs
            ]
            game = f"🎲 {len(legs)}-Leg Parlay"
            prediction = " + ".join(leg_summaries)
            confidence = float(b.get("combined_confidence", 0))
        else:
            game = (
                f"{b.get('player_name')} {b.get('market_key')}"
                if b.get("player_name")
                else f"{b.get('away_team')} @ {b.get('home_team')}"
            )
            prediction = b.get("prediction")
            confidence = float(b.get("final_confidence", b.get("confidence", 0)))

        result = {
            "bet_id": b.get("bet_id"),
            "game": game,
            "prediction": prediction,
            "market": b.get("market_key", "h2h"),
            "bet_type": "parlay" if is_parlay else "single",
            "ensemble_confidence": float(b.get("ensemble_confidence", b.get("confidence", confidence))),
            "final_confidence": confidence,
            "ai_reasoning": b.get("ai_reasoning", ""),
            "ai_key_factors": b.get("ai_key_factors", []),
            "bet_amount": float(b.get("bet_amount", 0)),
            "status": b.get("status"),
            "payout": float(b.get("payout", 0)),
            "placed_at": b.get("placed_at"),
            "expected_roi": None,
        }

        if is_parlay:
            result["legs"] = [
                {
                    "player": l.get("player"),
                    "market": l.get("market"),
                    "prediction": l.get("prediction"),
                    "odds": float(l.get("odds", 0)),
                    "status": l.get("status", "pending"),
                }
                for l in b.get("legs", [])
            ]
            result["combined_odds"] = b.get("combined_american_odds")
        elif b.get("expected_payout") and float(b.get("bet_amount", 0)) > 0:
            result["expected_roi"] = round(
                (float(b["expected_payout"]) - float(b["bet_amount"]))
                / float(b["bet_amount"]),
                3,
            )

        return result

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
                self._format_bet_for_dashboard(b)
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


def _send_consensus_email(table):
    """Compare today's V1 and V3 bets and send consensus report via SQS."""
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        v1_bets = _get_todays_bets(table, "BENNY", today)
        v3_bets = _get_todays_bets(table, "BENNY_V3", today)

        if not v1_bets and not v3_bets:
            print("No bets placed today, skipping consensus email")
            return

        # Match on game_id + market_key
        v1_by_key = {(b["game_id"], b["market_key"]): b for b in v1_bets}
        v3_by_key = {(b["game_id"], b["market_key"]): b for b in v3_bets}

        agree, v1_only, v3_only = [], [], []
        for key, b1 in v1_by_key.items():
            if key in v3_by_key:
                b3 = v3_by_key[key]
                same_pick = b1["prediction"] == b3["prediction"]
                entry = {
                    "pick": b1["prediction"],
                    "v1_conf": float(b1.get("confidence", 0)),
                    "v3_conf": float(b3.get("confidence", 0)),
                    "sport": b1.get("sport", ""),
                    "odds": float(b1.get("odds", 0)),
                    "same_pick": same_pick,
                }
                if not same_pick:
                    entry["v3_pick"] = b3["prediction"]
                agree.append(entry)
            else:
                v1_only.append(b1)
        for key, b3 in v3_by_key.items():
            if key not in v1_by_key:
                v3_only.append(b3)

        # Serialize bets for SQS (convert Decimal to float)
        def _serialize_bets(bets):
            serialized = []
            for b in bets:
                serialized.append({
                    "prediction": b.get("prediction", ""),
                    "sport": b.get("sport", ""),
                    "confidence": float(b.get("confidence", 0)),
                    "bet_amount": float(b.get("bet_amount", 0)),
                })
            return serialized

        queue_url = os.environ.get("NOTIFICATION_QUEUE_URL")
        if not queue_url:
            print("NOTIFICATION_QUEUE_URL not set, skipping consensus notification")
            return

        message = {
            "type": "consensus_report",
            "data": {
                "date": today,
                "agree": agree,
                "v1_only": _serialize_bets(v1_only),
                "v3_only": _serialize_bets(v3_only),
            },
        }

        sqs = boto3.client("sqs")
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
        print(f"Consensus report queued: {len(agree)} shared, {len(v1_only)} V1-only, {len(v3_only)} V3-only")
    except Exception as e:
        print(f"Failed to send consensus report: {e}")


def _get_todays_bets(table, pk, today):
    """Get non-parlay bets placed today for a given pk."""
    response = table.query(
        KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("BET#"),
        FilterExpression="begins_with(placed_at, :today) AND (attribute_not_exists(bet_type) OR bet_type <> :parlay)",
        ExpressionAttributeValues={":today": today, ":parlay": "parlay"},
    )
    return response.get("Items", [])


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

        print("\nRunning Benny v3...")
        trader_v3 = BennyTrader(version="v3")
        result_v3 = trader_v3.run_daily_analysis()
        print(f"Benny v3 complete: {result_v3}")

        # Send consensus notification
        _send_consensus_email(trader_v1.table)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        exit_code = 1
    finally:
        trader_v1._release_lock()

    sys.exit(exit_code)
