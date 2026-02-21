"""More user model executor tests"""

from unittest.mock import Mock, patch

import pytest

from user_model_executor import (
    evaluate_team_stats,
    evaluate_odds_movement,
    evaluate_player_stats,
    evaluate_recent_form
)


def test_evaluate_team_stats_no_home_stats():
    """Test team stats with missing home stats"""
    with patch("user_model_executor.bets_table") as mock_table:
        mock_table.query.side_effect = [
            {"Items": []},  # No home stats
            {"Items": [{"stats": {"Field Goal %": "48.0"}}]}  # Away stats
        ]
        
        game_data = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors"
        }
        
        score = evaluate_team_stats(game_data)
        assert score == 0.5


def test_evaluate_team_stats_no_away_stats():
    """Test team stats with missing away stats"""
    with patch("user_model_executor.bets_table") as mock_table:
        mock_table.query.side_effect = [
            {"Items": [{"stats": {"Field Goal %": "45.0"}}]},  # Home stats
            {"Items": []}  # No away stats
        ]
        
        game_data = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors"
        }
        
        score = evaluate_team_stats(game_data)
        assert score == 0.5


def test_evaluate_odds_movement_no_game_id():
    """Test odds movement with missing game_id"""
    game_data = {}
    
    score = evaluate_odds_movement(game_data)
    assert score == 0.5


def test_evaluate_odds_movement_no_items():
    """Test odds movement with no historical data"""
    with patch("user_model_executor.bets_table") as mock_table:
        mock_table.query.return_value = {"Items": []}
        
        game_data = {"game_id": "game123"}
        
        score = evaluate_odds_movement(game_data)
        assert score == 0.5


def test_evaluate_player_stats_no_player():
    """Test player stats with missing player_name"""
    game_data = {}
    
    score = evaluate_player_stats(game_data)
    assert score == 0.5


def test_evaluate_player_stats_no_data():
    """Test player stats with no data"""
    with patch("user_model_executor.bets_table") as mock_table:
        mock_table.query.return_value = {"Items": []}
        
        game_data = {"player_name": "LeBron James"}
        
        score = evaluate_player_stats(game_data)
        assert score == 0.5


def test_evaluate_recent_form_no_team():
    """Test recent form with missing team"""
    game_data = {}
    
    score = evaluate_recent_form(game_data)
    assert score == 0.5


def test_evaluate_recent_form_no_outcomes():
    """Test recent form with no outcomes"""
    with patch("user_model_executor.bets_table") as mock_table:
        mock_table.query.return_value = {"Items": []}
        
        game_data = {"home_team": "Lakers", "sport": "basketball_nba"}
        
        score = evaluate_recent_form(game_data)
        assert score == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
