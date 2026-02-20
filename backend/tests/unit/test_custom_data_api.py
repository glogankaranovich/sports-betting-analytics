"""
Unit tests for custom data API handlers
"""

import os

os.environ["DYNAMODB_TABLE"] = "test-table"
os.environ["ENVIRONMENT"] = "dev"

import unittest  # noqa: E402
from unittest.mock import patch, MagicMock  # noqa: E402

from api.user_data import (
    handle_list_custom_data,
    handle_upload_custom_data,
    handle_delete_custom_data,
)


class TestCustomDataAPI(unittest.TestCase):
    @patch("api.user_data.CustomDataset")
    @patch("api.user_data.check_feature_access")
    def test_list_custom_data_blocked_for_free_tier(
        self, mock_check_access, mock_dataset
    ):
        """Should block listing custom data for free tier users"""
        mock_check_access.return_value = {
            "allowed": False,
            "error": "Feature 'custom_data' not available on your plan. Upgrade to access.",
        }

        result = handle_list_custom_data({"user_id": "user1"})

        self.assertEqual(result["statusCode"], 403)
        mock_check_access.assert_called_once_with("user1", "custom_data")

    @patch("api.user_data.CustomDataset")
    @patch("api.user_data.check_resource_limit")
    @patch("api.user_data.check_feature_access")
    def test_upload_custom_data_blocked_for_free_tier(
        self, mock_check_access, mock_check_limit, mock_dataset
    ):
        """Should block uploading custom data for free tier users"""
        mock_check_access.return_value = {
            "allowed": False,
            "error": "Feature 'custom_data' not available on your plan. Upgrade to access.",
        }

        body = {
            "user_id": "user1",
            "name": "Test Dataset",
            "sport": "basketball_nba",
            "data_type": "team",
            "data": "team,stat\nLakers,100",
        }

        result = handle_upload_custom_data(body)

        self.assertEqual(result["statusCode"], 403)
        mock_check_access.assert_called_once_with("user1", "custom_data")

    @patch("api.user_data.CustomDataset")
    @patch("api.user_data.check_resource_limit")
    @patch("api.user_data.check_feature_access")
    def test_upload_custom_data_blocked_at_limit(
        self, mock_check_access, mock_check_limit, mock_dataset
    ):
        """Should block uploading when dataset limit reached"""
        mock_check_access.return_value = {"allowed": True}
        mock_dataset.list_by_user.return_value = [MagicMock(), MagicMock()]
        mock_check_limit.return_value = {
            "allowed": False,
            "error": "Dataset limit reached (5). Upgrade to create more.",
        }

        body = {
            "user_id": "user1",
            "name": "Test Dataset",
            "sport": "basketball_nba",
            "data_type": "team",
            "data": "team,stat\nLakers,100",
        }

        result = handle_upload_custom_data(body)

        self.assertEqual(result["statusCode"], 403)
        mock_check_limit.assert_called_once_with("user1", "dataset", 2)

    @patch("api.user_data.CustomDataset")
    @patch("api.user_data.check_feature_access")
    def test_delete_custom_data_blocked_for_free_tier(
        self, mock_check_access, mock_dataset
    ):
        """Should block deleting custom data for free tier users"""
        mock_check_access.return_value = {
            "allowed": False,
            "error": "Feature 'custom_data' not available on your plan. Upgrade to access.",
        }

        result = handle_delete_custom_data("dataset1", {"user_id": "user1"})

        self.assertEqual(result["statusCode"], 403)
        mock_check_access.assert_called_once_with("user1", "custom_data")
