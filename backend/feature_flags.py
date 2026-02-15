"""
Feature Flags & Subscription Tiers

Supports both subscription tiers and usage-based limits.
Enables staged rollout and monetization.
"""

import os
from typing import Dict
from enum import Enum


class SubscriptionTier(Enum):
    FREE = "free"
    BASIC = "basic"  # $9.99/month
    PRO = "pro"  # $29.99/month


# Subscription tier limits
TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "system_models": True,
        "benny_ai": False,
        "user_models": False,
        "custom_data": False,
        "model_marketplace": False,
        "max_user_models": 0,
        "max_custom_datasets": 0,
    },
    SubscriptionTier.BASIC: {
        "system_models": True,
        "benny_ai": True,
        "user_models": True,
        "custom_data": True,
        "model_marketplace": False,
        "max_user_models": 3,
        "max_custom_datasets": 5,
    },
    SubscriptionTier.PRO: {
        "system_models": True,
        "benny_ai": True,
        "user_models": True,
        "custom_data": True,
        "model_marketplace": True,
        "max_user_models": 20,
        "max_custom_datasets": 50,
    },
}


# Feature rollout stages (overrides subscription for beta testing)
FEATURE_ROLLOUT = {
    "system_models": {
        "name": "System Models",
        "enabled_envs": ["dev", "staging", "prod"],
        "beta_users": [],  # Empty = all users in enabled_envs
    },
    "benny_ai": {
        "name": "Benny AI Betting",
        "enabled_envs": ["dev", "staging", "prod"],
        "beta_users": [],  # Empty = all users
    },
    "user_models": {
        "name": "User Models & Custom Data",
        "enabled_envs": ["dev"],  # Dev only for now
        "beta_users": [],  # Specific beta testers
    },
    "model_marketplace": {
        "name": "Model Marketplace",
        "enabled_envs": ["dev"],  # Dev only
        "beta_users": [],
    },
}


def get_user_tier(user_id: str) -> SubscriptionTier:
    """Get user's subscription tier from DynamoDB"""
    try:
        from subscriptions import UserSubscription

        subscription = UserSubscription.get(user_id)
        return SubscriptionTier(subscription.tier)
    except Exception as e:
        print(f"Error getting user tier: {e}")
        return SubscriptionTier.FREE


def is_feature_enabled(
    feature_name: str,
    user_id: str,
    environment: str = None,
) -> bool:
    """Check if feature is enabled for user (considers both rollout and subscription)"""
    env = environment or os.environ.get("ENVIRONMENT", "dev")

    # Check feature rollout first (beta testing)
    if feature_name in FEATURE_ROLLOUT:
        rollout = FEATURE_ROLLOUT[feature_name]

        # Check environment
        if env not in rollout["enabled_envs"]:
            return False

        # Check beta users (empty list = all users in enabled envs)
        if rollout["beta_users"] and user_id not in rollout["beta_users"]:
            return False

    # Check subscription tier
    tier = get_user_tier(user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])

    return limits.get(feature_name, False)


def get_user_limits(user_id: str) -> Dict:
    """Get all limits for user's subscription tier"""
    tier = get_user_tier(user_id)
    return TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])


def can_create_user_model(user_id: str, current_count: int) -> bool:
    """Check if user can create another model"""
    limits = get_user_limits(user_id)
    max_models = limits["max_user_models"]
    return max_models == -1 or current_count < max_models


def can_create_dataset(user_id: str, current_count: int) -> bool:
    """Check if user can create another dataset"""
    limits = get_user_limits(user_id)
    max_datasets = limits["max_custom_datasets"]
    return max_datasets == -1 or current_count < max_datasets


def add_beta_tester(feature_name: str, user_id: str) -> bool:
    """Add user to beta test (bypasses subscription requirement)"""
    if feature_name not in FEATURE_ROLLOUT:
        return False

    if user_id not in FEATURE_ROLLOUT[feature_name]["beta_users"]:
        FEATURE_ROLLOUT[feature_name]["beta_users"].append(user_id)
    return True
