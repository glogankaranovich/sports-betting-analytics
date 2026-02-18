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
    BASE_MIN_CONFIDENCE = 0.65  # Base confidence threshold
    MAX_BET_PERCENTAGE = 0.20  # Max 20% of bankroll per bet

    def __init__(self, table_name=None):
        # Use module-level table for easier testing, or create new instance if table_name provided
        if table_name:
            self.table = dynamodb.Table(table_name)
        else:
            self.table = table
        self.bankroll = self._get_current_bankroll()
        self.week_start = self._get_week_start()
        self.learning_params = self._get_learning_parameters()

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
                ),  # Added to BASE_MIN_CONFIDENCE
                "kelly_fraction": Decimal("0.25"),  # Conservative Kelly (1/4 Kelly)
                "performance_by_sport": {},
                "performance_by_bet_type": {},
                "last_updated": datetime.utcnow().isoformat(),
            }
            self.table.put_item(Item=default_params)
            return default_params
        except Exception as e:
            print(f"Error loading learning parameters: {e}")
            return {
                "min_confidence_adjustment": 0.0,
                "kelly_fraction": 0.25,
                "performance_by_sport": {},
                "performance_by_bet_type": {},
            }

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
        """Update bankroll amount and store history"""
        self.bankroll = amount
        timestamp = datetime.utcnow().isoformat()

        # Update current bankroll
        self.table.put_item(
            Item={
                "pk": "BENNY",
                "sk": "BANKROLL",
                "amount": amount,
                "last_reset": self.week_start,
                "updated_at": timestamp,
            }
        )

        # Store history snapshot
        self.table.put_item(
            Item={
                "pk": "BENNY",
                "sk": f"BANKROLL#{timestamp}",
                "amount": amount,
                "updated_at": timestamp,
            }
        )

    def _get_top_models(self, sport: str, limit: int = 3) -> List[str]:
        """Get top performing models for a sport based on recent accuracy"""
        try:
            # Get all models for this sport by querying each model type
            all_models = [
                "consensus",
                "value",
                "momentum",
                "ensemble",
                "matchup",
                "contrarian",
                "hot_cold",
                "rest_schedule",
                "injury_aware",
            ]
            model_stats = {}

            for model in all_models:
                # Query recent verified predictions for this model+sport
                response = table.query(
                    IndexName="VerifiedAnalysisGSI",
                    KeyConditionExpression=Key("verified_analysis_pk").eq(
                        f"VERIFIED#{model}#{sport}#game"
                    ),
                    ScanIndexForward=False,
                    Limit=100,  # Last 100 predictions per model
                )

                predictions = response.get("Items", [])

                if len(predictions) < 10:  # Need at least 10 predictions
                    continue

                # Calculate accuracy
                correct = sum(1 for p in predictions if p.get("analysis_correct"))
                total = len(predictions)
                accuracy = correct / total if total > 0 else 0

                model_stats[model] = {"accuracy": accuracy, "total": total}

            # Sort by accuracy
            sorted_models = sorted(
                model_stats.items(),
                key=lambda x: (x[1]["accuracy"], x[1]["total"]),
                reverse=True,
            )
            top_models = [m[0] for m in sorted_models[:limit]]

            # Fallback to default models if not enough data
            if len(top_models) < limit:
                default_models = [
                    "ensemble",
                    "consensus",
                    "value",
                    "momentum",
                    "matchup",
                ]
                for model in default_models:
                    if model not in top_models:
                        top_models.append(model)
                    if len(top_models) >= limit:
                        break

            return top_models[:limit]

        except Exception as e:
            print(f"Error getting top models: {e}")
            # Fallback to safe defaults
            return ["ensemble", "consensus", "value"]

    def analyze_games(self) -> List[Dict[str, Any]]:
        """Analyze upcoming games independently using raw data and AI"""
        now = datetime.utcnow()
        three_days_out = now + timedelta(days=3)

        opportunities = []

        for sport in [
            "basketball_nba",
            "americanfootball_nfl",
            "baseball_mlb",
            "icehockey_nhl",
            "soccer_epl",
        ]:
            # Get upcoming games with odds
            response = self.table.query(
                IndexName="ActiveBetsIndexV2",
                KeyConditionExpression=Key("active_bet_pk").eq(f"GAME#{sport}")
                & Key("commence_time").between(now.isoformat(), three_days_out.isoformat()),
                FilterExpression="attribute_exists(latest) AND latest = :true AND market_key = :h2h",
                ExpressionAttributeValues={":true": True, ":h2h": "h2h"},
                Limit=50,
            )

            print(f"Checking {sport}: found {len(response.get('Items', []))} odds items")
            
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
                        "odds": [],
                    }

                # Extract odds from outcomes (only h2h markets)
                if item.get("market_key") != "h2h":
                    continue
                    
                outcomes = item.get("outcomes", [])
                if len(outcomes) >= 2:
                    odds_entry = {
                        "bookmaker": item.get("bookmaker"),
                        "home_price": None,
                        "away_price": None,
                    }
                    
                    # Handle 3-way markets (soccer) vs 2-way markets
                    home_team = item.get("home_team")
                    away_team = item.get("away_team")
                    
                    for outcome in outcomes:
                        if outcome.get("name") == home_team:
                            odds_entry["home_price"] = outcome.get("price")
                        elif outcome.get("name") == away_team:
                            odds_entry["away_price"] = outcome.get("price")
                    
                    # Only add if we found both home and away prices
                    if odds_entry["home_price"] and odds_entry["away_price"]:
                        games[game_id]["odds"].append(odds_entry)

            print(f"  Parsed {len(games)} unique games for {sport}")
            
            # Analyze each game with AI
            for game_id, game_data in games.items():
                if len(game_data["odds"]) < 2:  # Need at least 2 bookmakers
                    print(f"  Skipping {game_data['home_team']} vs {game_data['away_team']}: only {len(game_data['odds'])} bookmaker(s)")
                    continue

                print(f"  Analyzing {game_data['home_team']} vs {game_data['away_team']}")
                
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

                # Calculate average odds
                avg_home_price = sum(o["home_price"] for o in game_data["odds"]) / len(
                    game_data["odds"]
                )
                avg_away_price = sum(o["away_price"] for o in game_data["odds"]) / len(
                    game_data["odds"]
                )

                # Let AI analyze the data
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
                )

                # Use learned confidence threshold
                min_confidence = self.BASE_MIN_CONFIDENCE + float(
                    self.learning_params.get("min_confidence_adjustment", 0)
                )

                if analysis and float(analysis["confidence"]) >= min_confidence:
                    # Determine which team was predicted and get their odds
                    predicted_team = analysis["prediction"]
                    predicted_odds = None

                    if game_data["home_team"].lower() in predicted_team.lower():
                        predicted_odds = avg_home_price
                    elif game_data["away_team"].lower() in predicted_team.lower():
                        predicted_odds = avg_away_price

                    opportunities.append(
                        {
                            "game_id": game_id,
                            "sport": sport,
                            "home_team": game_data["home_team"],
                            "away_team": game_data["away_team"],
                            "prediction": analysis["prediction"],
                            "confidence": analysis["confidence"],
                            "reasoning": analysis["reasoning"],
                            "key_factors": analysis["key_factors"],
                            "commence_time": game_data["commence_time"],
                            "market_key": "h2h",
                            "odds": predicted_odds,
                        }
                    )

        return opportunities

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
    ) -> Dict[str, Any]:
        """Have AI analyze game data and make independent prediction"""
        try:
            # Calculate average odds across bookmakers
            avg_home_price = sum(o["home_price"] for o in game_data["odds"]) / len(
                game_data["odds"]
            )
            avg_away_price = sum(o["away_price"] for o in game_data["odds"]) / len(
                game_data["odds"]
            )

            # Convert to implied probabilities
            home_prob = self._american_to_probability(avg_home_price)
            away_prob = self._american_to_probability(avg_away_price)

            prompt = f"""You are Benny, an expert sports betting analyst. Analyze this game and make YOUR prediction.

Game: {game_data['away_team']} @ {game_data['home_team']}
Sport: {game_data['sport']}

ODDS:
Home: {avg_home_price} ({home_prob:.1%} implied)
Away: {avg_away_price} ({away_prob:.1%} implied)

TEAM STATS (Season):
Home: {json.dumps(home_stats, indent=2) if home_stats else 'No data'}
Away: {json.dumps(away_stats, indent=2) if away_stats else 'No data'}

RECENT FORM (Last 5 games):
Home: {home_form.get('record', 'Unknown')} - {home_form.get('streak', '')}
Away: {away_form.get('record', 'Unknown')} - {away_form.get('streak', '')}

HEAD-TO-HEAD (Last 3 meetings):
{json.dumps(h2h_history, indent=2) if h2h_history else 'No history'}

INJURIES:
Home: {json.dumps(home_injuries, indent=2) if home_injuries else 'None'}
Away: {json.dumps(away_injuries, indent=2) if away_injuries else 'None'}

NEWS SENTIMENT (Last 48 hours):
Home: Sentiment={home_news.get('sentiment_score', 0):.2f}, Impact={home_news.get('impact_score', 0):.1f}, Articles={home_news.get('news_count', 0)}
Away: Sentiment={away_news.get('sentiment_score', 0):.2f}, Impact={away_news.get('impact_score', 0):.1f}, Articles={away_news.get('news_count', 0)}

Analyze and predict:
1. Which team wins and why?
2. Is there value vs the odds?
3. Key factors driving your prediction?

Respond with JSON only:
{{"prediction": "Team Name", "confidence": 0.75, "reasoning": "Brief explanation", "key_factors": ["factor1", "factor2", "factor3"]}}"""

            response = bedrock.invoke_model(
                modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 600,
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

    def calculate_bet_size(self, confidence: float, odds: float = None) -> Decimal:
        """Calculate bet size using Kelly Criterion with learned parameters"""
        # Kelly Criterion: f = (bp - q) / b
        # where b = decimal odds - 1, p = win probability, q = 1 - p

        kelly_fraction = self.learning_params.get("kelly_fraction", 0.25)

        if odds and odds != 0:
            # Convert American odds to decimal
            if odds > 0:
                decimal_odds = (odds / 100) + 1
            else:
                decimal_odds = (100 / abs(odds)) + 1

            # Kelly formula
            b = decimal_odds - 1
            p = confidence
            q = 1 - p
            kelly_pct = (b * p - q) / b

            # Apply fractional Kelly for safety
            kelly_pct = max(0, kelly_pct * kelly_fraction)
        else:
            # Fallback: simple confidence-based sizing
            kelly_pct = (confidence - 0.5) * 2 * kelly_fraction

        max_bet = self.bankroll * Decimal(str(self.MAX_BET_PERCENTAGE))
        bet_size = self.bankroll * Decimal(str(kelly_pct))
        bet_size = min(bet_size, max_bet)
        bet_size = max(bet_size, Decimal("5.00"))  # Minimum $5 bet

        return bet_size.quantize(Decimal("0.01"))

    def update_learning_parameters(self):
        """Update Benny's learning parameters based on recent performance"""
        try:
            # Get recent settled bets (last 30 days)
            from datetime import timedelta

            cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()

            response = self.table.query(
                KeyConditionExpression=Key("pk").eq("BENNY#BETS"),
                FilterExpression="settled_at > :cutoff AND #status IN (:won, :lost)",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":cutoff": cutoff,
                    ":won": "won",
                    ":lost": "lost",
                },
            )

            bets = response.get("Items", [])
            if len(bets) < 10:  # Need at least 10 bets to learn
                return

            # Calculate overall win rate
            wins = sum(1 for b in bets if b.get("status") == "won")
            win_rate = wins / len(bets)

            # Adjust MIN_CONFIDENCE based on performance
            if win_rate > 0.60:
                # Performing well, can lower threshold slightly
                adjustment = -0.02
            elif win_rate < 0.45:
                # Performing poorly, raise threshold
                adjustment = 0.05
            else:
                # Acceptable performance, small adjustment toward 0
                current_adj = self.learning_params.get("min_confidence_adjustment", 0)
                adjustment = -current_adj * 0.1  # Slowly return to baseline

            # Calculate performance by sport and bet type
            perf_by_sport = {}
            perf_by_bet_type = {}

            for bet in bets:
                sport = bet.get("sport", "unknown")
                bet_type = bet.get("bet_type", "unknown")
                won = bet.get("status") == "won"

                if sport not in perf_by_sport:
                    perf_by_sport[sport] = {"wins": 0, "total": 0}
                perf_by_sport[sport]["total"] += 1
                if won:
                    perf_by_sport[sport]["wins"] += 1

                if bet_type not in perf_by_bet_type:
                    perf_by_bet_type[bet_type] = {"wins": 0, "total": 0}
                perf_by_bet_type[bet_type]["total"] += 1
                if won:
                    perf_by_bet_type[bet_type]["wins"] += 1

            # Update learning parameters
            self.learning_params.update(
                {
                    "min_confidence_adjustment": Decimal(str(adjustment)),
                    "performance_by_sport": perf_by_sport,
                    "performance_by_bet_type": perf_by_bet_type,
                    "overall_win_rate": Decimal(str(win_rate)),
                    "total_bets_analyzed": len(bets),
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )

            self.table.put_item(Item=self.learning_params)
            print(
                f"Updated Benny learning: win_rate={win_rate:.2%}, adjustment={adjustment:+.3f}"
            )

        except Exception as e:
            print(f"Error updating learning parameters: {e}")

    def place_bet(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Place a virtual bet"""
        # Benny already analyzed the game, just use that confidence
        confidence = opportunity["confidence"]
        odds = opportunity.get("odds")
        bet_size = self.calculate_bet_size(confidence, odds)

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
            "confidence": Decimal(str(confidence)),
            "ai_reasoning": opportunity["reasoning"],
            "ai_key_factors": opportunity["key_factors"],
            "bet_amount": bet_size,
            "market_key": opportunity["market_key"],
            "commence_time": opportunity["commence_time"],
            "placed_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "bankroll_before": self.bankroll,
            "odds": Decimal(str(opportunity.get("odds", 0)))
            if opportunity.get("odds")
            else None,
        }

        # Store bet
        self.table.put_item(Item=bet)

        # Also store as analysis record for outcome verification and leaderboard tracking
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
            "confidence": Decimal(str(confidence)),
            "reasoning": opportunity["reasoning"],
            "market_key": opportunity["market_key"],
            "commence_time": opportunity["commence_time"],
            "created_at": datetime.utcnow().isoformat(),
            "latest": True,
        }
        self.table.put_item(Item=analysis_record)

        # Update bankroll
        new_bankroll = self.bankroll - bet_size
        self._update_bankroll(new_bankroll)

        return {
            "success": True,
            "bet_id": bet_id,
            "bet_amount": float(bet_size),
            "remaining_bankroll": float(new_bankroll),
            "ai_reasoning": opportunity["reasoning"],
        }

    def run_daily_analysis(self) -> Dict[str, Any]:
        """Run daily analysis and place bets"""
        print(f"Starting Benny Trader analysis. Current bankroll: ${self.bankroll}")
        
        opportunities = self.analyze_games()
        print(f"Found {len(opportunities)} betting opportunities")

        bets_placed = []
        total_bet = Decimal("0")

        # Update learning parameters before analyzing
        self.update_learning_parameters()

        for opp in opportunities:
            # Don't bet if bankroll too low
            if self.bankroll < Decimal("10.00"):
                print(f"Bankroll too low (${self.bankroll}), stopping")
                break

            result = self.place_bet(opp)
            if result["success"]:
                bets_placed.append(result)
                total_bet += Decimal(str(result["bet_amount"]))
                print(f"Placed bet: {result['prediction']} for ${result['bet_amount']}")

        print(f"Analysis complete. Placed {len(bets_placed)} bets totaling ${total_bet}")
        
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
            KeyConditionExpression=Key("pk").eq("BENNY")
            & Key("sk").begins_with("BET#"),
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
            KeyConditionExpression=Key("pk").eq("BENNY")
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
