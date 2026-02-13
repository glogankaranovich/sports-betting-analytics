"""
Unit tests for user models API endpoints
"""
import os

# Set environment variable before importing api_handler
os.environ["DYNAMODB_TABLE"] = "test-table"

import json  # noqa: E402
import unittest  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

from api_handler import handle_create_user_model  # noqa: E402
from api_handler import (
    handle_delete_user_model,
    handle_get_user_model,
    handle_get_user_model_performance,
    handle_list_user_models,
    handle_update_user_model,
)


class TestUserModelsAPI(unittest.TestCase):
    """Test user models API handlers"""

    @patch("user_models.UserModel")
    def test_list_user_models(self, mock_model):
        """Test listing user models"""
        mock_instance = MagicMock()
        mock_instance.to_dynamodb.return_value = {"model_id": "model1", "name": "Test Model"}
        mock_model.list_by_user.return_value = [mock_instance]

        result = handle_list_user_models({"user_id": "user123"})

        self.assertEqual(result["statusCode"], 200)
        mock_model.list_by_user.assert_called_once_with("user123")

    def test_list_user_models_missing_user_id(self):
        """Test listing models without user_id"""
        result = handle_list_user_models({})

        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("user_id parameter required", body["error"])

    @patch("user_models.validate_model_config")
    @patch("user_models.UserModel")
    def test_create_user_model(self, mock_model, mock_validate):
        """Test creating a user model"""
        mock_validate.return_value = (True, None)
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance

        body = {
            "user_id": "user123",
            "name": "Test Model",
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {"team_stats": {"enabled": True, "weight": 1.0}},
        }

        result = handle_create_user_model(body)

        self.assertEqual(result["statusCode"], 201)
        mock_instance.save.assert_called_once()

    def test_create_user_model_missing_fields(self):
        """Test creating model with missing fields"""
        result = handle_create_user_model({"user_id": "user123"})

        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("Missing required field", body["error"])

    @patch("user_models.validate_model_config")
    @patch("user_models.UserModel")
    def test_create_user_model_invalid_config(self, mock_model, mock_validate):
        """Test creating model with invalid configuration"""
        mock_validate.return_value = (False, "Invalid weights")

        body = {
            "user_id": "user123",
            "name": "Test Model",
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {"team_stats": {"enabled": True, "weight": 0.5}},
        }

        result = handle_create_user_model(body)

        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertEqual(body["error"], "Invalid weights")

    @patch("user_models.UserModel")
    def test_get_user_model(self, mock_model):
        """Test getting a specific model"""
        mock_instance = MagicMock()
        mock_instance.to_dynamodb.return_value = {"model_id": "model1"}
        mock_model.get.return_value = mock_instance

        result = handle_get_user_model("model1", {"user_id": "user123"})

        self.assertEqual(result["statusCode"], 200)
        mock_model.get.assert_called_once_with("user123", "model1")

    @patch("user_models.UserModel")
    def test_get_user_model_not_found(self, mock_model):
        """Test getting non-existent model"""
        mock_model.get.return_value = None

        result = handle_get_user_model("model1", {"user_id": "user123"})

        self.assertEqual(result["statusCode"], 404)

    @patch("user_models.validate_model_config")
    @patch("user_models.UserModel")
    def test_update_user_model(self, mock_model, mock_validate):
        """Test updating a model"""
        mock_validate.return_value = (True, None)
        mock_instance = MagicMock()
        mock_instance.name = "Old Name"
        mock_instance.sport = "basketball_nba"
        mock_instance.bet_types = ["h2h"]
        mock_model.get.return_value = mock_instance

        body = {"user_id": "user123", "name": "New Name"}

        result = handle_update_user_model("model1", body)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(mock_instance.name, "New Name")
        mock_instance.save.assert_called_once()

    @patch("user_models.UserModel")
    def test_delete_user_model(self, mock_model):
        """Test deleting a model"""
        mock_instance = MagicMock()
        mock_model.get.return_value = mock_instance

        result = handle_delete_user_model("model1", {"user_id": "user123"})

        self.assertEqual(result["statusCode"], 200)
        mock_instance.delete.assert_called_once()

    @patch("user_models.ModelPrediction")
    def test_get_user_model_performance(self, mock_prediction):
        """Test getting model performance metrics"""
        mock_prediction.get_performance.return_value = {
            "total_predictions": 10,
            "correct": 7,
            "incorrect": 3,
            "accuracy": 0.7,
        }

        result = handle_get_user_model_performance("model1")

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["performance"]["accuracy"], 0.7)
        mock_prediction.get_performance.assert_called_once_with("model1")


if __name__ == "__main__":
    unittest.main()
