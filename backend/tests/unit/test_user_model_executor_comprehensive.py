"""
Comprehensive tests for user model executor
"""
import os
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal

os.environ["DYNAMODB_TABLE"] = "test-table"
os.environ["BETS_TABLE"] = "test-bets-table"

from user_model_executor import (
    evaluate_team_stats,
    evaluate_odds_movement,
    evaluate_player_injury,
    evaluate_player_stats,
    evaluate_recent_form,
    evaluate_rest_schedule,
    evaluate_head_to_head,
    calculate_prediction,
    process_model
)


class TestUserModelExecutorComprehensive(unittest.TestCase):

    def test_evaluate_team_stats_neutral_no_data(self):
        """Test team stats returns neutral when no data"""
        with patch("user_model_executor.bets_table") as mock_table:
            mock_table.query.return_value = {"Items": []}
            
            game_data = {
                "sport": "basketball_nba",
                "home_team": "Lakers",
                "away_team": "Warriors"
            }
            
            score = evaluate_team_stats(game_data)
            self.assertEqual(score, 0.5)

    def test_evaluate_team_stats_with_data(self):
        """Test team stats evaluation with actual data"""
        with patch("user_model_executor.bets_table") as mock_table:
            mock_table.query.side_effect = [
                {
                    "Items": [{
                        "stats": {
                            "Field Goal %": "45.0",
                            "Three Point %": "35.0",
                            "Rebounds": "45"
                        }
                    }]
                },
                {
                    "Items": [{
                        "stats": {
                            "Field Goal %": "42.0",
                            "Three Point %": "33.0",
                            "Rebounds": "42"
                        }
                    }]
                }
            ]
            
            game_data = {
                "sport": "basketball_nba",
                "home_team": "Lakers",
                "away_team": "Warriors"
            }
            
            score = evaluate_team_stats(game_data)
            
            # Home team has better stats, should favor home (>0.5)
            self.assertGreater(score, 0.5)
            self.assertLessEqual(score, 1.0)

    def test_evaluate_odds_movement_neutral(self):
        """Test odds movement returns neutral with no data"""
        with patch("user_model_executor.bets_table") as mock_table:
            mock_table.query.return_value = {"Items": []}
            
            game_data = {"game_id": "game123"}
            
            score = evaluate_odds_movement(game_data)
            self.assertEqual(score, 0.5)

    def test_evaluate_odds_movement_sharp_action(self):
        """Test odds movement detects sharp action"""
        with patch("user_model_executor.bets_table") as mock_table:
            mock_table.query.return_value = {
                "Items": [
                    {
                        "sk": "fanduel#h2h#2025-01-01T00:00:00",
                        "home_team": "Lakers",
                        "away_team": "Warriors",
                        "outcomes": [
                            {"name": "Lakers", "price": -110},
                            {"name": "Warriors", "price": -110}
                        ]
                    },
                    {
                        "sk": "fanduel#h2h#2025-01-02T00:00:00",
                        "home_team": "Lakers",
                        "away_team": "Warriors",
                        "outcomes": [
                            {"name": "Lakers", "price": -130},  # Line moved
                            {"name": "Warriors", "price": 110}
                        ]
                    }
                ]
            }
            
            game_data = {"game_id": "game123"}
            
            score = evaluate_odds_movement(game_data)
            
            # Should detect movement
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_evaluate_player_injury_neutral(self):
        """Test player injury returns neutral"""
        game_data = {"home_team": "Lakers", "away_team": "Warriors"}
        
        score = evaluate_player_injury(game_data)
        
        # Currently returns neutral
        self.assertEqual(score, 0.5)

    def test_evaluate_player_stats_neutral(self):
        """Test player stats returns neutral with no data"""
        with patch("user_model_executor.bets_table") as mock_table:
            mock_table.query.return_value = {"Items": []}
            
            game_data = {
                "sport": "basketball_nba",
                "home_team": "Lakers",
                "away_team": "Warriors"
            }
            
            score = evaluate_player_stats(game_data)
            self.assertEqual(score, 0.5)

    def test_evaluate_recent_form_neutral(self):
        """Test recent form returns neutral with no data"""
        with patch("user_model_executor.bets_table") as mock_table:
            mock_table.query.return_value = {"Items": []}
            
            game_data = {
                "sport": "basketball_nba",
                "home_team": "Lakers",
                "away_team": "Warriors"
            }
            
            score = evaluate_recent_form(game_data)
            self.assertEqual(score, 0.5)

    def test_evaluate_rest_schedule_neutral(self):
        """Test rest schedule returns neutral"""
        game_data = {"home_team": "Lakers", "away_team": "Warriors"}
        
        score = evaluate_rest_schedule(game_data)
        self.assertEqual(score, 0.5)

    def test_evaluate_head_to_head_neutral(self):
        """Test head to head returns neutral with no data"""
        with patch("user_model_executor.bets_table") as mock_table:
            mock_table.query.return_value = {"Items": []}
            
            game_data = {
                "sport": "basketball_nba",
                "home_team": "Lakers",
                "away_team": "Warriors"
            }
            
            score = evaluate_head_to_head(game_data)
            self.assertEqual(score, 0.5)



if __name__ == "__main__":
    unittest.main()
