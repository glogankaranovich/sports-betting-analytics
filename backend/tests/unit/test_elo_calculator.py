"""
Unit tests for Elo rating calculator
"""
import os
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal

os.environ["DYNAMODB_TABLE"] = "test-table"

from elo_calculator import EloCalculator


class TestEloCalculator(unittest.TestCase):
    """Test Elo rating calculator"""

    @patch("elo_calculator.boto3.resource")
    def setUp(self, mock_resource):
        self.mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = self.mock_table
        self.calculator = EloCalculator()

    def test_calculate_expected_score(self):
        """Test expected score calculation"""
        expected = self.calculator.calculate_expected_score(1600, 1400)
        self.assertGreater(expected, 0.5)  # Higher rated team should have >50% chance
        self.assertLess(expected, 1.0)

    def test_update_ratings_home_win(self):
        """Test rating update when home team wins"""
        self.mock_table.query.return_value = {"Items": []}  # New teams, use default rating
        
        new_home, new_away = self.calculator.update_ratings(
            "basketball_nba", "Lakers", "Warriors", home_score=100, away_score=90
        )
        self.assertGreater(new_home, 1500)  # Winner gains rating
        self.assertLess(new_away, 1500)     # Loser loses rating

    def test_update_ratings_away_win(self):
        """Test rating update when away team wins"""
        self.mock_table.query.return_value = {"Items": []}
        
        new_home, new_away = self.calculator.update_ratings(
            "basketball_nba", "Lakers", "Warriors", home_score=90, away_score=100
        )
        self.assertLess(new_home, 1500)
        self.assertGreater(new_away, 1500)

    def test_get_team_rating_exists(self):
        """Test getting existing team rating"""
        self.mock_table.query.return_value = {
            "Items": [{"rating": Decimal("1600")}]
        }
        
        rating = self.calculator.get_team_rating("basketball_nba", "Lakers")
        self.assertEqual(rating, 1600)

    def test_get_team_rating_new_team(self):
        """Test getting rating for new team returns default"""
        self.mock_table.query.return_value = {"Items": []}
        
        rating = self.calculator.get_team_rating("basketball_nba", "NewTeam")
        self.assertEqual(rating, 1500)  # Default rating

    def test_save_rating(self):
        """Test saving team rating"""
        self.calculator._store_rating("basketball_nba", "Lakers", 1650, "2026-02-20T00:00:00")
        self.mock_table.put_item.assert_called_once()

    def test_process_game_result(self):
        """Test processing game result"""
        self.mock_table.query.return_value = {"Items": []}
        
        game_data = {
            "sport": "basketball_nba",
            "status": {"type": {"completed": True}},
            "competitions": [{
                "competitors": [
                    {"team": {"displayName": "Lakers"}, "score": "110"},
                    {"team": {"displayName": "Warriors"}, "score": "105"}
                ]
            }]
        }
        
        result = self.calculator.process_game_result(game_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], float)
        self.assertIsInstance(result[1], float)


if __name__ == "__main__":
    unittest.main()
