import os
import unittest
from unittest.mock import MagicMock, patch, Mock
import json


class TestAIAgent(unittest.TestCase):
    def setUp(self):
        os.environ["DYNAMODB_TABLE"] = "test-table"

    @patch("ai_agent.boto3")
    def test_init(self, mock_boto3):
        """Test AIAgent initialization"""
        from ai_agent import AIAgent

        agent = AIAgent()
        self.assertIsNotNone(agent.bedrock)
        self.assertIsNotNone(agent.table)

    @patch("ai_agent.boto3")
    def test_execute_tool_create_model(self, mock_boto3):
        """Test executing create_model tool"""
        from ai_agent import AIAgent

        agent = AIAgent()
        
        with patch.object(agent, "_create_model") as mock_create:
            mock_create.return_value = {"success": True}
            
            result = agent.execute_tool(
                "create_model",
                {"model_name": "Test", "sport": "basketball_nba"},
                "user123"
            )
            
            mock_create.assert_called_once()

    @patch("ai_agent.boto3")
    def test_execute_tool_unknown(self, mock_boto3):
        """Test executing unknown tool"""
        from ai_agent import AIAgent

        agent = AIAgent()
        result = agent.execute_tool("unknown_tool", {})
        
        self.assertIn("error", result)

    @patch("ai_agent.boto3")
    @patch("ai_agent.validate_model_config")
    @patch("ai_agent.UserModel")
    def test_create_model(self, mock_user_model, mock_validate, mock_boto3):
        """Test creating a model"""
        from ai_agent import AIAgent

        mock_validate.return_value = []
        mock_model = Mock()
        mock_user_model.create.return_value = mock_model

        agent = AIAgent()
        result = agent._create_model({
            "model_name": "Test Model",
            "sport": "basketball_nba",
            "bet_types": ["games"],
            "data_sources": ["team_stats"]
        }, "user123")

        self.assertTrue(result["success"])
        self.assertIn("model_id", result)

    @patch("ai_agent.boto3")
    @patch("ai_agent.validate_model_config")
    def test_create_model_validation_error(self, mock_validate, mock_boto3):
        """Test creating model with validation errors"""
        from ai_agent import AIAgent

        mock_validate.return_value = ["Invalid sport"]

        agent = AIAgent()
        result = agent._create_model({
            "model_name": "Test",
            "sport": "invalid",
            "bet_types": [],
            "data_sources": []
        })

        self.assertFalse(result["success"])
        self.assertIn("errors", result)

    @patch("ai_agent.boto3")
    def test_analyze_predictions(self, mock_boto3):
        """Test analyzing predictions"""
        from ai_agent import AIAgent

        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}

        agent = AIAgent()
        result = agent._analyze_predictions({"days": 7}, "user123")

        self.assertIn("total_predictions", result)

    @patch("ai_agent.boto3")
    def test_query_stats(self, mock_boto3):
        """Test querying stats"""
        from ai_agent import AIAgent

        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}

        agent = AIAgent()
        result = agent._query_stats({
            "stat_type": "team",
            "team": "Lakers",
            "sport": "basketball_nba"
        })

        self.assertIsInstance(result, dict)

    @patch("ai_agent.boto3")
    @patch("ai_agent.UserModel")
    def test_list_user_models(self, mock_user_model, mock_boto3):
        """Test listing user models"""
        from ai_agent import AIAgent

        mock_model = Mock()
        mock_model.to_dict.return_value = {"model_id": "model123"}
        mock_user_model.list_by_user.return_value = [mock_model]

        agent = AIAgent()
        result = agent._list_user_models({}, "user123")

        self.assertIn("models", result)
        self.assertEqual(len(result["models"]), 1)

    @patch("ai_agent.AIAgent")
    def test_lambda_handler(self, mock_agent_class):
        """Test lambda handler"""
        from ai_agent import lambda_handler

        mock_agent = Mock()
        mock_agent._invoke_model.return_value = "Test response"
        mock_agent._get_tools.return_value = []
        mock_agent.system_prompt = "Test prompt"
        mock_agent_class.return_value = mock_agent

        event = {
            "body": json.dumps({
                "message": "Hello",
                "stream": False
            })
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 200)


if __name__ == "__main__":
    unittest.main()
