"""
Unit tests for AI Agent privacy controls
"""
from unittest.mock import MagicMock, patch

import pytest

from ai_agent import AIAgent


@pytest.fixture
def mock_dynamodb():
    with patch("ai_agent.boto3") as mock_boto3:
        mock_table = MagicMock()
        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_resource
        yield mock_table


@pytest.fixture
def agent(mock_dynamodb):
    with patch("ai_agent.boto3.client"):
        return AIAgent()


class TestPrivacyControls:
    def test_list_user_models_own_models(self, agent):
        """Users can list their own models"""
        with patch("ai_agent.UserModel") as mock_model:
            mock_model.list_by_user.return_value = [
                MagicMock(
                    model_id="model1",
                    name="My Model",
                    sport="basketball_nba",
                    bet_types=["h2h"],
                    status="active",
                    created_at="2024-01-01",
                )
            ]

            result = agent._list_user_models({"user_id": "user123"}, user_id="user123")

            assert "models" in result
            assert len(result["models"]) == 1
            assert result["models"][0]["model_id"] == "model1"
            mock_model.list_by_user.assert_called_once_with("user123")

    def test_list_user_models_access_denied(self, agent):
        """Users cannot list other users' models"""
        result = agent._list_user_models({"user_id": "user456"}, user_id="user123")

        assert "error" in result
        assert result["error"] == "Access denied"

    def test_list_user_models_benny_can_see_all(self, agent):
        """Benny can list any user's models"""
        with patch("ai_agent.UserModel") as mock_model:
            mock_model.list_by_user.return_value = []

            result = agent._list_user_models({"user_id": "user456"}, user_id="benny")

            assert "models" in result
            mock_model.list_by_user.assert_called_once_with("user456")

    def test_analyze_predictions_filters_by_user(self, agent, mock_dynamodb):
        """Analyze predictions filters by user_id"""
        mock_dynamodb.query.return_value = {
            "Items": [
                {"user_id": "user123", "outcome": "correct"},
                {"user_id": "user456", "outcome": "correct"},
                {"user_id": "user123", "outcome": "incorrect"},
            ]
        }

        result = agent._analyze_predictions({"days_back": 7}, user_id="user123")

        assert result["total_predictions"] == 2
        assert result["correct_predictions"] == 1
        assert result["accuracy"] == 50.0

    def test_analyze_predictions_benny_sees_all(self, agent, mock_dynamodb):
        """Benny can analyze all predictions"""
        mock_dynamodb.query.return_value = {
            "Items": [
                {"user_id": "user123", "outcome": "correct"},
                {"user_id": "user456", "outcome": "correct"},
                {"user_id": "user123", "outcome": "incorrect"},
            ]
        }

        result = agent._analyze_predictions({"days_back": 7}, user_id="benny")

        assert result["total_predictions"] == 3
        assert result["correct_predictions"] == 2

    def test_explain_prediction_access_denied(self, agent, mock_dynamodb):
        """Users cannot explain other users' predictions"""
        mock_dynamodb.get_item.return_value = {
            "Item": {
                "user_id": "user456",
                "game": "Lakers vs Warriors",
                "prediction": "Lakers",
                "confidence": 0.75,
            }
        }

        result = agent._explain_prediction(
            {"prediction_id": "pred123"}, user_id="user123"
        )

        assert "error" in result
        assert result["error"] == "Access denied"

    def test_explain_prediction_benny_can_see_all(self, agent, mock_dynamodb):
        """Benny can explain any prediction"""
        mock_dynamodb.get_item.return_value = {
            "Item": {
                "user_id": "user456",
                "game": "Lakers vs Warriors",
                "prediction": "Lakers",
                "confidence": 0.75,
            }
        }

        result = agent._explain_prediction(
            {"prediction_id": "pred123"}, user_id="benny"
        )

        assert "prediction_id" in result
        assert result["game"] == "Lakers vs Warriors"

    def test_get_recent_predictions_filters_by_user(self, agent, mock_dynamodb):
        """RAG context retrieval filters predictions by user"""
        mock_dynamodb.query.return_value = {
            "Items": [
                {"user_id": "user123", "game": "Game 1"},
                {"user_id": "user456", "game": "Game 2"},
                {"user_id": "user123", "game": "Game 3"},
            ]
        }

        predictions = agent._get_recent_predictions(user_id="user123")

        assert len(predictions) == 2
        assert all(p["user_id"] == "user123" for p in predictions)

    def test_get_recent_predictions_benny_sees_all(self, agent, mock_dynamodb):
        """Benny sees all predictions in RAG context"""
        mock_dynamodb.query.return_value = {
            "Items": [
                {"user_id": "user123", "game": "Game 1"},
                {"user_id": "user456", "game": "Game 2"},
                {"user_id": "user123", "game": "Game 3"},
            ]
        }

        predictions = agent._get_recent_predictions(user_id="benny")

        assert len(predictions) == 3

    def test_create_model_uses_requesting_user_id(self, agent):
        """Create model uses requesting user's ID, not parameter"""
        with patch("ai_agent.UserModel") as mock_model, patch(
            "ai_agent.validate_model_config"
        ) as mock_validate:
            mock_validate.return_value = []
            mock_instance = MagicMock()
            mock_model.create.return_value = mock_instance

            params = {
                "model_name": "Test Model",
                "sport": "basketball_nba",
                "bet_types": ["h2h"],
                "data_sources": {"team_stats": {"enabled": True, "weight": 1.0}},
            }

            result = agent._create_model(params, requesting_user_id="user123")

            assert result["success"]
            # Verify model was created with requesting_user_id
            mock_model.create.assert_called_once()
            call_args = mock_model.create.call_args[0]
            assert call_args[0] == "user123"  # user_id parameter
