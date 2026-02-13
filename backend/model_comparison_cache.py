"""
Lambda function to pre-compute model comparison data and cache in DynamoDB.
Runs on a schedule (every 15 minutes) to keep data fresh.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import boto3
from boto3.dynamodb.conditions import Key
from constants import SUPPORTED_SPORTS, SYSTEM_MODELS, TIME_RANGES

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])


def _get_model_comparison_data(
    model_id: str,
    sport: str,
    cutoff_time: str,
    is_user_model: bool = False,
    model_name: str = None,
) -> list:
    """Get comparison data for a single model"""
    results = []

    for bet_type in ["game", "prop"]:
        # Query original predictions
        original_pk = f"VERIFIED#{model_id}#{sport}#{bet_type}"
        original_response = table.query(
            IndexName="VerifiedAnalysisGSI",
            KeyConditionExpression=Key("verified_analysis_pk").eq(original_pk)
            & Key("verified_analysis_sk").gte(cutoff_time),
            Limit=5000,
        )
        original_items = original_response.get("Items", [])

        # Query inverse predictions
        inverse_pk = f"{original_pk}#inverse"
        inverse_response = table.query(
            IndexName="VerifiedAnalysisGSI",
            KeyConditionExpression=Key("verified_analysis_pk").eq(inverse_pk)
            & Key("verified_analysis_sk").gte(cutoff_time),
            Limit=5000,
        )
        inverse_items = inverse_response.get("Items", [])

        if not original_items:
            continue

        # Calculate metrics
        original_total = len(original_items)
        original_correct = sum(
            1 for item in original_items if item.get("analysis_correct")
        )
        original_accuracy = (
            original_correct / original_total if original_total > 0 else 0
        )

        inverse_total = len(inverse_items)
        inverse_correct = sum(
            1 for item in inverse_items if item.get("analysis_correct")
        )
        inverse_accuracy = inverse_correct / inverse_total if inverse_total > 0 else 0

        # Determine recommendation
        if inverse_accuracy > original_accuracy and inverse_accuracy > 0.5:
            recommendation = "INVERSE"
        elif original_accuracy > 0.5:
            recommendation = "ORIGINAL"
        else:
            recommendation = "AVOID"

        results.append(
            {
                "model": model_name or model_id,
                "model_id": model_id,
                "bet_type": bet_type,
                "is_user_model": is_user_model,
                "sample_size": original_total,
                "original_accuracy": round(original_accuracy, 3),
                "original_correct": original_correct,
                "original_total": original_total,
                "inverse_accuracy": round(inverse_accuracy, 3),
                "inverse_correct": inverse_correct,
                "inverse_total": inverse_total,
                "recommendation": recommendation,
            }
        )

    return results


def compute_model_comparison(sport: str, days: int) -> List[Dict[str, Any]]:
    """Compute model comparison for a sport and time range"""
    if days >= 9999:
        cutoff_time = "2000-01-01T00:00:00"
    else:
        cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()

    comparison = []

    for model in SYSTEM_MODELS:
        model_data = _get_model_comparison_data(
            model, sport, cutoff_time, is_user_model=False
        )
        if model_data:
            comparison.extend(model_data)

    # Sort by best performing
    comparison.sort(
        key=lambda x: max(x["original_accuracy"], x["inverse_accuracy"]),
        reverse=True,
    )

    return comparison


def lambda_handler(event, context):
    """Pre-compute model comparison data for common queries"""
    try:
        results = []

        for sport in SUPPORTED_SPORTS:
            for days in TIME_RANGES:
                print(f"Computing model comparison for {sport}, {days} days")

                comparison_data = compute_model_comparison(sport, days)

                # Store in DynamoDB with cache key
                cache_key = f"MODEL_COMPARISON#{sport}#{days}"
                timestamp = datetime.utcnow().isoformat()

                table.put_item(
                    Item={
                        "pk": "CACHE",
                        "sk": cache_key,
                        "data": comparison_data,
                        "sport": sport,
                        "days": days,
                        "computed_at": timestamp,
                        "ttl": int(
                            (datetime.utcnow() + timedelta(hours=1)).timestamp()
                        ),  # 1 hour TTL
                    }
                )

                results.append(
                    {
                        "sport": sport,
                        "days": days,
                        "models_count": len(comparison_data),
                        "computed_at": timestamp,
                    }
                )

                print(
                    f"Cached {len(comparison_data)} model comparisons for {sport}, {days} days"
                )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Model comparison cache updated", "results": results}
            ),
        }

    except Exception as e:
        print(f"Error computing model comparison: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
