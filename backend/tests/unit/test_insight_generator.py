import os
import sys
import unittest
from unittest.mock import patch

os.environ["DYNAMODB_TABLE"] = "test-table"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from insight_generator import lambda_handler  # noqa: E402


class TestInsightGenerator(unittest.TestCase):
    @patch("insight_generator.generate_insights_from_analyses")
    def test_lambda_handler_game_insights(self, mock_gen_insights):
        """Test lambda handler for game insights"""
        mock_gen_insights.return_value = [{"id": "1"}, {"id": "2"}]

        event = {
            "sport": "basketball_nba",
            "model": "consensus",
            "analysis_type": "game",
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["body"]["game_insights"], 2)
        self.assertEqual(result["body"]["prop_insights"], 0)
        mock_gen_insights.assert_called_once()

    @patch("insight_generator.generate_insights_from_analyses")
    def test_lambda_handler_prop_insights(self, mock_gen_insights):
        """Test lambda handler for prop insights"""
        mock_gen_insights.return_value = [{"id": "1"}, {"id": "2"}, {"id": "3"}]

        event = {
            "sport": "basketball_nba",
            "model": "consensus",
            "analysis_type": "prop",
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["body"]["game_insights"], 0)
        self.assertEqual(result["body"]["prop_insights"], 3)

    @patch("insight_generator.generate_insights_from_analyses")
    def test_lambda_handler_all_insights(self, mock_gen_insights):
        """Test lambda handler for both game and prop insights"""
        mock_gen_insights.side_effect = [
            [{"id": "1"}, {"id": "2"}],  # game insights
            [{"id": "3"}],  # prop insights
        ]

        event = {
            "sport": "basketball_nba",
            "model": "consensus",
            "analysis_type": "all",
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["body"]["game_insights"], 2)
        self.assertEqual(result["body"]["prop_insights"], 1)
        self.assertEqual(result["body"]["message"], "Generated 3 insights")
        self.assertEqual(mock_gen_insights.call_count, 2)

    @patch("insight_generator.generate_insights_from_analyses")
    def test_lambda_handler_with_confidence_filter(self, mock_gen_insights):
        """Test lambda handler with custom confidence threshold"""
        mock_gen_insights.return_value = [{"id": "1"}]

        event = {
            "sport": "basketball_nba",
            "model": "consensus",
            "analysis_type": "game",
            "min_confidence": "0.7",
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        # Verify min_confidence was passed correctly
        call_args = mock_gen_insights.call_args[0]
        self.assertEqual(call_args[3], 0.7)

    @patch("insight_generator.generate_insights_from_analyses")
    def test_lambda_handler_with_limit(self, mock_gen_insights):
        """Test lambda handler with custom limit"""
        mock_gen_insights.return_value = []

        event = {
            "sport": "basketball_nba",
            "model": "consensus",
            "analysis_type": "game",
            "limit": "5",
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        # Verify limit was passed correctly
        call_args = mock_gen_insights.call_args[0]
        self.assertEqual(call_args[4], 5)

    @patch("insight_generator.generate_insights_from_analyses")
    def test_lambda_handler_defaults(self, mock_gen_insights):
        """Test lambda handler with default parameters"""
        mock_gen_insights.side_effect = [[], []]

        event = {}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        # Should use defaults: basketball_nba, consensus, all, 0.6, 10
        self.assertEqual(mock_gen_insights.call_count, 2)


if __name__ == "__main__":
    unittest.main()
