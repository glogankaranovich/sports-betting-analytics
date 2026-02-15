"""Unit tests for API middleware"""
import os
import unittest
from unittest.mock import patch

os.environ["DYNAMODB_TABLE"] = "test-table"
os.environ["ENVIRONMENT"] = "dev"

from api_middleware import (  # noqa: E402
    check_feature_access,
    check_resource_limit,
)


class TestAPIMiddleware(unittest.TestCase):
    """Test API middleware functions"""

    @patch("api_middleware.is_feature_enabled")
    def test_check_feature_access_allowed(self, mock_enabled):
        """Should allow access when feature enabled"""
        mock_enabled.return_value = True

        result = check_feature_access("user1", "user_models")

        self.assertTrue(result["allowed"])
        mock_enabled.assert_called_once_with("user_models", "user1")

    @patch("api_middleware.is_feature_enabled")
    def test_check_feature_access_denied(self, mock_enabled):
        """Should deny access when feature disabled"""
        mock_enabled.return_value = False

        result = check_feature_access("user1", "user_models")

        self.assertFalse(result["allowed"])
        self.assertIn("not available", result["error"])

    @patch("feature_flags.can_create_user_model")
    def test_check_resource_limit_model_allowed(self, mock_can_create):
        """Should allow creating model under limit"""
        mock_can_create.return_value = True

        result = check_resource_limit("user1", "user_model", 2)

        self.assertTrue(result["allowed"])
        mock_can_create.assert_called_once_with("user1", 2)

    @patch("feature_flags.get_user_limits")
    @patch("feature_flags.can_create_user_model")
    def test_check_resource_limit_model_exceeded(self, mock_can_create, mock_limits):
        """Should deny creating model at limit"""
        mock_can_create.return_value = False
        mock_limits.return_value = {"max_user_models": 3}

        result = check_resource_limit("user1", "user_model", 3)

        self.assertFalse(result["allowed"])
        self.assertIn("limit reached", result["error"])

    @patch("feature_flags.can_create_dataset")
    def test_check_resource_limit_dataset_allowed(self, mock_can_create):
        """Should allow creating dataset under limit"""
        mock_can_create.return_value = True

        result = check_resource_limit("user1", "dataset", 1)

        self.assertTrue(result["allowed"])
        mock_can_create.assert_called_once_with("user1", 1)


if __name__ == "__main__":
    unittest.main()
