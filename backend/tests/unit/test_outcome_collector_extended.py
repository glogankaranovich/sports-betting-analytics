"""
Extended unit tests for outcome_collector.py to increase coverage
"""
import unittest
from unittest.mock import patch, MagicMock
import json

with patch("boto3.resource"), patch("boto3.client"):
    from outcome_collector import lambda_handler


class TestLambdaHandler(unittest.TestCase):
    """Test outcome collector Lambda handler"""

    @patch.dict(
        "os.environ",
        {"DYNAMODB_TABLE": "test-table", "ODDS_API_SECRET_ARN": "test-arn"},
    )
    @patch("outcome_collector._get_secret_value")
    @patch("outcome_collector.OutcomeCollector")
    def test_lambda_handler_success(self, mock_collector_class, mock_get_secret):
        """Test Lambda handler success"""
        mock_get_secret.return_value = "test-api-key"
        mock_collector = MagicMock()
        mock_collector.collect_recent_outcomes.return_value = {
            "verified": 5,
            "pending": 2,
        }
        mock_collector_class.return_value = mock_collector

        event = {}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        self.assertIn("results", result["body"])

    def test_lambda_handler_missing_env(self):
        """Test Lambda handler with missing environment variables"""
        event = {}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 500)

    @patch.dict(
        "os.environ",
        {"DYNAMODB_TABLE": "test-table", "ODDS_API_SECRET_ARN": "test-arn"},
    )
    @patch("outcome_collector._get_secret_value")
    def test_lambda_handler_error(self, mock_get_secret):
        """Test Lambda handler error handling"""
        mock_get_secret.side_effect = Exception("Test error")

        event = {}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 500)


if __name__ == "__main__":
    unittest.main()
