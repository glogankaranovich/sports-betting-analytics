"""Unit tests for feature flags and subscriptions"""
import os
import unittest
from unittest.mock import patch

os.environ["DYNAMODB_TABLE"] = "test-table"
os.environ["ENVIRONMENT"] = "dev"

from feature_flags import (  # noqa: E402
    SubscriptionTier,
    is_feature_enabled,
    get_user_limits,
    can_create_user_model,
)
from subscriptions import UserSubscription  # noqa: E402


class TestFeatureFlags(unittest.TestCase):
    """Test feature flag functionality"""

    @patch("feature_flags.get_user_tier")
    def test_system_models_enabled_all_envs(self, mock_tier):
        """System models should be enabled in all environments"""
        mock_tier.return_value = SubscriptionTier.FREE

        self.assertTrue(is_feature_enabled("system_models", "user1", "dev"))
        self.assertTrue(is_feature_enabled("system_models", "user1", "staging"))
        self.assertTrue(is_feature_enabled("system_models", "user1", "prod"))

    @patch("feature_flags.get_user_tier")
    def test_user_models_dev_only(self, mock_tier):
        """User models should only be enabled in dev"""
        mock_tier.return_value = SubscriptionTier.BASIC

        self.assertTrue(is_feature_enabled("user_models", "user1", "dev"))
        self.assertFalse(is_feature_enabled("user_models", "user1", "staging"))
        self.assertFalse(is_feature_enabled("user_models", "user1", "prod"))

    @patch("feature_flags.get_user_tier")
    def test_free_tier_limits(self, mock_tier):
        """FREE tier should have no user models"""
        mock_tier.return_value = SubscriptionTier.FREE

        limits = get_user_limits("user1")
        self.assertEqual(limits["max_user_models"], 0)
        self.assertFalse(limits["user_models"])

    @patch("feature_flags.get_user_tier")
    @patch.dict("os.environ", {"ENVIRONMENT": "dev"})
    def test_basic_tier_limits(self, mock_tier):
        """BASIC tier should have 3 user models"""
        mock_tier.return_value = SubscriptionTier.BASIC

        limits = get_user_limits("user1")
        self.assertEqual(limits["max_user_models"], 3)
        self.assertTrue(limits["user_models"])

    @patch("feature_flags.get_user_tier")
    @patch.dict("os.environ", {"ENVIRONMENT": "dev"})
    def test_can_create_model_under_limit(self, mock_tier):
        """Should allow creating model under limit"""
        mock_tier.return_value = SubscriptionTier.BASIC

        self.assertTrue(can_create_user_model("user1", 0))
        self.assertTrue(can_create_user_model("user1", 2))
        self.assertFalse(can_create_user_model("user1", 3))


class TestSubscriptions(unittest.TestCase):
    """Test subscription management"""

    @patch("subscriptions.table")
    def test_get_subscription_not_found(self, mock_table):
        """Should return FREE tier if no subscription found"""
        mock_table.get_item.return_value = {}

        sub = UserSubscription.get("user1")
        self.assertEqual(sub.tier, "free")
        self.assertEqual(sub.user_id, "user1")

    @patch("subscriptions.table")
    def test_get_subscription_found(self, mock_table):
        """Should return subscription from DynamoDB"""
        mock_table.get_item.return_value = {
            "Item": {
                "tier": "basic",
                "status": "active",
            }
        }

        sub = UserSubscription.get("user1")
        self.assertEqual(sub.tier, "basic")
        self.assertEqual(sub.status, "active")


if __name__ == "__main__":
    unittest.main()
