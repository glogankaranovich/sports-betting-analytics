"""
Integration tests for AI Agent
Tests the full flow from API request to LLM response

NOTE: These tests require AWS Bedrock model access to be enabled.
If you get ResourceNotFoundException, submit the Anthropic use case form in AWS Bedrock console.
"""
import os

import pytest
import requests

# Use test table for local tests, but integration tests hit real API
API_URL = os.environ.get(
    "AI_AGENT_API_URL",
    "https://ddzbfblwr0.execute-api.us-east-1.amazonaws.com/prod",
)


@pytest.mark.integration
class TestAIAgentIntegration:
    """Integration tests that call the live API"""

    def test_simple_greeting(self):
        """Test simple greeting returns valid response"""
        response = requests.post(
            f"{API_URL}/ai-agent/chat",
            json={
                "message": "Hello, what can you help me with?",
                "user_id": "test-user",
            },
            timeout=30,
        )

        # Skip if Bedrock access not enabled
        if response.status_code == 500:
            data = response.json()
            if "ResourceNotFoundException" in data.get("error", ""):
                pytest.skip("Bedrock model access not enabled - submit use case form")

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        # Response should be Claude's message format
        assert isinstance(data["response"], dict)

    def test_model_creation_question(self):
        """Test asking about model creation"""
        response = requests.post(
            f"{API_URL}/ai-agent/chat",
            json={
                "message": "How do I create a betting model?",
                "user_id": "test-user",
            },
            timeout=30,
        )

        if response.status_code == 500:
            data = response.json()
            if "ResourceNotFoundException" in data.get("error", ""):
                pytest.skip("Bedrock model access not enabled")

        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_conversation_with_history(self):
        """Test conversation with history context"""
        history = [
            {"role": "user", "content": "What can you do?"},
            {"role": "assistant", "content": "I can help with betting models"},
        ]

        response = requests.post(
            f"{API_URL}/ai-agent/chat",
            json={
                "message": "Can you explain more?",
                "user_id": "test-user",
                "conversation_history": history,
            },
            timeout=30,
        )

        if response.status_code == 500:
            data = response.json()
            if "ResourceNotFoundException" in data.get("error", ""):
                pytest.skip("Bedrock model access not enabled")

        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_missing_user_id(self):
        """Test error handling for missing user_id"""
        response = requests.post(
            f"{API_URL}/ai-agent/chat",
            json={"message": "Hello"},
            timeout=30,
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "user_id is required" in data["error"]

    def test_missing_message(self):
        """Test error handling for missing message"""
        response = requests.post(
            f"{API_URL}/ai-agent/chat",
            json={"user_id": "test-user"},
            timeout=30,
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "message is required" in data["error"]

    def test_invalid_endpoint(self):
        """Test 404 for invalid endpoint"""
        response = requests.post(
            f"{API_URL}/ai-agent/invalid",
            json={"message": "Hello", "user_id": "test-user"},
            timeout=30,
        )

        # API Gateway returns 403 for missing routes
        assert response.status_code in [403, 404]
