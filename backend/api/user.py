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

        from subscriptions import UserSubscription
        from feature_flags import get_user_limits

        # Get subscription
        subscription = UserSubscription.get(user_id)
        limits = get_user_limits(user_id)

        # Get current usage counts (with error handling)
        user_models_count = 0
        datasets_count = 0

        try:
            from user_models import UserModel

            user_models = UserModel.list_by_user(user_id)
            user_models_count = len(user_models)
        except Exception as e:
            print(f"Error fetching user models: {e}")

        try:
            from custom_data import CustomDataset

            datasets = CustomDataset.list_by_user(user_id)
            datasets_count = len(datasets)
        except Exception as e:
            print(f"Error fetching datasets: {e}")

        return create_response(
            200,
            {
                "tier": subscription.tier,
                "status": subscription.status,
                "limits": limits,
                "usage": {
                    "user_models_count": user_models_count,
                    "datasets_count": datasets_count,
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

        response = table.get_item(Key={"pk": f"USER#{user_id}", "sk": "PROFILE"})

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
        response = table.get_item(Key={"pk": f"USER#{user_id}", "sk": "PROFILE"})

        if "Item" in response:
            item = response["Item"]
            item["preferences"] = preferences
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            item = {
                "pk": f"USER#{user_id}",
                "sk": "PROFILE",
                "email": body.get("email", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "preferences": preferences,
            }

        table.put_item(Item=item)

        return create_response(200, {"message": "Profile updated successfully"})
    except Exception as e:
        return create_response(500, {"error": f"Error updating profile: {str(e)}"})


def handle_upgrade_subscription(body: Dict[str, Any]):
    """Upgrade or downgrade user subscription tier"""
    try:
        user_id = body.get("user_id")
        tier = body.get("tier")

        if not user_id or not tier:
            return create_response(400, {"error": "user_id and tier are required"})

        if tier not in ["free", "basic", "pro"]:
            return create_response(400, {"error": "Invalid tier"})

        from subscriptions import UserSubscription

        # Get current subscription
        subscription = UserSubscription.get(user_id)

        # For now, just update the tier directly (no Stripe integration yet)
        subscription.update_tier(tier)

        return create_response(
            200, {"message": f"Subscription updated to {tier}", "tier": tier}
        )
    except Exception as e:
        return create_response(
            500, {"error": f"Error updating subscription: {str(e)}"}
        )
