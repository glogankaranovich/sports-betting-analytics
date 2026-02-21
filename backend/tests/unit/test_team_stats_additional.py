"""Additional team stats collector tests"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from team_stats_collector import TeamStatsCollector


@pytest.fixture
def collector():
    with patch("team_stats_collector.boto3"):
        return TeamStatsCollector()


def test_find_espn_game_id_previous_day(collector):
    """Test finding game ID from previous day for late games"""
    game = {
        "home_team": "Lakers",
        "away_team": "Warriors",
        "commence_time": "2024-01-15T02:00:00Z"
    }
    
    with patch("team_stats_collector.requests.get") as mock_get:
        # First call (same day) returns no match
        mock_get.return_value.json.side_effect = [
            {"events": []},
            # Second call (previous day) returns match
            {
                "events": [{
                    "id": "401585123",
                    "competitions": [{
                        "competitors": [
                            {"team": {"displayName": "Lakers"}},
                            {"team": {"displayName": "Warriors"}}
                        ]
                    }]
                }]
            }
        ]
        
        game_id = collector._find_espn_game_id(game, "basketball_nba")
        assert game_id == "401585123"


def test_find_espn_game_id_no_match(collector):
    """Test when no ESPN game found"""
    game = {
        "home_team": "Lakers",
        "away_team": "Warriors",
        "commence_time": "2024-01-15T20:00:00Z"
    }
    
    with patch("team_stats_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"events": []}
        
        game_id = collector._find_espn_game_id(game, "basketball_nba")
        assert game_id is None


def test_fetch_espn_team_stats_error(collector):
    """Test ESPN API error handling"""
    with patch("team_stats_collector.requests.get") as mock_get:
        mock_get.side_effect = Exception("API error")
        
        stats = collector._fetch_espn_team_stats("401585123", "basketball_nba")
        assert stats is None


def test_store_team_stats_with_stats(collector):
    """Test storing team stats"""
    collector.table = Mock()
    
    team_stats = {
        "home": {"fieldGoalPct": 0.45, "rebounds": 42},
        "away": {"fieldGoalPct": 0.48, "rebounds": 38}
    }
    
    collector._store_team_stats("game123", team_stats, "basketball_nba")
    
    # Should call put_item twice (home + away)
    assert collector.table.put_item.call_count == 2


def test_collect_stats_unsupported_sport(collector):
    """Test collecting stats for unsupported sport"""
    count = collector.collect_stats_for_sport("cricket_test")
    assert count == 0


def test_get_completed_games_empty(collector):
    """Test getting completed games with no results"""
    collector.table = Mock()
    collector.table.query.return_value = {"Items": []}
    
    games = collector._get_completed_games("basketball_nba")
    assert games == []


def test_get_completed_games_deduplication(collector):
    """Test game deduplication by pk"""
    collector.table = Mock()
    collector.table.query.return_value = {
        "Items": [
            {"pk": "GAME#game123", "home_team": "Lakers", "away_team": "Warriors"},
            {"pk": "GAME#game123", "home_team": "Lakers", "away_team": "Warriors"},  # Duplicate
            {"pk": "GAME#game456", "home_team": "Celtics", "away_team": "Heat"}
        ]
    }
    
    games = collector._get_completed_games("basketball_nba")
    assert len(games) == 2
    assert games[0]["id"] == "game123"
    assert games[1]["id"] == "game456"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
