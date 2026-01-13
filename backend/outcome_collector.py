import boto3
import requests
import os
from datetime import datetime
from typing import Dict, List, Any
from decimal import Decimal


class OutcomeCollector:
    def __init__(self, table_name: str, odds_api_key: str):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.table = self.dynamodb.Table(table_name)
        self.odds_api_key = odds_api_key
        self.base_url = "https://api.the-odds-api.com/v4"

    def collect_recent_outcomes(self, days_back: int = 7) -> Dict[str, int]:
        """Collect outcomes for games from the last N days"""
        results = {"updated_analysis": 0, "updated_insights": 0}

        # Get completed games from odds API
        completed_games = self._get_completed_games(days_back)

        for game in completed_games:
            try:
                # Update analysis with outcome
                analysis_updates = self._update_analysis_outcomes(game)
                results["updated_analysis"] += analysis_updates

                # Update insights with outcome
                insight_updates = self._update_insight_outcomes(game)
                results["updated_insights"] += insight_updates

            except Exception as e:
                print(f"Error processing game {game.get('id', 'unknown')}: {e}")
                continue

        return results

    def _get_completed_games(self, days_back: int) -> List[Dict[str, Any]]:
        """Get completed games from The Odds API"""
        completed_games = []
        sports = ["americanfootball_nfl", "basketball_nba"]

        for sport in sports:
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

    def _update_analysis_outcomes(self, game: Dict[str, Any]) -> int:
        """Update analysis records with actual outcomes"""
        updates = 0

        try:
            # Query for analyses for this game using the correct pattern
            # Analysis items have PK like "ANALYSIS#sport#game_id#bookmaker"
            response = self.table.scan(
                FilterExpression="begins_with(pk, :pk_prefix) AND game_id = :game_id",
                ExpressionAttributeValues={
                    ":pk_prefix": "ANALYSIS#",
                    ":game_id": game["id"],
                },
            )

            for item in response.get("Items", []):
                # Determine actual outcome based on analysis type
                if item.get("analysis_type") == "game":
                    home_won = self._determine_winner(game)

                    # Check if analysis was correct
                    analysis_result = item.get(
                        "prediction", ""
                    )  # Note: field is still called 'prediction' in DB
                    analysis_correct = self._check_game_analysis_accuracy(
                        analysis_result, home_won, game
                    )

                    # Update the analysis record
                    self.table.update_item(
                        Key={"pk": item["pk"], "sk": item["sk"]},
                        UpdateExpression="SET actual_home_won = :home_won, analysis_correct = :correct, outcome_verified_at = :verified",
                        ExpressionAttributeValues={
                            ":home_won": home_won,
                            ":correct": analysis_correct,
                            ":verified": datetime.utcnow().isoformat(),
                        },
                    )
                    updates += 1

                elif item.get("analysis_type") == "prop":
                    # For props, we'd need actual player stats (not implemented yet)
                    # For now, just mark as verified without accuracy check
                    self.table.update_item(
                        Key={"pk": item["pk"], "sk": item["sk"]},
                        UpdateExpression="SET outcome_verified_at = :verified, analysis_correct = :correct",
                        ExpressionAttributeValues={
                            ":verified": datetime.utcnow().isoformat(),
                            ":correct": False,  # Default until we implement prop verification
                        },
                    )
                    updates += 1

        except Exception as e:
            print(f"Error updating analyses for game {game['id']}: {e}")

        return updates

    def _check_game_analysis_accuracy(
        self, analysis_result: str, home_won: bool, game: Dict[str, Any]
    ) -> bool:
        """Check if a game analysis was accurate"""
        try:
            analysis_lower = analysis_result.lower()
            home_team = game.get("home_team", "").lower()
            away_team = game.get("away_team", "").lower()

            # Check if analysis mentions home team winning
            if home_team in analysis_lower and (
                "+" in analysis_result or "win" in analysis_lower
            ):
                return home_won
            elif away_team in analysis_lower and (
                "+" in analysis_result or "win" in analysis_lower
            ):
                return not home_won
            else:
                # For spread analysis, we'd need the actual spread result
                # For now, default to checking team names
                if home_team in analysis_lower:
                    return home_won
                elif away_team in analysis_lower:
                    return not home_won
                else:
                    return False  # Can't determine

        except Exception as e:
            print(f"Error checking analysis accuracy: {e}")
            return False

    def _update_insight_outcomes(self, game: Dict[str, Any]) -> int:
        """Update insight records with actual outcomes"""
        updates = 0

        try:
            # Query for insights for this game
            response = self.table.scan(
                FilterExpression="begins_with(pk, :pk_prefix) AND game_id = :game_id",
                ExpressionAttributeValues={
                    ":pk_prefix": "INSIGHT#",
                    ":game_id": game["id"],
                },
            )

            for item in response.get("Items", []):
                # Determine if the insight won
                home_won = self._determine_winner(game)
                bet_won = self._determine_bet_outcome(item, home_won)

                # Calculate ROI if bet won
                roi = self._calculate_roi(item, bet_won)

                # Update the insight record
                self.table.update_item(
                    Key={"pk": item["pk"], "sk": item["sk"]},
                    UpdateExpression="SET actual_outcome = :outcome, bet_won = :won, actual_roi = :roi, outcome_verified_at = :verified",
                    ExpressionAttributeValues={
                        ":outcome": home_won,
                        ":won": bet_won,
                        ":roi": Decimal(str(roi)),
                        ":verified": datetime.utcnow().isoformat(),
                    },
                )
                updates += 1

        except Exception as e:
            print(f"Error updating insights for game {game['id']}: {e}")

        return updates

    def _determine_winner(self, game: Dict[str, Any]) -> bool:
        """Determine if home team won"""
        home_score = game.get("home_score")
        away_score = game.get("away_score")

        if home_score is None or away_score is None:
            return False  # Default if scores unavailable

        return int(home_score) > int(away_score)

    def _determine_bet_outcome(self, insight: Dict[str, Any], home_won: bool) -> bool:
        """Determine if the recommended bet won"""
        bet_type = insight.get("bet_type", "")
        team_or_player = insight.get("team_or_player", "")

        # Simple moneyline logic (expand for other bet types)
        if bet_type == "moneyline":
            if "home" in team_or_player.lower():
                return home_won
            else:
                return not home_won

        # Default to False for unsupported bet types
        return False

    def _calculate_roi(self, insight: Dict[str, Any], bet_won: bool) -> float:
        """Calculate ROI for the insight"""
        if not bet_won:
            return -1.0  # Lost entire bet

        bet_amount = float(insight.get("recommended_bet_amount", 0))
        potential_payout = float(insight.get("potential_payout", 0))

        if bet_amount == 0:
            return 0.0

        profit = potential_payout - bet_amount
        return profit / bet_amount

    def _map_sport_name(self, api_sport: str) -> str:
        """Map API sport names to our internal names"""
        mapping = {"americanfootball_nfl": "NFL", "basketball_nba": "NBA"}
        return mapping.get(api_sport, api_sport)


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

    import json

    secret_data = json.loads(response["SecretString"])
    return secret_data.get("api_key", "")
