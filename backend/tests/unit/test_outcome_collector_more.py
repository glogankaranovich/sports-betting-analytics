"""More outcome collector tests"""

import os
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from outcome_collector import OutcomeCollector


@pytest.fixture
def collector():
    with patch("outcome_collector.boto3"):
        return OutcomeCollector("test-table", "test-key")


def test_store_outcome_tie_game(collector):
    """Test storing outcome for tie game"""
    collector.table = Mock()
    
    game = {
        "id": "game123",
        "sport": "soccer_epl",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_score": 2,
        "away_score": 2,
        "completed_at": "2024-01-15T22:00:00Z"
    }
    
    collector._store_outcome(game)
    assert collector.table.put_item.call_count == 3


def test_update_elo_ratings_success(collector):
    """Test successful Elo update"""
    collector.elo_calculator = Mock()
    
    game = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "home_score": 110,
        "away_score": 105
    }
    
    result = collector._update_elo_ratings(game)
    assert result is True
    collector.elo_calculator.update_ratings.assert_called_once()


def test_update_elo_ratings_error(collector):
    """Test Elo update with error"""
    collector.elo_calculator = Mock()
    collector.elo_calculator.update_ratings.side_effect = Exception("Error")
    
    game = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "home_score": 110,
        "away_score": 105
    }
    
    result = collector._update_elo_ratings(game)
    assert result is False


def test_get_completed_games_multiple_sports(collector):
    """Test getting completed games for multiple sports"""
    with patch("outcome_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [
                {
                    "id": "game123",
                    "completed": True,
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "scores": [{"score": "110"}, {"score": "105"}]
                }
            ]
        }
        
        games = collector._get_completed_games(3)
        # Should call API for each sport
        assert mock_get.call_count >= 5


def test_map_sport_name_all_sports(collector):
    """Test sport name mapping for all supported sports"""
    assert collector._map_sport_name("basketball_nba") == "basketball_nba"
    assert collector._map_sport_name("americanfootball_nfl") == "americanfootball_nfl"
    assert collector._map_sport_name("baseball_mlb") == "baseball_mlb"
    assert collector._map_sport_name("icehockey_nhl") == "icehockey_nhl"
    assert collector._map_sport_name("soccer_epl") == "soccer_epl"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



def test_store_outcome_tie_game(collector):
    """Test storing outcome for tie game"""
    collector.table = Mock()
    
    game = {
        "id": "game123",
        "sport": "soccer_epl",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_score": 2,
        "away_score": 2,
        "completed_at": "2024-01-15T22:00:00Z"
    }
    
    collector._store_outcome(game)
    assert collector.table.put_item.call_count == 3


def test_update_elo_ratings_success(collector):
    """Test successful Elo update"""
    collector.elo_calculator = Mock()
    
    game = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "home_score": 110,
        "away_score": 105
    }
    
    result = collector._update_elo_ratings(game)
    assert result is True
    collector.elo_calculator.update_ratings.assert_called_once()


def test_update_elo_ratings_error(collector):
    """Test Elo update with error"""
    collector.elo_calculator = Mock()
    collector.elo_calculator.update_ratings.side_effect = Exception("Error")
    
    game = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "home_score": 110,
        "away_score": 105
    }
    
    result = collector._update_elo_ratings(game)
    assert result is False


def test_get_completed_games_multiple_sports(collector):
    """Test getting completed games for multiple sports"""
    with patch("outcome_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [
                {
                    "id": "game123",
                    "completed": True,
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "scores": [{"score": "110"}, {"score": "105"}]
                }
            ]
        }
        
        games = collector._get_completed_games(3)
        # Should call API for each sport
        assert mock_get.call_count >= 5


def test_map_sport_name_all_sports(collector):
    """Test sport name mapping for all supported sports"""
    assert collector._map_sport_name("basketball_nba") == "basketball_nba"
    assert collector._map_sport_name("americanfootball_nfl") == "americanfootball_nfl"
    assert collector._map_sport_name("baseball_mlb") == "baseball_mlb"
    assert collector._map_sport_name("icehockey_nhl") == "icehockey_nhl"
    assert collector._map_sport_name("soccer_epl") == "soccer_epl"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
