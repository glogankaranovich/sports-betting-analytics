"""Tests for subscriptions"""
import unittest
from unittest.mock import Mock, patch

from subscriptions import UserSubscription


class TestUserSubscription(unittest.TestCase):
    """Test UserSubscription"""

    def test_init(self):
        """Test initialization"""
        sub = UserSubscription(
            user_id="user123",
            tier="premium",
            status="active",
            stripe_subscription_id="sub_123"
        )
        
        self.assertEqual(sub.user_id, "user123")
        self.assertEqual(sub.tier, "premium")
        self.assertEqual(sub.status, "active")
        self.assertEqual(sub.stripe_subscription_id, "sub_123")

    @patch("subscriptions.table")
    def test_get_existing_subscription(self, mock_table):
        """Test getting existing subscription"""
        mock_table.get_item.return_value = {
            "Item": {
                "tier": "premium",
                "status": "active",
                "stripe_subscription_id": "sub_123",
                "current_period_start": "2024-01-01",
                "current_period_end": "2024-02-01"
            }
        }
        
        sub = UserSubscription.get("user123")
        
        self.assertEqual(sub.user_id, "user123")
        self.assertEqual(sub.tier, "premium")
        self.assertEqual(sub.status, "active")
        self.assertEqual(sub.stripe_subscription_id, "sub_123")

    @patch("subscriptions.table")
    def test_get_no_subscription_returns_free(self, mock_table):
        """Test getting non-existent subscription returns free tier"""
        mock_table.get_item.return_value = {}
        
        sub = UserSubscription.get("user123")
        
        self.assertEqual(sub.user_id, "user123")
        self.assertEqual(sub.tier, "free")

    @patch("subscriptions.table")
    def test_get_error_returns_free(self, mock_table):
        """Test error getting subscription returns free tier"""
        mock_table.get_item.side_effect = Exception("DB error")
        
        sub = UserSubscription.get("user123")
        
        self.assertEqual(sub.user_id, "user123")
        self.assertEqual(sub.tier, "free")

    @patch("subscriptions.table")
    def test_save(self, mock_table):
        """Test saving subscription"""
        sub = UserSubscription(
            user_id="user123",
            tier="premium",
            status="active"
        )
        
        sub.save()
        
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]["Item"]
        self.assertEqual(call_args["pk"], "USER#user123")
        self.assertEqual(call_args["sk"], "SUBSCRIPTION")
        self.assertEqual(call_args["tier"], "premium")
        self.assertEqual(call_args["status"], "active")

    @patch("subscriptions.table")
    def test_update_tier(self, mock_table):
        """Test updating subscription tier"""
        sub = UserSubscription(user_id="user123", tier="free")
        
        sub.update_tier("premium", "sub_123")
        
        self.assertEqual(sub.tier, "premium")
        self.assertEqual(sub.stripe_subscription_id, "sub_123")
        mock_table.put_item.assert_called_once()

    @patch("subscriptions.table")
    def test_cancel(self, mock_table):
        """Test cancelling subscription"""
        sub = UserSubscription(user_id="user123", tier="premium", status="active")
        
        sub.cancel()
        
        self.assertEqual(sub.tier, "free")
        self.assertEqual(sub.status, "cancelled")
        mock_table.put_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
