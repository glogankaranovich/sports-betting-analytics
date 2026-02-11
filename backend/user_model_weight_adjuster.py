"""
User Model Weight Adjuster - Adjusts data source weights based on performance
Runs weekly to optimize user models that have auto_adjust_weights enabled
"""
import os
from datetime import datetime, timedelta
from typing import Dict

import boto3
from boto3.dynamodb.conditions import Key

from user_models import UserModel

dynamodb = boto3.resource("dynamodb")
BETS_TABLE = os.environ.get("BETS_TABLE", "carpool-bets-v2-dev")
bets_table = dynamodb.Table(BETS_TABLE)


def get_data_source_accuracy(
    user_id: str, model_id: str, source_name: str, days: int = 30
) -> float:
    """
    Calculate accuracy for a specific data source over last N days
    Returns accuracy 0-1 or None if insufficient data
    """
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # Query verified predictions for this model
    response = bets_table.query(
        IndexName="VerifiedAnalysisGSI",
        KeyConditionExpression=Key("verified_analysis_pk").eq(
            f"USER_MODEL#{user_id}#{model_id}"
        )
        & Key("verified_at").gt(cutoff),
        Limit=1000,
    )

    items = response.get("Items", [])
    if len(items) < 10:  # Need at least 10 predictions
        return None

    # Filter predictions where this source contributed
    source_predictions = []
    for item in items:
        reasoning = item.get("reasoning", "")
        # Check if source was used (appears in reasoning)
        if source_name in reasoning:
            source_predictions.append(item)

    if len(source_predictions) < 5:  # Need at least 5 with this source
        return None

    # Calculate accuracy
    correct = sum(1 for p in source_predictions if p.get("correct"))
    return correct / len(source_predictions)


def calculate_new_weights(
    model: UserModel, source_accuracies: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate new weights based on source accuracies
    Uses performance-based scaling with minimum weight floor
    """
    new_weights = {}
    min_weight = 0.05  # Minimum 5% weight to keep sources active

    # Calculate total accuracy-weighted score
    total_score = sum(acc for acc in source_accuracies.values() if acc is not None)

    if total_score == 0:
        return {}  # No changes if no data

    # Distribute weights proportionally to accuracy
    for source_name, accuracy in source_accuracies.items():
        if accuracy is None:
            # Keep existing weight if no data
            current_weight = model.data_sources.get(source_name, {}).get("weight", 0)
            new_weights[source_name] = current_weight
        else:
            # Scale weight by relative accuracy
            new_weight = accuracy / total_score
            # Apply floor
            new_weights[source_name] = max(min_weight, new_weight)

    # Normalize to sum to 1.0
    total_weight = sum(new_weights.values())
    if total_weight > 0:
        new_weights = {k: v / total_weight for k, v in new_weights.items()}

    return new_weights


def adjust_model_weights(user_id: str, model_id: str):
    """
    Adjust weights for a single user model based on recent performance
    """
    # Load model
    model = UserModel.get(user_id, model_id)
    if not model:
        print(f"Model not found: {model_id}")
        return

    # Check if auto-adjustment is enabled
    if not model.auto_adjust_weights:
        print(f"Model {model_id}: auto-adjustment disabled")
        return

    # Calculate accuracy for each data source
    source_accuracies = {}
    for source_name, config in model.data_sources.items():
        if not config.get("enabled"):
            continue

        accuracy = get_data_source_accuracy(user_id, model_id, source_name)
        source_accuracies[source_name] = accuracy
        print(
            f"  {source_name}: {accuracy:.2%}" if accuracy else f"  {source_name}: N/A"
        )

    # Calculate new weights
    new_weights = calculate_new_weights(model, source_accuracies)
    if not new_weights:
        print(f"Model {model_id}: insufficient data for adjustment")
        return

    # Update model weights
    changes = []
    for source_name, new_weight in new_weights.items():
        old_weight = model.data_sources.get(source_name, {}).get("weight", 0)
        if abs(new_weight - old_weight) > 0.05:  # Only log significant changes
            changes.append(f"{source_name}: {old_weight:.1%} → {new_weight:.1%}")
        model.data_sources[source_name]["weight"] = new_weight

    # Save updated model
    model.save()

    if changes:
        print(f"Model {model_id}: Updated weights - {', '.join(changes)}")
    else:
        print(f"Model {model_id}: No significant weight changes")


def handler(event, context):
    """
    Lambda handler - adjusts weights for all user models with auto-adjustment enabled
    Triggered weekly by EventBridge
    """
    print("Starting user model weight adjustment")

    # Scan for all user models with auto_adjust_weights=true
    response = bets_table.scan(
        FilterExpression="begins_with(pk, :prefix) AND auto_adjust_weights = :true",
        ExpressionAttributeValues={":prefix": "USER_MODEL#", ":true": True},
    )

    models = response.get("Items", [])
    print(f"Found {len(models)} models with auto-adjustment enabled")

    adjusted_count = 0
    for item in models:
        try:
            # Extract user_id and model_id from pk/sk
            pk = item.get("pk", "")
            sk = item.get("sk", "")

            # pk format: USER_MODEL#{user_id}
            # sk format: MODEL#{model_id}
            user_id = pk.split("#")[1] if "#" in pk else ""
            model_id = sk.split("#")[1] if "#" in sk else ""

            if not user_id or not model_id:
                continue

            print(f"\nAdjusting model: {model_id} (user: {user_id})")
            adjust_model_weights(user_id, model_id)
            adjusted_count += 1

        except Exception as e:
            print(f"Error adjusting model {item.get('pk')}: {e}")
            continue

    print(f"\nCompleted: Adjusted {adjusted_count} models")

    return {"statusCode": 200, "adjusted_models": adjusted_count}
