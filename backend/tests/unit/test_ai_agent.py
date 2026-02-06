"""
Unit tests for AI Agent
"""
import json
import unittest
from unittest.mock import MagicMock, patch

from ai_agent import AIAgent


class TestAIAgent(unittest.TestCase):
    def setUp(self):
        self.agent = AIAgent()

    def test_get_tools(self):
        """Test that tools are properly defined"""
        tools = self.agent._get_tools()

        self.assertEqual(len(tools), 4)
        tool_names = [t["name"] for t in tools]
        self.assertIn("create_model", tool_names)
        self.assertIn("analyze_predictions", tool_names)
        self.assertIn("query_stats", tool_names)
        self.assertIn("explain_prediction", tool_names)

    def test_create_model_tool_schema(self):
        """Test create_model tool has correct schema"""
        tools = self.agent._get_tools()
        create_model = next(t for t in tools if t["name"] == "create_model")

        self.assertIn("input_schema", create_model)
        schema = create_model["input_schema"]
        self.assertIn("model_name", schema["properties"])
        self.assertIn("sport", schema["properties"])
        self.assertIn("bet_types", schema["properties"])
        self.assertIn("data_sources", schema["properties"])

    @patch("ai_agent.boto3.client")
    def test_invoke_model(self, mock_boto3):
        """Test non-streaming model invocation"""
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock

        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {
                        "content": [
                            {"text": "Hello! I can help you create betting models."}
                        ],
                        "stop_reason": "end_turn",
                    }
                ).encode()
            )
        }
        mock_bedrock.invoke_model.return_value = mock_response

        agent = AIAgent()
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": agent.system_prompt,
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": agent._get_tools(),
            "temperature": 0.7,
        }

        response = agent._invoke_model(request_body)

        self.assertIn("content", response)
        mock_bedrock.invoke_model.assert_called_once()

    def test_system_prompt(self):
        """Test system prompt is defined"""
        self.assertIsNotNone(self.agent.system_prompt)
        self.assertIn("betting analyst", self.agent.system_prompt.lower())
        self.assertIn("model", self.agent.system_prompt.lower())

    @patch.object(AIAgent, "_get_recent_team_stats")
    @patch.object(AIAgent, "_get_recent_predictions")
    @patch.object(AIAgent, "_get_recent_games")
    def test_retrieve_context_team_query(
        self, mock_games, mock_predictions, mock_stats
    ):
        """Test context retrieval for team-related queries"""
        mock_stats.return_value = [{"team": "Lakers", "wins": 10}]
        mock_predictions.return_value = []
        mock_games.return_value = []

        context = self.agent.retrieve_context("Show me team stats")

        self.assertIn("team statistics", context.lower())
        mock_stats.assert_called_once()

    @patch.object(AIAgent, "_get_recent_team_stats")
    @patch.object(AIAgent, "_get_recent_predictions")
    @patch.object(AIAgent, "_get_recent_games")
    def test_retrieve_context_prediction_query(
        self, mock_games, mock_predictions, mock_stats
    ):
        """Test context retrieval for prediction-related queries"""
        mock_stats.return_value = []
        mock_predictions.return_value = [{"model": "test", "accuracy": 0.75}]
        mock_games.return_value = []

        context = self.agent.retrieve_context("How accurate are my predictions?")

        self.assertIn("predictions", context.lower())
        mock_predictions.assert_called_once()

    @patch.object(AIAgent, "_get_recent_team_stats")
    @patch.object(AIAgent, "_get_recent_predictions")
    @patch.object(AIAgent, "_get_recent_games")
    def test_retrieve_context_game_query(
        self, mock_games, mock_predictions, mock_stats
    ):
        """Test context retrieval for game-related queries"""
        mock_stats.return_value = []
        mock_predictions.return_value = []
        mock_games.return_value = [
            {"home": "Lakers", "away": "Warriors", "score": "110-105"}
        ]

        context = self.agent.retrieve_context("What were the recent game results?")

        self.assertIn("game outcomes", context.lower())
        mock_games.assert_called_once()

    @patch("ai_agent.UserModel")
    @patch("ai_agent.boto3")
    @patch("ai_agent.validate_model_config")
    def test_create_model_tool(self, mock_validate, mock_boto3, mock_user_model):
        """Test create_model tool execution"""
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        mock_validate.return_value = []  # No errors

        mock_model = MagicMock()
        mock_user_model.create.return_value = mock_model

        agent = AIAgent()

        params = {
            "model_name": "Test Model",
            "sport": "basketball_nba",
            "bet_types": ["h2h", "spreads"],
            "data_sources": {
                "team_stats": {"enabled": True, "weight": 0.5},
                "recent_form": {"enabled": True, "weight": 0.5},
            },
        }

        result = agent.execute_tool("create_model", params)

        self.assertTrue(result.get("success"), f"Error: {result.get('error')}")
        self.assertIn("model_id", result)

    @patch("ai_agent.boto3")
    def test_analyze_predictions_tool(self, mock_boto3):
        """Test analyze_predictions tool execution"""
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {"outcome": "correct"},
                {"outcome": "correct"},
                {"outcome": "incorrect"},
            ]
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        agent = AIAgent()
        result = agent.execute_tool("analyze_predictions", {"days_back": 7})

        self.assertEqual(result["total_predictions"], 3)
        self.assertEqual(result["correct_predictions"], 2)
        self.assertAlmostEqual(result["accuracy"], 66.67, places=1)

    @patch("ai_agent.boto3")
    def test_query_stats_tool(self, mock_boto3):
        """Test query_stats tool execution"""
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": [{"team": "Lakers", "wins": 10}]}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        agent = AIAgent()
        result = agent.execute_tool(
            "query_stats", {"query_type": "team_stats", "team": "Lakers"}
        )

        self.assertIn("stats", result)
        self.assertEqual(len(result["stats"]), 1)

    @patch("ai_agent.boto3")
    def test_explain_prediction_tool(self, mock_boto3):
        """Test explain_prediction tool execution"""
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "game": "Lakers vs Warriors",
                "prediction": "Lakers",
                "confidence": 0.75,
            }
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        agent = AIAgent()
        result = agent.execute_tool("explain_prediction", {"prediction_id": "test-123"})

        self.assertEqual(result["prediction_id"], "test-123")
        self.assertEqual(result["game"], "Lakers vs Warriors")


if __name__ == "__main__":
    unittest.main()
