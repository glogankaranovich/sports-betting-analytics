"""
Extended unit tests for api_handler.py to increase coverage
"""
import unittest
from unittest.mock import patch, MagicMock
import json
import os

os.environ["TABLE_NAME"] = "test-table"

with patch("boto3.resource"):
    from api_handler import (
        lambda_handler,
        handle_health,
        handle_get_sports,
        handle_get_bookmakers,
        calculate_roi,
    )


class TestLambdaHandler(unittest.TestCase):
    """Test API Lambda handler"""

    def test_health_endpoint(self):
        """Test health check endpoint"""
        event = {"httpMethod": "GET", "path": "/health"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "healthy")

    @patch("api_handler.handle_get_sports")
    def test_get_sports_endpoint(self, mock_handler):
        """Test get sports endpoint"""
        mock_handler.return_value = {
            "statusCode": 200,
            "body": json.dumps({"sports": []}),
        }

        event = {"httpMethod": "GET", "path": "/sports"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        mock_handler.assert_called_once()

    @patch("api_handler.handle_get_bookmakers")
    def test_get_bookmakers_endpoint(self, mock_handler):
        """Test get bookmakers endpoint"""
        mock_handler.return_value = {
            "statusCode": 200,
            "body": json.dumps({"bookmakers": []}),
        }

        event = {"httpMethod": "GET", "path": "/bookmakers"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        mock_handler.assert_called_once()

    @patch("api_handler.handle_get_games")
    def test_get_games_endpoint(self, mock_handler):
        """Test get games endpoint"""
        mock_handler.return_value = {
            "statusCode": 200,
            "body": json.dumps({"games": []}),
        }

        event = {
            "httpMethod": "GET",
            "path": "/games",
            "queryStringParameters": {"sport": "basketball_nba"},
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        mock_handler.assert_called_once()

    @patch("api_handler.handle_get_analyses")
    def test_get_analyses_endpoint(self, mock_handler):
        """Test get analyses endpoint"""
        mock_handler.return_value = {
            "statusCode": 200,
            "body": json.dumps({"analyses": []}),
        }

        event = {
            "httpMethod": "GET",
            "path": "/analyses",
            "queryStringParameters": {"sport": "basketball_nba"},
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        mock_handler.assert_called_once()

    def test_invalid_method(self):
        """Test invalid HTTP method - health accepts all methods"""
        event = {"httpMethod": "DELETE", "path": "/health"}
        result = lambda_handler(event, None)

        # Health endpoint accepts all methods
        self.assertEqual(result["statusCode"], 200)

    def test_invalid_path(self):
        """Test invalid path"""
        event = {"httpMethod": "GET", "path": "/invalid"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 404)

    def test_exception_handling(self):
        """Test exception handling in lambda handler"""
        event = None  # Invalid event
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 500)


class TestHealthEndpoint(unittest.TestCase):
    """Test health check endpoint"""

    def test_handle_health(self):
        """Test health check returns correct response"""
        result = handle_health()

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "healthy")
        self.assertIn("environment", body)


class TestSportsEndpoint(unittest.TestCase):
    """Test sports endpoint"""

    @patch("api_handler.table")
    def test_handle_get_sports(self, mock_table):
        """Test get sports returns available sports"""
        mock_table.query.return_value = {
            "Items": [
                {"pk": "GAME#basketball_nba", "sport": "basketball_nba"},
                {"pk": "GAME#football_nfl", "sport": "football_nfl"},
            ]
        }

        result = handle_get_sports()

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("sports", body)


class TestBookmakersEndpoint(unittest.TestCase):
    """Test bookmakers endpoint"""

    @patch("api_handler.table")
    def test_handle_get_bookmakers(self, mock_table):
        """Test get bookmakers returns available bookmakers"""
        mock_table.query.return_value = {
            "Items": [
                {"bookmaker": "fanduel"},
                {"bookmaker": "draftkings"},
            ]
        }

        result = handle_get_bookmakers()

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("bookmakers", body)


class TestCalculateROI(unittest.TestCase):
    """Test ROI calculation"""

    def test_calculate_roi_negative_odds(self):
        """Test ROI calculation with negative odds"""
        result = calculate_roi(-110, 0.60)

        self.assertIn("roi", result)
        self.assertIn("risk_level", result)
        self.assertIn("implied_probability", result)
        self.assertIsInstance(result["roi"], float)

    def test_calculate_roi_positive_odds(self):
        """Test ROI calculation with positive odds"""
        result = calculate_roi(150, 0.60)

        self.assertIn("roi", result)
        self.assertIn("risk_level", result)
        self.assertIn("implied_probability", result)
        self.assertIsInstance(result["roi"], float)

    def test_calculate_roi_zero_confidence(self):
        """Test ROI calculation with zero confidence"""
        result = calculate_roi(-110, 0.0)

        self.assertIn("roi", result)
        self.assertTrue(result["roi"] < 0)


if __name__ == "__main__":
    unittest.main()
