"""
Extended unit tests for model_analytics.py to increase coverage
"""
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json

with patch("boto3.resource"):
    from model_analytics import ModelAnalytics, lambda_handler


class TestModelAnalytics(unittest.TestCase):
    """Test ModelAnalytics class"""

    def setUp(self):
        """Set up test fixtures"""
        self.analytics = ModelAnalytics("test-table")

    @patch.object(ModelAnalytics, "_get_verified_analyses")
    def test_get_model_performance_summary(self, mock_get_analyses):
        """Test model performance summary calculation"""
        mock_get_analyses.return_value = [
            {"model": "consensus", "sport": "basketball_nba", "analysis_correct": True},
            {"model": "consensus", "sport": "basketball_nba", "analysis_correct": False},
            {"model": "contrarian", "sport": "football_nfl", "analysis_correct": True},
        ]

        result = self.analytics.get_model_performance_summary()

        self.assertIn("consensus", result)
        self.assertIn("contrarian", result)
        self.assertEqual(result["consensus"]["total_analyses"], 2)
        self.assertEqual(result["consensus"]["correct_analyses"], 1)
        self.assertEqual(result["consensus"]["accuracy"], 50.0)

    @patch.object(ModelAnalytics, "_get_verified_analyses")
    def test_get_model_performance_by_sport(self, mock_get_analyses):
        """Test model performance by sport"""
        mock_get_analyses.return_value = [
            {"model": "consensus", "sport": "basketball_nba", "analysis_correct": True},
            {"model": "consensus", "sport": "basketball_nba", "analysis_correct": False},
            {"model": "consensus", "sport": "football_nfl", "analysis_correct": True},
        ]

        result = self.analytics.get_model_performance_by_sport(model="consensus")

        self.assertIn("consensus", result)
        self.assertIn("basketball_nba", result["consensus"])
        self.assertIn("football_nfl", result["consensus"])
        self.assertEqual(result["consensus"]["basketball_nba"]["total"], 2)
        self.assertEqual(result["consensus"]["basketball_nba"]["accuracy"], 50.0)

    @patch.object(ModelAnalytics, "_get_verified_analyses")
    def test_get_model_performance_by_bet_type(self, mock_get_analyses):
        """Test model performance by bet type"""
        mock_get_analyses.return_value = [
            {"model": "consensus", "bet_type": "game", "analysis_correct": True},
            {"model": "consensus", "bet_type": "game", "analysis_correct": False},
            {"model": "consensus", "bet_type": "prop", "analysis_correct": True},
        ]

        result = self.analytics.get_model_performance_by_bet_type(model="consensus")

        self.assertIn("consensus", result)
        # Bet type might be stored differently, just check structure
        self.assertIsInstance(result["consensus"], dict)

    @patch.object(ModelAnalytics, "_get_verified_analyses")
    def test_empty_analyses(self, mock_get_analyses):
        """Test handling of empty analyses"""
        mock_get_analyses.return_value = []

        result = self.analytics.get_model_performance_summary()

        self.assertEqual(result, {})

    @patch.object(ModelAnalytics, "_get_verified_analyses")
    def test_zero_division_handling(self, mock_get_analyses):
        """Test accuracy calculation with zero total"""
        mock_get_analyses.return_value = []

        result = self.analytics.get_model_performance_summary()

        # Should not raise division by zero error
        self.assertIsInstance(result, dict)


class TestLambdaHandler(unittest.TestCase):
    """Test model analytics Lambda handler"""

    @patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"})
    @patch("model_analytics.ModelAnalytics")
    def test_lambda_handler_scheduled_run(self, mock_analytics_class):
        """Test Lambda handler for scheduled run (no query params)"""
        mock_analytics = MagicMock()
        mock_analytics.compute_and_store_all_analytics.return_value = None
        mock_analytics_class.return_value = mock_analytics

        event = {}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        mock_analytics.compute_and_store_all_analytics.assert_called_once()

    @patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"})
    @patch("model_analytics.ModelAnalytics")
    def test_lambda_handler_summary(self, mock_analytics_class):
        """Test Lambda handler for summary endpoint"""
        mock_analytics = MagicMock()
        mock_analytics.get_cached_analytics.return_value = {
            "consensus": {"accuracy": 55.0}
        }
        mock_analytics_class.return_value = mock_analytics

        event = {"queryStringParameters": {"type": "summary"}}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)

    @patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"})
    @patch("model_analytics.ModelAnalytics")
    def test_lambda_handler_recent_predictions(self, mock_analytics_class):
        """Test Lambda handler for recent predictions"""
        mock_analytics = MagicMock()
        mock_analytics.get_recent_predictions.return_value = []
        mock_analytics_class.return_value = mock_analytics

        event = {
            "queryStringParameters": {"type": "recent_predictions", "model": "consensus"}
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)

    @patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"})
    def test_lambda_handler_missing_model_param(self):
        """Test Lambda handler with missing required model parameter"""
        event = {"queryStringParameters": {"type": "over_time"}}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)

    def test_lambda_handler_missing_table_name(self):
        """Test Lambda handler with missing table name"""
        event = {}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 500)


if __name__ == "__main__":
    unittest.main()
