"""Unit tests for AI Agent API"""
import json
import os
from unittest.mock import MagicMock, patch

# Set environment variable before importing
os.environ["DYNAMODB_TABLE"] = "test-table"

from ai_agent_api import handle_chat, lambda_handler  # noqa: E402


class TestAIAgentAPI:
    @patch("ai_agent_api.AIAgent")
    def test_lambda_handler_chat_endpoint(self, mock_agent_class):
        """Test Lambda handler routes to chat endpoint"""
        mock_agent = MagicMock()
        mock_agent.chat.return_value = "Test response"
        mock_agent_class.return_value = mock_agent

        event = {
            "path": "/ai-agent/chat",
            "httpMethod": "POST",
            "body": json.dumps({"message": "Create a model", "user_id": "user123"}),
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["response"] == "Test response"

    def test_lambda_handler_not_found(self):
        """Test Lambda handler returns 404 for unknown paths"""
        event = {"path": "/unknown", "httpMethod": "GET"}

        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    @patch("ai_agent_api.AIAgent")
    def test_handle_chat_success(self, mock_agent_class):
        """Test successful chat request"""
        mock_agent = MagicMock()
        mock_agent.chat.return_value = "Model created successfully"
        mock_agent_class.return_value = mock_agent

        event = {
            "body": json.dumps(
                {
                    "message": "Create a model for NBA",
                    "user_id": "user123",
                    "conversation_history": [],
                }
            )
        }

        response = handle_chat(event)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["response"] == "Model created successfully"
        mock_agent.chat.assert_called_once()

    def test_handle_chat_missing_message(self):
        """Test chat request without message"""
        event = {"body": json.dumps({"user_id": "user123"})}

        response = handle_chat(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "message is required" in body["error"]

    def test_handle_chat_missing_user_id(self):
        """Test chat request without user_id"""
        event = {"body": json.dumps({"message": "Create a model"})}

        response = handle_chat(event)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "user_id is required" in body["error"]

    @patch("ai_agent_api.AIAgent")
    def test_handle_chat_with_conversation_history(self, mock_agent_class):
        """Test chat request with conversation history"""
        mock_agent = MagicMock()
        mock_agent.chat.return_value = "Response with context"
        mock_agent_class.return_value = mock_agent

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        event = {
            "body": json.dumps(
                {
                    "message": "What models do I have?",
                    "user_id": "user123",
                    "conversation_history": history,
                }
            )
        }

        response = handle_chat(event)

        assert response["statusCode"] == 200
        mock_agent.chat.assert_called_once_with(
            message="What models do I have?", conversation_history=history, stream=False
        )
