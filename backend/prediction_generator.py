"""
Lambda function to generate predictions on schedule
"""

import json
import os
from prediction_tracker import PredictionTracker


def lambda_handler(event, context):
    """Generate and store predictions for specific sport, bet type, and model"""

    table_name = os.getenv("DYNAMODB_TABLE")
    if not table_name:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "DYNAMODB_TABLE environment variable not set"}
            ),
        }

    # Parse parameters from event
    sport = event.get("sport", "basketball_nba")  # Default to NBA
    bet_type = event.get("bet_type", "games")  # 'games' or 'props'
    model = event.get("model", "consensus")  # Default to consensus model
    limit = event.get("limit")  # Optional limit for testing

    try:
        tracker = PredictionTracker(table_name)

        if bet_type == "games":
            if sport:
                predictions_count = tracker.generate_game_predictions_for_sport(
                    sport, model, limit=limit
                )
            else:
                predictions_count = tracker.generate_game_predictions(
                    model, limit=limit
                )
        elif bet_type == "props":
            if sport:
                predictions_count = tracker.generate_prop_predictions_for_sport(
                    sport, model, limit=limit
                )
            else:
                predictions_count = tracker.generate_prop_predictions(
                    model, limit=limit
                )
        else:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": f'Invalid bet_type: {bet_type}. Must be "games" or "props"'
                    }
                ),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": f"Generated {predictions_count} {bet_type} predictions for {sport} using {model} model",
                    "sport": sport,
                    "bet_type": bet_type,
                    "model": model,
                    "limit": limit,
                    "predictions_count": predictions_count,
                }
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to generate predictions: {str(e)}"}),
        }
