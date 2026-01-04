import boto3
import os
from typing import List, Dict, Any
from bet_recommendations import BetRecommendationEngine, RiskLevel
from recommendation_storage import RecommendationStorage


# Supported sports for recommendations
SUPPORTED_SPORTS = ["basketball_nba", "americanfootball_nfl"]


class RecommendationGenerator:
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.table = self.dynamodb.Table(table_name)
        self.engine = BetRecommendationEngine()
        self.storage = RecommendationStorage(table_name)

    def generate_all_recommendations(self) -> Dict[str, int]:
        """Generate recommendations for all sports/models/risk combinations"""
        results = {}

        # Get active sports
        sports = self._get_active_sports()
        models = ["consensus"]  # Start with consensus model
        risk_levels = [RiskLevel.CONSERVATIVE, RiskLevel.MODERATE, RiskLevel.AGGRESSIVE]

        for sport in sports:
            for model in models:
                for risk_level in risk_levels:
                    count = self._generate_recommendations_for_combination(
                        sport, model, risk_level
                    )
                    key = f"{sport}#{model}#{risk_level.value}"
                    results[key] = count

        return results

    def _generate_recommendations_for_combination(
        self, sport: str, model: str, risk_level: RiskLevel
    ) -> int:
        """Generate recommendations for a specific sport/model/risk combination"""
        print(f"Generating recommendations for {sport}#{model}#{risk_level.value}")

        # Get recent predictions for this sport
        predictions = self._get_recent_predictions(sport, model)
        print(f"Found {len(predictions)} predictions for {sport}")

        if not predictions:
            print(f"No predictions found for {sport}")
            return 0

        # Generate recommendations
        all_recommendations = []
        for pred_data in predictions:
            try:
                print(
                    f"Processing prediction: {pred_data.get('prediction', {}).get('game_id', 'unknown')}"
                )
                game_recs = self.engine.generate_game_recommendations(
                    pred_data["prediction"], pred_data["odds"]
                )
                print(f"Generated {len(game_recs)} recommendations from prediction")
                # Filter by risk level
                filtered_recs = [r for r in game_recs if r.risk_level == risk_level]
                all_recommendations.extend(filtered_recs)
            except Exception as e:
                print(
                    f"Error generating recommendations for {pred_data.get('game_id', 'unknown')}: {e}"
                )
                continue

        # Sort by expected value * confidence
        all_recommendations.sort(
            key=lambda r: r.expected_value * r.confidence_score, reverse=True
        )

        # Store top 10
        top_recommendations = all_recommendations[:10]
        if top_recommendations:
            self.storage.store_recommendations(
                sport, model, risk_level, top_recommendations
            )

        return len(top_recommendations)

    def _get_active_sports(self) -> List[str]:
        """Get list of supported sports"""
        print(f"Using supported sports: {SUPPORTED_SPORTS}")
        return SUPPORTED_SPORTS

    def _get_recent_predictions(self, sport: str, model: str) -> List[Dict[str, Any]]:
        """Get recent predictions for a sport/model combination"""
        try:
            # Query for game predictions
            response = self.table.scan(
                FilterExpression="begins_with(sk, :sk_prefix) AND sport = :sport",
                ExpressionAttributeValues={
                    ":sk_prefix": f"PREDICTION#{model}",
                    ":sport": sport,
                },
            )

            predictions = []
            for item in response.get("Items", []):
                # Convert DynamoDB item to prediction format
                pred_data = {
                    "game_id": item.get("pk", "").replace("PRED#GAME#", ""),
                    "prediction": {
                        "home_team": item.get("home_team", ""),
                        "away_team": item.get("away_team", ""),
                        "home_win_probability": float(
                            item.get("home_win_probability", 0.5)
                        ),
                        "away_win_probability": float(
                            item.get("away_win_probability", 0.5)
                        ),
                        "confidence_score": float(item.get("confidence_score", 0.5)),
                    },
                    "odds": self._extract_odds_from_item(item),
                }
                predictions.append(pred_data)

            return predictions

        except Exception as e:
            print(f"Error getting predictions for {sport}/{model}: {e}")
            return []

    def _extract_odds_from_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract odds data from DynamoDB item"""
        # This is a simplified version - adjust based on your actual odds structure
        return {
            "home_odds": float(item.get("home_odds", -110)),
            "away_odds": float(item.get("away_odds", -110)),
            "bookmaker": item.get("bookmaker", "DraftKings"),
        }


def lambda_handler(event, context):
    """Lambda handler for recommendation generation"""
    table_name = os.getenv("DYNAMODB_TABLE")
    if not table_name:
        return {
            "statusCode": 500,
            "body": "DYNAMODB_TABLE environment variable not set",
        }

    try:
        generator = RecommendationGenerator(table_name)
        results = generator.generate_all_recommendations()

        total_recommendations = sum(results.values())

        return {
            "statusCode": 200,
            "body": {
                "message": f"Generated {total_recommendations} recommendations",
                "results": results,
            },
        }

    except Exception as e:
        print(f"Error in recommendation generation: {str(e)}")
        return {"statusCode": 500, "body": {"error": str(e)}}
