"""Additional outcome collector tests"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from outcome_collector import OutcomeCollector


@pytest.fixture
def collector():
    with patch("outcome_collector.boto3"):
        return OutcomeCollector("test-table", "test-key")


def test_collect_recent_outcomes_with_days_validation(collector):
    """Test days_back validation (1-3 only)"""
    with patch.object(collector, "_get_completed_games", return_value=[]):
        
        # Test invalid days (should default to 3)
        result = collector.collect_recent_outcomes(days_back=5)
        collector._get_completed_games.assert_called_with(3)
        
        result = collector.collect_recent_outcomes(days_back=0)
        collector._get_completed_games.assert_called_with(3)


def test_get_completed_games_api_error(collector):
    """Test API error handling in get_completed_games"""
    with patch("outcome_collector.requests.get") as mock_get:
        mock_get.side_effect = Exception("API error")
        
        games = collector._get_completed_games(3)
        assert games == []


def test_store_outcome_with_scores(collector):
    """Test storing outcome with scores"""
    collector.table = Mock()
    
    game = {
        "id": "game123",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "home_score": 110,
        "away_score": 105,
        "completed_at": "2024-01-15T22:00:00Z"
    }
    
    collector._store_outcome(game)
    
    # Should call put_item 3 times (outcome + 2 team outcomes)
    assert collector.table.put_item.call_count == 3


def test_update_elo_ratings_missing_scores(collector):
    """Test Elo update with missing scores"""
    game = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "home_score": None,
        "away_score": None
    }
    
    result = collector._update_elo_ratings(game)
    assert result is False


def test_store_prop_outcomes_no_props(collector):
    """Test storing prop outcomes when none exist"""
    with patch("outcome_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"data": []}
        
        count = collector._store_prop_outcomes({"id": "game123", "sport": "basketball_nba"})
        assert count == 0


def test_update_analysis_outcomes_no_analysis(collector):
    """Test updating analysis when none exist"""
    collector.table = Mock()
    collector.table.query.return_value = {"Items": []}
    
    game = {
        "id": "game123",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "home_score": 110,
        "away_score": 105
    }
    
    count = collector._update_analysis_outcomes(game)
    assert count == 0


def test_map_sport_name(collector):
    """Test sport name mapping"""
    assert collector._map_sport_name("basketball_nba") == "basketball_nba"
    assert collector._map_sport_name("americanfootball_nfl") == "americanfootball_nfl"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
