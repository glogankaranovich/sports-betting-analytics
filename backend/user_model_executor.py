"""
User Model Executor - Processes user models from SQS queue and generates predictions
"""
import json
import os
from typing import Dict, List
import boto3
from user_models import UserModel, ModelPrediction

dynamodb = boto3.resource("dynamodb")
BETS_TABLE = os.environ.get("BETS_TABLE", "carpool-bets-v2-dev")
bets_table = dynamodb.Table(BETS_TABLE)


def evaluate_team_stats(game_data: Dict) -> float:
    """
    Evaluate team stats data source
    Returns normalized score 0-1
    """
    # TODO: Implement actual team stats evaluation
    # For now, return placeholder
    return 0.5


def evaluate_odds_movement(game_data: Dict) -> float:
    """
    Evaluate odds movement data source
    Returns normalized score 0-1
    """
    # TODO: Implement actual odds movement evaluation
    # For now, return placeholder
    return 0.5


def evaluate_recent_form(game_data: Dict) -> float:
    """
    Evaluate recent form data source
    Returns normalized score 0-1
    """
    # TODO: Implement actual recent form evaluation
    # For now, return placeholder
    return 0.5


def evaluate_rest_schedule(game_data: Dict) -> float:
    """
    Evaluate rest and schedule data source
    Returns normalized score 0-1
    """
    # TODO: Implement actual rest/schedule evaluation
    # For now, return placeholder
    return 0.5


def evaluate_head_to_head(game_data: Dict) -> float:
    """
    Evaluate head-to-head data source
    Returns normalized score 0-1
    """
    # TODO: Implement actual head-to-head evaluation
    # For now, return placeholder
    return 0.5


DATA_SOURCE_EVALUATORS = {
    "team_stats": evaluate_team_stats,
    "odds_movement": evaluate_odds_movement,
    "recent_form": evaluate_recent_form,
    "rest_schedule": evaluate_rest_schedule,
    "head_to_head": evaluate_head_to_head,
}


def calculate_prediction(model: UserModel, game_data: Dict) -> Dict:
    """
    Calculate prediction using model configuration
    Returns: {prediction, confidence, reasoning} or None if below threshold
    """
    total_score = 0
    total_weight = 0
    source_scores = {}

    # Evaluate each enabled data source
    for source_name, config in model.data_sources.items():
        if not config.get("enabled"):
            continue

        evaluator = DATA_SOURCE_EVALUATORS.get(source_name)
        if not evaluator:
            continue

        # Get normalized score (0-1) from data source
        score = evaluator(game_data)
        weight = config.get("weight", 0)

        source_scores[source_name] = score
        total_score += score * weight
        total_weight += weight

    # Normalize to 0-1
    confidence = total_score / total_weight if total_weight > 0 else 0

    # Check minimum confidence threshold
    if confidence < model.min_confidence:
        return None

    # Determine prediction based on score
    if confidence > 0.55:
        prediction = game_data["home_team"]
    elif confidence < 0.45:
        prediction = game_data["away_team"]
    else:
        return None  # Too close to call

    # Generate reasoning
    reasoning_parts = []
    for source, score in sorted(
        source_scores.items(), key=lambda x: x[1], reverse=True
    ):
        weight = model.data_sources[source]["weight"]
        reasoning_parts.append(f"{source}: {score:.2f} (weight: {weight:.0%})")

    reasoning = f"Prediction based on: {', '.join(reasoning_parts[:3])}"

    return {"prediction": prediction, "confidence": confidence, "reasoning": reasoning}


def get_upcoming_games(sport: str, bet_types: List[str]) -> List[Dict]:
    """
    Get upcoming games for the sport
    """
    # Query games from DynamoDB
    # For now, return empty list (will implement after connecting to existing data)
    return []


def process_model(model_id: str, user_id: str):
    """
    Process a single user model - generate predictions for upcoming games
    """
    # Load model configuration
    model = UserModel.get(user_id, model_id)
    if not model or model.status != "active":
        print(f"Model {model_id} not found or inactive")
        return

    # Get upcoming games for this sport
    games = get_upcoming_games(model.sport, model.bet_types)

    predictions_created = 0
    for game in games:
        # Calculate prediction
        result = calculate_prediction(model, game)
        if not result:
            continue  # Skip low-confidence predictions

        # Create prediction record
        prediction = ModelPrediction(
            model_id=model.model_id,
            user_id=model.user_id,
            game_id=game["game_id"],
            sport=model.sport,
            prediction=result["prediction"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            bet_type=game.get("bet_type", "h2h"),
            home_team=game["home_team"],
            away_team=game["away_team"],
            commence_time=game["commence_time"],
        )

        # Save to DynamoDB
        prediction.save()
        predictions_created += 1

    print(f"Model {model_id}: Created {predictions_created} predictions")


def handler(event, context):
    """
    Lambda handler - processes SQS messages with model execution requests
    """
    print(f"Processing {len(event['Records'])} messages")

    failed_items = []

    for record in event["Records"]:
        try:
            # Parse message body
            body = json.loads(record["body"])
            model_id = body["model_id"]
            user_id = body["user_id"]

            print(f"Processing model: {model_id}")

            # Process the model
            process_model(model_id, user_id)

        except Exception as e:
            print(f"Error processing message: {str(e)}")
            # Add to failed items for partial batch failure
            failed_items.append({"itemIdentifier": record["messageId"]})

    # Return partial batch failure response
    if failed_items:
        return {"batchItemFailures": failed_items}

    return {
        "statusCode": 200,
        "body": json.dumps(f'Processed {len(event["Records"])} models'),
    }
