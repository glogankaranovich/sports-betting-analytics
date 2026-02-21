"""
Unit tests for games API handler
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import json
from decimal import Decimal

os.environ["DYNAMODB_TABLE"] = "test-table"

from api.games import GamesHandler


class TestGamesHandler(unittest.TestCase):
    """Test games API handler"""

    @patch("api.utils.table")
    def setUp(self, mock_table):
        self.mock_table = mock_table
        self.handler = GamesHandler()

    def test_get_games_success(self):
        """Test getting games successfully"""
        self.mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "sk": "draftkings#h2h",
                    "sport": "basketball_nba",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": "2026-02-21T19:00:00",
                    "updated_at": "2026-02-21T10:00:00",
                    "latest": True,
                    "outcomes": [{"name": "Lakers", "price": -110}]
                }
            ]
        }

        result = self.handler.get_games({"sport": "basketball_nba"})
        
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("games", body)
        self.assertEqual(body["count"], 1)

    def test_get_games_missing_sport(self):
        """Test error when sport parameter missing"""
        result = self.handler.get_games({})
        
        self.assertEqual(result["statusCode"], 400)

    def test_get_player_props_success(self):
        """Test getting player props"""
        self.mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "PROP#game123",
                    "player_name": "LeBron James",
                    "market": "player_points",
                    "line": Decimal("25.5"),
                    "latest": True,
                    "bookmaker": "draftkings"
                }
            ]
        }

        result = self.handler.get_player_props({"sport": "basketball_nba"})
        
        self.assertEqual(result["statusCode"], 200)

    def test_get_player_props_missing_sport(self):
        """Test error when sport missing"""
        result = self.handler.get_player_props({})
        
        self.assertEqual(result["statusCode"], 400)

    def test_get_sports(self):
        """Test getting available sports"""
        self.mock_table.scan.return_value = {
            "Items": [
                {"pk": "GAME#basketball_nba"},
                {"pk": "GAME#americanfootball_nfl"}
            ]
        }

        result = self.handler.get_sports()
        
        self.assertEqual(result["statusCode"], 200)

    def test_get_bookmakers(self):
        """Test getting available bookmakers"""
        self.mock_table.scan.return_value = {
            "Items": [
                {"bookmakers": [{"key": "draftkings"}]}
            ]
        }

        result = self.handler.get_bookmakers()
        
        self.assertEqual(result["statusCode"], 200)

    def test_route_request_games(self):
        """Test routing to games endpoint"""
        self.mock_table.query.return_value = {"Items": []}
        
        result = self.handler.route_request("GET", "/games", {"sport": "basketball_nba"}, {}, {})
        
        self.assertEqual(result["statusCode"], 200)

    def test_route_request_unknown(self):
        """Test unknown endpoint"""
        result = self.handler.route_request("GET", "/unknown", {}, {}, {})
        
        self.assertEqual(result["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
