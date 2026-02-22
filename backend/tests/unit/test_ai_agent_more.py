"""AI agent tests"""

import os
from unittest.mock import Mock, patch

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from ai_agent import AIAgent


@pytest.fixture
def agent():
    with patch("ai_agent.boto3"):
        return AIAgent()


def test_execute_tool_create_model(agent):
    """Test create_model tool execution"""
    with patch.object(agent, "_create_model", return_value={"success": True}):
        result = agent.execute_tool("create_model", {}, "user123")
        assert result["success"] is True


def test_execute_tool_analyze_predictions(agent):
    """Test analyze_predictions tool execution"""
    with patch.object(agent, "_analyze_predictions", return_value={"total": 10}):
        result = agent.execute_tool("analyze_predictions", {}, "user123")
        assert "total" in result


def test_execute_tool_query_stats(agent):
    """Test query_stats tool execution"""
    with patch.object(agent, "_query_stats", return_value={"stats": {}}):
        result = agent.execute_tool("query_stats", {})
        assert "stats" in result


def test_execute_tool_explain_prediction(agent):
    """Test explain_prediction tool execution"""
    with patch.object(agent, "_explain_prediction", return_value={"explanation": "test"}):
        result = agent.execute_tool("explain_prediction", {}, "user123")
        assert "explanation" in result


def test_execute_tool_list_user_models(agent):
    """Test list_user_models tool execution"""
    with patch.object(agent, "_list_user_models", return_value={"models": []}):
        result = agent.execute_tool("list_user_models", {}, "user123")
        assert "models" in result


def test_execute_tool_analyze_bet(agent):
    """Test analyze_bet tool execution"""
    with patch.object(agent, "_analyze_bet", return_value={"recommendation": "pass"}):
        result = agent.execute_tool("analyze_bet", {})
        assert "recommendation" in result


def test_execute_tool_unknown(agent):
    """Test unknown tool"""
    result = agent.execute_tool("unknown_tool", {})
    assert "error" in result


def test_create_model_validation_error(agent):
    """Test create_model with validation errors"""
    with patch("ai_agent.validate_model_config", return_value=["Error"]):
        result = agent._create_model({
            "model_name": "Test",
            "sport": "basketball_nba",
            "bet_types": ["game"],
            "data_sources": []
        }, "user123")
        
        assert result["success"] is False
        assert "errors" in result


def test_create_model_success(agent):
    """Test successful model creation"""
    with patch("ai_agent.validate_model_config", return_value=[]), \
         patch("ai_agent.UserModel") as mock_model:
        
        mock_instance = Mock()
        mock_model.create.return_value = mock_instance
        
        result = agent._create_model({
            "model_name": "Test Model",
            "sport": "basketball_nba",
            "bet_types": ["game"],
            "data_sources": [{"source": "team_stats", "weight": 0.5}]
        }, "user123")
        
        assert result["success"] is True
        assert "model_id" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
