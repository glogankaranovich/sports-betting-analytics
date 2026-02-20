import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

import boto3
import requests
from boto3.dynamodb.conditions import Key

from constants import SUPPORTED_SPORTS, SYSTEM_MODELS
from elo_calculator import EloCalculator


class OutcomeCollector:
    def __init__(self, table_name: str, odds_api_key: str):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.table = self.dynamodb.Table(table_name)
        self.odds_api_key = odds_api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.elo_calculator = EloCalculator()

    def collect_recent_outcomes(self, days_back: int = 3) -> Dict[str, int]:
        """Collect outcomes for games from the last N days (max 3)"""
        results = {
            "updated_analysis": 0,
            "stored_outcomes": 0,
            "stored_prop_outcomes": 0,
            "updated_elo": 0,
        }

        # Validate days_back (API only accepts 1-3)
        if days_back < 1 or days_back > 3:
            days_back = 3

        # Get completed games from odds API
        completed_games = self._get_completed_games(days_back)

        for game in completed_games:
            try:
                # Store game outcome for H2H queries
                self._store_outcome(game)
                results["stored_outcomes"] += 1

                # Update Elo ratings
                if self._update_elo_ratings(game):
                    results["updated_elo"] += 1

                # Store prop outcomes for player tracking
                prop_count = self._store_prop_outcomes(game)
                results["stored_prop_outcomes"] += prop_count

                # Update analysis with outcome
                analysis_updates = self._update_analysis_outcomes(game)
                results["updated_analysis"] += analysis_updates

            except Exception as e:
                print(f"Error processing game {game.get('id', 'unknown')}: {e}")
                continue

        return results

    def _get_completed_games(self, days_back: int) -> List[Dict[str, Any]]:
        """Get completed games from The Odds API"""
        completed_games = []

        for sport in SUPPORTED_SPORTS:
            try:
                # Get scores for completed games
                url = f"{self.base_url}/sports/{sport}/scores"
                params = {"apiKey": self.odds_api_key, "daysFrom": days_back}

                response = requests.get(url, params=params)
                response.raise_for_status()

                games = response.json()
                for game in games:
                    if game.get("completed", False):
                        completed_games.append(
                            {
                                "id": game["id"],
                                "sport": self._map_sport_name(sport),
                                "home_team": game["home_team"],
                                "away_team": game["away_team"],
                                "home_score": game.get("scores", [{}])[0].get("score"),
                                "away_score": game.get("scores", [{}])[1].get("score")
                                if len(game.get("scores", [])) > 1
                                else None,
                                "completed_at": game.get("last_update"),
                            }
                        )

            except Exception as e:
                print(f"Error fetching scores for {sport}: {e}")
                continue

        return completed_games
    
    def _update_elo_ratings(self, game: Dict[str, Any]) -> bool:
        """Update Elo ratings for completed game"""
        try:
            sport = game.get("sport")
            home_team = game.get("home_team")
            away_team = game.get("away_team")
            home_score = game.get("home_score")
            away_score = game.get("away_score")
            
            if not all([sport, home_team, away_team, home_score is not None, away_score is not None]):
                return False
            
            self.elo_calculator.update_ratings(sport, home_team, away_team, int(home_score), int(away_score))
            return True
        except Exception as e:
            print(f"Error updating Elo ratings: {e}")
            return False

    def _store_outcome(self, game: Dict[str, Any]) -> None:
        """Store game outcome as separate record for H2H queries"""
        try:
            home_score = int(game.get("home_score", 0))
            away_score = int(game.get("away_score", 0))
            winner = game["home_team"] if home_score > away_score else game["away_team"]

            # Normalize team names for consistent H2H queries
            home_normalized = game["home_team"].lower().replace(" ", "_")
            away_normalized = game["away_team"].lower().replace(" ", "_")

            # Sort teams alphabetically for consistent H2H key
            teams_sorted = sorted([home_normalized, away_normalized])
            h2h_pk = f"H2H#{game['sport']}#{teams_sorted[0]}#{teams_sorted[1]}"
            completed_at = game.get("completed_at", datetime.utcnow().isoformat())

            # Store main outcome + team-specific records
            self.table.put_item(
                Item={
                    "pk": f"OUTCOME#{game['sport']}#{game['id']}",
                    "sk": "RESULT",
                    "game_id": game["id"],
                    "sport": game["sport"],
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],
                    "home_score": Decimal(str(home_score)),
                    "away_score": Decimal(str(away_score)),
                    "winner": winner,
                    "completed_at": completed_at,
                    "h2h_pk": h2h_pk,
                    "h2h_sk": completed_at,
                }
            )

            # Store team-specific records for recent form queries
            for team, team_norm in [
                (game["home_team"], home_normalized),
                (game["away_team"], away_normalized),
            ]:
                self.table.put_item(
                    Item={
                        "pk": f"TEAM_OUTCOME#{game['sport']}#{team_norm}",
                        "sk": f"{completed_at}#{game['id']}",
                        "team_outcome_pk": f"TEAM#{game['sport']}#{team_norm}",
                        "completed_at": completed_at,
                        "game_id": game["id"],
                        "sport": game["sport"],
                        "team": team,
                        "opponent": game["away_team"]
                        if team == game["home_team"]
                        else game["home_team"],
                        "team_score": Decimal(
                            str(home_score if team == game["home_team"] else away_score)
                        ),
                        "opponent_score": Decimal(
                            str(away_score if team == game["home_team"] else home_score)
                        ),
                        "winner": winner,
                        "is_home": team == game["home_team"],
                    }
                )

            print(
                f"Stored outcome: {game['home_team']} {home_score} - {away_score} {game['away_team']}"
            )

        except Exception as e:
            print(f"Error storing outcome for game {game.get('id')}: {e}")
            raise

    def _store_prop_outcomes(self, game: Dict[str, Any]) -> int:
        """Store prop outcomes for player performance tracking"""
        try:
            game_id = game["id"]
            sport = game["sport"]

            # Query for player stats from this game
            response = self.table.query(
                IndexName="GameIndex",
                KeyConditionExpression="game_index_pk = :game_id",
                ExpressionAttributeValues={":game_id": game_id},
            )

            stored_count = 0
            for item in response.get("Items", []):
                # Only process player stats records
                if not item.get("pk", "").startswith("PLAYER_STATS"):
                    continue

                player_name = item.get("player_name")
                stats = item.get("stats", {})

                if not player_name or not stats:
                    continue

                # Store outcomes for common prop markets
                prop_markets = {
                    "player_points": "PTS",
                    "player_rebounds": "REB",
                    "player_assists": "AST",
                    "player_threes": "3PM",
                }

                for market_key, stat_field in prop_markets.items():
                    actual_value = stats.get(stat_field)
                    if actual_value is None:
                        continue

                    # Normalize player name for PK
                    player_normalized = player_name.lower().replace(" ", "_")

                    self.table.put_item(
                        Item={
                            "pk": f"PROP_OUTCOME#{sport}#{game_id}#{player_normalized}",
                            "sk": f"RESULT#{market_key}",
                            "game_id": game_id,
                            "sport": sport,
                            "player_name": player_name,
                            "market_key": market_key,
                            "actual_value": Decimal(str(actual_value)),
                            "completed_at": game.get(
                                "completed_at", datetime.utcnow().isoformat()
                            ),
                            "game_index_pk": game_id,
                            "game_index_sk": f"PROP_OUTCOME#{sport}#{player_normalized}#{market_key}",
                        }
                    )
                    stored_count += 1

            if stored_count > 0:
                print(f"Stored {stored_count} prop outcomes for game {game_id}")

            return stored_count

        except Exception as e:
            print(f"Error storing prop outcomes for game {game.get('id')}: {e}")
            return 0

    def _update_analysis_outcomes(self, game: Dict[str, Any]) -> int:
        """Update analysis records with actual outcomes"""
        updates = 0
        sport = game["sport"]
        game_id = game["id"]

        try:
            # Query AnalysisTimeGSI for each model/bet_type combination
            models = SYSTEM_MODELS
            bet_types = ["game", "prop"]
            bookmakers = ["fanduel"]

            for model in models:
                for bet_type in bet_types:
                    for bookmaker in bookmakers:
                        pk = f"ANALYSIS#{sport}#{bookmaker}#{model}#{bet_type}"

                        response = self.table.query(
                            IndexName="AnalysisTimeGSI",
                            KeyConditionExpression="analysis_time_pk = :pk",
                            FilterExpression="game_id = :game_id",
                            ExpressionAttributeValues={
                                ":pk": pk,
                                ":game_id": game_id,
                            },
                        )

                        items = response.get("Items", [])
                        updates += self._process_analysis_items(items, game)

                        # Also verify inverse predictions
                        updates += self._verify_inverse_predictions(items, game)

            # Settle Benny bets for this game
            self._settle_benny_bets(game)

            # Archive odds to historical records
            self._archive_game_odds(game)

        except Exception as e:
            print(f"Error updating analyses for game {game['id']}: {e}")

        return updates

    def _verify_inverse_predictions(
        self, original_items: List[Dict[str, Any]], game: Dict[str, Any]
    ) -> int:
        """Verify inverse predictions for the given original predictions"""
        updates = 0

        try:
            for original_item in original_items:
                # Find corresponding inverse prediction
                inverse_sk = original_item.get("sk", "").replace("#LATEST", "#INVERSE")

                try:
                    inverse_response = self.table.get_item(
                        Key={"pk": original_item["pk"], "sk": inverse_sk}
                    )

                    if "Item" not in inverse_response:
                        continue

                    inverse_item = inverse_response["Item"]

                    # Verify inverse prediction
                    if inverse_item.get("analysis_type") == "game":
                        home_won = self._determine_winner(game)
                        inverse_correct = self._check_game_analysis_accuracy(
                            inverse_item.get("prediction", ""), home_won, game
                        )

                        verified_at = datetime.utcnow().isoformat()
                        model = inverse_item.get("model", "consensus")
                        sport = inverse_item.get("sport")
                        verified_pk = f"VERIFIED#{model}#{sport}#game#inverse"

                        self.table.update_item(
                            Key={"pk": inverse_item["pk"], "sk": inverse_item["sk"]},
                            UpdateExpression="SET actual_home_won = :home_won, analysis_correct = :correct, outcome_verified_at = :verified, verified_analysis_pk = :vpk, verified_analysis_sk = :vsk",
                            ExpressionAttributeValues={
                                ":home_won": home_won,
                                ":correct": inverse_correct,
                                ":verified": verified_at,
                                ":vpk": verified_pk,
                                ":vsk": verified_at,
                            },
                        )
                        updates += 1

                        print(
                            f"Verified inverse: {model} - Original: {original_item.get('analysis_correct', 'unknown')}, Inverse: {inverse_correct}"
                        )

                    elif inverse_item.get("analysis_type") == "prop":
                        prop_correct = self._check_prop_analysis_accuracy(
                            inverse_item, game
                        )

                        verified_at = datetime.utcnow().isoformat()
                        model = inverse_item.get("model", "consensus")
                        sport = inverse_item.get("sport")
                        verified_pk = f"VERIFIED#{model}#{sport}#prop#inverse"

                        self.table.update_item(
                            Key={"pk": inverse_item["pk"], "sk": inverse_item["sk"]},
                            UpdateExpression="SET outcome_verified_at = :verified, analysis_correct = :correct, verified_analysis_pk = :vpk, verified_analysis_sk = :vsk",
                            ExpressionAttributeValues={
                                ":verified": verified_at,
                                ":correct": prop_correct,
                                ":vpk": verified_pk,
                                ":vsk": verified_at,
                            },
                        )
                        updates += 1

                except Exception as e:
                    print(f"Error verifying inverse prediction: {e}")
                    continue

        except Exception as e:
            print(f"Error in _verify_inverse_predictions: {e}")

        return updates

    def _process_analysis_items(
        self, items: List[Dict[str, Any]], game: Dict[str, Any]
    ) -> int:
        """Process analysis items and update with outcomes"""
        updates = 0

        for item in items:
            # Determine actual outcome based on analysis type
            if item.get("analysis_type") == "game":
                home_won = self._determine_winner(game)

                # Check if analysis was correct
                analysis_result = item.get("prediction", "")
                analysis_correct = self._check_game_analysis_accuracy(
                    analysis_result, home_won, game
                )

                verified_at = datetime.utcnow().isoformat()
                model = item.get("model", "consensus")
                sport = item.get("sport")
                verified_pk = f"VERIFIED#{model}#{sport}#game"

                # Update the analysis record
                self.table.update_item(
                    Key={"pk": item["pk"], "sk": item["sk"]},
                    UpdateExpression="SET actual_home_won = :home_won, analysis_correct = :correct, outcome_verified_at = :verified, verified_analysis_pk = :vpk, verified_analysis_sk = :vsk",
                    ExpressionAttributeValues={
                        ":home_won": home_won,
                        ":correct": analysis_correct,
                        ":verified": verified_at,
                        ":vpk": verified_pk,
                        ":vsk": verified_at,
                    },
                )
                updates += 1

            elif item.get("analysis_type") == "prop":
                # Get player stats for prop verification
                prop_correct = self._check_prop_analysis_accuracy(item, game)

                print(
                    f"Prop verification: {item.get('player_name')} {item.get('market_key')} {item.get('prediction')} = {prop_correct}"
                )

                verified_at = datetime.utcnow().isoformat()
                model = item.get("model", "consensus")
                sport = item.get("sport")
                verified_pk = f"VERIFIED#{model}#{sport}#prop"

                self.table.update_item(
                    Key={"pk": item["pk"], "sk": item["sk"]},
                    UpdateExpression="SET outcome_verified_at = :verified, analysis_correct = :correct, verified_analysis_pk = :vpk, verified_analysis_sk = :vsk",
                    ExpressionAttributeValues={
                        ":verified": verified_at,
                        ":correct": prop_correct,
                        ":vpk": verified_pk,
                        ":vsk": verified_at,
                    },
                )
                updates += 1

        return updates

    def _check_game_analysis_accuracy(
        self, analysis_result: str, home_won: bool, game: Dict[str, Any]
    ) -> bool:
        """Check if a game analysis was accurate"""
        try:
            home_score = int(game.get("home_score", 0))
            away_score = int(game.get("away_score", 0))

            analysis_lower = analysis_result.lower()
            home_team = game.get("home_team", "").lower()
            away_team = game.get("away_team", "").lower()

            # Check for spread bets (e.g., "Team +7.5" or "Team -3.5")
            if "+" in analysis_result or "-" in analysis_result:
                # Extract spread value
                import re

                spread_match = re.search(r"([+-]\d+\.?\d*)", analysis_result)
                if spread_match:
                    spread = float(spread_match.group(1))

                    # Determine which team has the spread
                    if home_team in analysis_lower:
                        # Home team with spread
                        adjusted_score = home_score + spread
                        return adjusted_score > away_score
                    elif away_team in analysis_lower:
                        # Away team with spread
                        adjusted_score = away_score + spread
                        return adjusted_score > home_score

            # Check for totals (over/under)
            if "over" in analysis_lower or "under" in analysis_lower:
                total_score = home_score + away_score
                # Extract total value
                import re

                total_match = re.search(r"(\d+\.?\d*)", analysis_result)
                if total_match:
                    line = float(total_match.group(1))
                    if "over" in analysis_lower:
                        return total_score > line
                    else:  # under
                        return total_score < line

            # Moneyline - simple win/loss
            if home_team in analysis_lower:
                return home_won
            elif away_team in analysis_lower:
                return not home_won

            return False  # Can't determine

        except Exception as e:
            print(f"Error checking analysis accuracy: {e}")
            return False

    def _check_prop_analysis_accuracy(
        self, analysis: Dict[str, Any], game: Dict[str, Any]
    ) -> bool:
        """Check if a prop analysis was accurate using player stats"""
        try:
            # Extract prop details from analysis
            market_key = analysis.get("market_key", "")
            prop_type = market_key.replace(
                "player_", ""
            )  # e.g., "player_assists" -> "assists"
            player_name = analysis.get("player_name", "")
            prediction = analysis.get("prediction", "")

            # Extract line from prediction (e.g., "Under 6.5" -> 6.5)
            import re

            line_match = re.search(r"(\d+\.?\d*)", prediction)
            if not line_match:
                return False
            line = float(line_match.group(1))
            prediction_lower = prediction.lower()

            # Query for player stats for this game
            game_id = game["id"]
            sport = game["sport"]

            # Normalize player name to match storage format
            normalized_name = player_name.lower().replace(" ", "_")
            player_pk = f"PLAYER_STATS#{sport}#{normalized_name}"
            print(
                f"Querying for player stats with game_id: {game_id}, player: {player_pk}"
            )

            # Look for player stats in DynamoDB using GameIndex GSI
            response = self.table.query(
                IndexName="GameIndex",
                KeyConditionExpression="game_index_pk = :game_id AND game_index_sk = :player_pk",
                ExpressionAttributeValues={
                    ":game_id": game_id,
                    ":player_pk": player_pk,
                },
            )

            print(f"Query returned {len(response.get('Items', []))} items")

            # Check if we found the player's stats
            if response.get("Items"):
                item = response["Items"][0]
                stats = item.get("stats", {})

                print(f"Found stats for {player_name}: {stats}")

                # Map prop type to stat field
                stat_value = self._get_stat_value(stats, prop_type)

                print(
                    f"Prop type: {prop_type}, Stat value: {stat_value}, Line: {line}, Prediction: {prediction_lower}"
                )

                if stat_value is not None:
                    # Check if prediction was correct
                    if "over" in prediction_lower:
                        result = stat_value > line
                        print(f"Over check: {stat_value} > {line} = {result}")
                        return result
                    elif "under" in prediction_lower:
                        result = stat_value < line
                        print(f"Under check: {stat_value} < {line} = {result}")
                        return result

            return False  # Can't verify without stats

        except Exception as e:
            print(f"Error checking prop analysis accuracy: {e}")
            return False

    def _get_stat_value(self, stats: Dict[str, Any], prop_type: str) -> float:
        """Extract stat value from player stats based on prop type"""
        prop_mapping = {
            "points": "PTS",
            "rebounds": "REB",
            "assists": "AST",
            "threes": "3PM",
            "steals": "STL",
            "blocks": "BLK",
            "turnovers": "TO",
        }

        stat_key = prop_mapping.get(prop_type.lower())
        if stat_key and stat_key in stats:
            try:
                return float(stats[stat_key])
            except (ValueError, TypeError):
                return None

        return None

    def _determine_winner(self, game: Dict[str, Any]) -> bool:
        """Determine if home team won"""
        home_score = game.get("home_score")
        away_score = game.get("away_score")

        if home_score is None or away_score is None:
            return False  # Default if scores unavailable

        return int(home_score) > int(away_score)

    def _map_sport_name(self, api_sport: str) -> str:
        """Keep sport names consistent with storage format"""
        return api_sport

    def _settle_benny_bets(self, game: Dict[str, Any]) -> None:
        """Settle Benny bets for a completed game"""
        try:
            game_id = game["id"]

            # Query for Benny bets on this game
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                FilterExpression="game_id = :game_id AND #status = :pending",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":pk": "BENNY",
                    ":game_id": game_id,
                    ":pending": "pending",
                },
            )

            bets = response.get("Items", [])
            if not bets:
                return

            # Get current bankroll
            bankroll_response = self.table.get_item(
                Key={"pk": "BENNY", "sk": "BANKROLL"}
            )
            current_bankroll = Decimal(
                str(bankroll_response.get("Item", {}).get("amount", "100.00"))
            )

            for bet in bets:
                bet_amount = Decimal(str(bet.get("bet_amount", 0)))
                prediction = bet.get("prediction", "")
                odds = bet.get("odds")

                # Determine if bet won using improved matching
                bet_won = self._check_bet_outcome(
                    prediction,
                    game["home_team"],
                    game["away_team"],
                    self._determine_winner(game),
                    game,
                )

                # Calculate payout using actual odds
                if bet_won:
                    if odds:
                        # Use actual American odds
                        odds_value = float(odds)
                        if odds_value > 0:
                            # Positive odds: profit = (bet * odds) / 100
                            profit = (
                                bet_amount * Decimal(str(odds_value)) / Decimal("100")
                            )
                        else:
                            # Negative odds: profit = bet / (abs(odds) / 100)
                            profit = bet_amount / (
                                Decimal(str(abs(odds_value))) / Decimal("100")
                            )
                        payout = bet_amount + profit
                    else:
                        # Fallback to even money if no odds stored
                        profit = bet_amount
                        payout = bet_amount * Decimal("2.0")
                    new_status = "won"
                else:
                    payout = Decimal("0")
                    profit = -bet_amount
                    new_status = "lost"

                # Update bet record
                self.table.update_item(
                    Key={"pk": bet["pk"], "sk": bet["sk"]},
                    UpdateExpression="SET #status = :status, payout = :payout, profit = :profit, settled_at = :settled",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": new_status,
                        ":payout": payout,
                        ":profit": profit,
                        ":settled": datetime.utcnow().isoformat(),
                    },
                )

                # Update bankroll
                current_bankroll += payout

                print(
                    f"Settled Benny bet: {prediction} = {new_status} (${profit}, odds: {odds})"
                )

            # Save updated bankroll
            bankroll_item = bankroll_response.get("Item", {})
            self.table.put_item(
                Item={
                    "pk": "BENNY",
                    "sk": "BANKROLL",
                    "amount": current_bankroll,
                    "last_reset": bankroll_item.get(
                        "last_reset", datetime.utcnow().isoformat()
                    ),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )

            print(f"Updated Benny bankroll: ${current_bankroll}")

        except Exception as e:
            print(f"Error settling Benny bets for game {game.get('id')}: {e}")
            import traceback

            traceback.print_exc()

    def _check_bet_outcome(
        self,
        prediction: str,
        home_team: str,
        away_team: str,
        home_won: bool,
        game: Dict[str, Any],
    ) -> bool:
        """Check if a bet won with improved team name matching"""
        try:
            prediction_lower = prediction.lower().strip()
            home_lower = home_team.lower().strip()
            away_lower = away_team.lower().strip()

            # Normalize team names for better matching
            def normalize_team(team: str) -> str:
                """Extract key parts of team name"""
                # Remove common prefixes/suffixes
                team = team.replace("the ", "")
                # Get last word (usually the team name)
                parts = team.split()
                return parts[-1] if parts else team

            home_normalized = normalize_team(home_lower)
            away_normalized = normalize_team(away_lower)
            prediction_normalized = normalize_team(prediction_lower)

            # Check for spread bets
            if "+" in prediction or "-" in prediction:
                return self._check_game_analysis_accuracy(prediction, home_won, game)

            # Check for totals
            if "over" in prediction_lower or "under" in prediction_lower:
                return self._check_game_analysis_accuracy(prediction, home_won, game)

            # Moneyline - check multiple matching strategies
            # Strategy 1: Full name match
            if home_lower in prediction_lower:
                return home_won
            if away_lower in prediction_lower:
                return not home_won

            # Strategy 2: Normalized name match (last word)
            if home_normalized in prediction_normalized:
                return home_won
            if away_normalized in prediction_normalized:
                return not home_won

            # Strategy 3: Prediction contains team name
            if prediction_normalized in home_normalized:
                return home_won
            if prediction_normalized in away_normalized:
                return not home_won

            # Could not determine - log warning
            print(
                f"WARNING: Could not match prediction '{prediction}' to teams '{home_team}' vs '{away_team}'"
            )
            return False

        except Exception as e:
            print(f"Error checking bet outcome: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _archive_game_odds(self, game: Dict[str, Any]) -> None:
        """Archive odds for completed game to historical records"""
        try:
            game_id = game.get("id")
            if not game_id:
                return

            print(f"Archiving odds for completed game: {game_id}")

            # Query all odds for this game
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(f"GAME#{game_id}")
            )

            items = response.get("Items", [])
            archived_count = 0

            for item in items:
                sk = item.get("sk", "")

                # Skip if already historical or if it's a non-odds record
                if sk.startswith("HISTORICAL#") or "LATEST" not in sk:
                    continue

                # Create historical record
                historical_item = {**item}
                historical_item["pk"] = f"HISTORICAL_ODDS#{game_id}"
                historical_item["sk"] = sk.replace("#LATEST", "")
                historical_item["archived_at"] = datetime.utcnow().isoformat()

                # Remove active_bet_pk if present (no longer active)
                historical_item.pop("active_bet_pk", None)

                # Store historical record
                self.table.put_item(Item=historical_item)
                archived_count += 1

            print(f"Archived {archived_count} odds records for game {game_id}")

        except Exception as e:
            print(f"Error archiving odds for game {game.get('id')}: {e}")


def lambda_handler(event, context):
    """Lambda handler for outcome collection"""
    table_name = os.getenv("DYNAMODB_TABLE")
    secret_arn = os.getenv("ODDS_API_SECRET_ARN")

    if not table_name or not secret_arn:
        return {"statusCode": 500, "body": "Missing required environment variables"}

    try:
        # Get API key from Secrets Manager
        odds_api_key = _get_secret_value(secret_arn)

        collector = OutcomeCollector(table_name, odds_api_key)
        results = collector.collect_recent_outcomes()

        return {
            "statusCode": 200,
            "body": {"message": "Outcome collection completed", "results": results},
        }

    except Exception as e:
        print(f"Error in outcome collection: {str(e)}")
        return {"statusCode": 500, "body": {"error": str(e)}}


def _get_secret_value(secret_arn: str) -> str:
    """Get secret value from AWS Secrets Manager"""
    import boto3

    secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
    response = secrets_client.get_secret_value(SecretId=secret_arn)

    # Secret is stored as plain string, not JSON
    return response["SecretString"]
