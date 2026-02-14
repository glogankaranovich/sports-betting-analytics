"""
API Middleware for Feature Flags and Rate Limiting
"""

from typing import Dict
from feature_flags import is_feature_enabled, get_user_limits
from subscriptions import UserSubscription


def check_feature_access(user_id: str, feature_name: str) -> Dict:
    """Check if user has access to feature"""
    if not is_feature_enabled(feature_name, user_id):
        return {
            "allowed": False,
            "error": f"Feature '{feature_name}' not available on your plan. Upgrade to access.",
        }
    return {"allowed": True}


def check_rate_limit(user_id: str) -> Dict:
    """Check if user is within rate limits"""
    subscription = UserSubscription.get(user_id)
    limits = get_user_limits(user_id)

    if not subscription.increment_api_calls():
        return {
            "allowed": False,
            "error": f"Daily API limit reached ({limits['api_calls_per_day']} calls). Upgrade for more.",
        }

    return {
        "allowed": True,
        "remaining": limits["api_calls_per_day"] - subscription.api_calls_today,
    }


def check_resource_limit(user_id: str, resource_type: str, current_count: int) -> Dict:
    """Check if user can create more resources (models/datasets)"""
    from feature_flags import can_create_user_model, can_create_dataset

    if resource_type == "user_model":
        if not can_create_user_model(user_id, current_count):
            limits = get_user_limits(user_id)
            return {
                "allowed": False,
                "error": f"Model limit reached ({limits['max_user_models']}). Upgrade to create more.",
            }
    elif resource_type == "dataset":
        if not can_create_dataset(user_id, current_count):
            limits = get_user_limits(user_id)
            return {
                "allowed": False,
                "error": f"Dataset limit reached ({limits['max_custom_datasets']}). Upgrade to create more.",
            }

    return {"allowed": True}
