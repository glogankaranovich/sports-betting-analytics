"""
Unit tests for modular API handlers
"""
import unittest
from unittest.mock import patch
import json
import os

os.environ["TABLE_NAME"] = "test-table"
os.environ["DYNAMODB_TABLE"] = "test-table"

with patch("boto3.resource"):
    from api.misc import lambda_handler as misc_handler, handle_health
    from api.games import lambda_handler as games_handler, handle_get_sports, handle_get_bookmakers


class TestMiscHandler(unittest.TestCase):
    """Test misc API handler"""

    def test_health_endpoint(self):
        """Test health check endpoint"""
        event = {"httpMethod": "GET", "path": "/health", "queryStringParameters": None}
        result = misc_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "healthy")

    def test_handle_health(self):
        """Test health handler directly"""
        result = handle_health()
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "healthy")
        self.assertIn("environment", body)


class TestGamesHandler(unittest.TestCase):
    """Test games API handler"""

    @patch("api.games.handler.table")
    def test_get_sports_endpoint(self, mock_table):
        """Test get sports endpoint"""
        mock_table.scan.return_value = {"Items": [
            {"pk": "GAME#basketball_nba", "sport": "basketball_nba"},
            {"pk": "GAME#football_nfl", "sport": "football_nfl"},
        ]}
        
        event = {"httpMethod": "GET", "path": "/sports", "queryStringParameters": None}
        result = games_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("sports", body)

    @patch("api.games.handler.table")
    def test_get_bookmakers_endpoint(self, mock_table):
        """Test get bookmakers endpoint"""
        mock_table.scan.return_value = {"Items": [
            {"bookmaker": "fanduel"},
            {"bookmaker": "draftkings"},
        ]}
        
        event = {"httpMethod": "GET", "path": "/bookmakers", "queryStringParameters": None}
        result = games_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("bookmakers", body)

    @patch("api.games.handler.table")
    def test_handle_get_sports(self, mock_table):
        """Test get sports handler directly"""
        mock_table.scan.return_value = {"Items": [
            {"pk": "GAME#basketball_nba", "sport": "basketball_nba"},
        ]}
        result = handle_get_sports()
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("sports", body)

    @patch("api.games.handler.table")
    def test_handle_get_bookmakers(self, mock_table):
        """Test get bookmakers handler directly"""
        mock_table.scan.return_value = {"Items": [
            {"bookmaker": "fanduel"},
        ]}
        result = handle_get_bookmakers()
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("bookmakers", body)


if __name__ == "__main__":
    unittest.main()
