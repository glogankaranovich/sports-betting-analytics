"""
User-related API endpoints (profile, subscription)
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict

import boto3

from api.utils import create_response

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
table = dynamodb.Table(table_name)


def handle_get_subscription(query_params: Dict[str, str]):
    """Get user subscription info"""
    try:
        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id is required"})

        # TODO: Implement actual subscription logic
        # For now, return free tier with default limits
        return create_response(
            200,
            {
                "tier": "free",
                "limits": {
                    "system_models": True,
                    "benny_ai": False,
                    "user_models": False,
                    "custom_data": False,
                    "model_marketplace": False,
                    "api_calls_per_day": 100,
                    "max_user_models": 0,
                    "max_custom_datasets": 0,
                },
                "usage": {
                    "api_calls_today": 0,
                    "user_models_count": 0,
                    "datasets_count": 0,
                },
            },
        )
    except Exception as e:
        return create_response(500, {"error": f"Error fetching subscription: {str(e)}"})


def handle_get_profile(query_params: Dict[str, str]):
    """Get user profile"""
    try:
        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id is required"})

        response = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})

        if "Item" not in response:
            return create_response(404, {"error": "Profile not found"})

        item = response["Item"]
        return create_response(
            200,
            {
                "user_id": user_id,
                "email": item.get("email", ""),
                "created_at": item.get("created_at", ""),
                "last_login": item.get("last_login"),
                "preferences": item.get("preferences", {}),
            },
        )
    except Exception as e:
        return create_response(500, {"error": f"Error fetching profile: {str(e)}"})


def handle_update_profile(body: Dict[str, Any]):
    """Update user profile"""
    try:
        user_id = body.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id is required"})

        preferences = body.get("preferences", {})

        # Get existing profile or create new
        response = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})

        if "Item" in response:
            item = response["Item"]
            item["preferences"] = preferences
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            item = {
                "PK": f"USER#{user_id}",
                "SK": "PROFILE",
                "email": body.get("email", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "preferences": preferences,
            }

        table.put_item(Item=item)

        return create_response(200, {"message": "Profile updated successfully"})
    except Exception as e:
        return create_response(500, {"error": f"Error updating profile: {str(e)}"})
