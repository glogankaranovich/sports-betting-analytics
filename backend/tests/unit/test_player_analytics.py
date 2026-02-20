"""
Unit tests for player analytics
"""
import os
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal

os.environ["DYNAMODB_TABLE"] = "test-table"

from player_analytics import PlayerAnalytics


class TestPlayerAnalytics(unittest.TestCase):
    """Test player analytics"""

    @patch("player_analytics.boto3.resource")
    def setUp(self, mock_resource):
        self.mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = self.mock_table
        self.analytics = PlayerAnalytics()

    def test_calculate_usage_rate(self):
        """Test usage rate calculation"""
        player_stats = [
            {"stats": {"fieldGoalsAttempted": 15, "freeThrowsAttempted": 5, "turnovers": 3}},
            {"stats": {"fieldGoalsAttempted": 18, "freeThrowsAttempted": 6, "turnovers": 2}},
        ]
        team_stats = {"fga": 85, "fta": 25, "tov": 15}
        
        usage = self.analytics.calculate_usage_rate(player_stats, team_stats)
        
        self.assertGreater(usage, 0)
        self.assertLess(usage, 100)
        self.assertIsInstance(usage, float)

    def test_calculate_usage_rate_empty_stats(self):
        """Test usage rate with empty stats"""
        usage = self.analytics.calculate_usage_rate([], {})
        self.assertEqual(usage, 0.0)

    def test_get_home_away_splits(self):
        """Test home/away splits calculation"""
        self.mock_table.query.return_value = {
            "Items": [
                {"is_home": True, "stats": {"points": Decimal("25"), "rebounds": Decimal("8")}},
                {"is_home": True, "stats": {"points": Decimal("30"), "rebounds": Decimal("10")}},
                {"is_home": False, "stats": {"points": Decimal("20"), "rebounds": Decimal("6")}},
            ]
        }
        
        splits = self.analytics.get_home_away_splits("LeBron James", "basketball_nba")
        
        self.assertIn("home", splits)
        self.assertIn("away", splits)
        self.assertIn("home_games", splits)
        self.assertIn("away_games", splits)
        self.assertEqual(splits["home_games"], 2)
        self.assertEqual(splits["away_games"], 1)


if __name__ == "__main__":
    unittest.main()
