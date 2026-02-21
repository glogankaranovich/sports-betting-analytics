"""More team stats collector tests"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from team_stats_collector import TeamStatsCollector


@pytest.fixture
def collector():
    with patch("team_stats_collector.boto3"):
        return TeamStatsCollector()


def test_fetch_espn_team_stats_no_boxscore(collector):
    """Test fetching stats with no boxscore"""
    with patch("team_stats_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {}
        
        stats = collector._fetch_espn_team_stats("401585123", "basketball_nba")
        assert stats is None


def test_fetch_espn_team_stats_no_teams(collector):
    """Test fetching stats with no teams"""
    with patch("team_stats_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"boxscore": {"teams": []}}
        
        stats = collector._fetch_espn_team_stats("401585123", "basketball_nba")
        assert stats is None


def test_fetch_espn_team_stats_success(collector):
    """Test successful stats fetch"""
    with patch("team_stats_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "boxscore": {
                "teams": [
                    {
                        "team": {"displayName": "Lakers"},
                        "statistics": [
                            {"label": "fieldGoalPct", "displayValue": "45.2"}
                        ]
                    }
                ]
            }
        }
        
        stats = collector._fetch_espn_team_stats("401585123", "basketball_nba")
        assert stats is not None
        assert "Lakers" in stats


def test_find_espn_game_id_no_competitions(collector):
    """Test finding game ID with no competitions"""
    game = {
        "home_team": "Lakers",
        "away_team": "Warriors",
        "commence_time": "2024-01-15T20:00:00Z"
    }
    
    with patch("team_stats_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "events": [{"competitions": []}]
        }
        
        game_id = collector._find_espn_game_id(game, "basketball_nba")
        assert game_id is None


def test_find_espn_game_id_insufficient_competitors(collector):
    """Test finding game ID with insufficient competitors"""
    game = {
        "home_team": "Lakers",
        "away_team": "Warriors",
        "commence_time": "2024-01-15T20:00:00Z"
    }
    
    with patch("team_stats_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "events": [{
                "competitions": [{
                    "competitors": [{"team": {"displayName": "Lakers"}}]  # Only 1
                }]
            }]
        }
        
        game_id = collector._find_espn_game_id(game, "basketball_nba")
        assert game_id is None


def test_collect_stats_game_processing_error(collector):
    """Test error handling during game processing"""
    collector.table = Mock()
    collector.table.query.return_value = {
        "Items": [
            {"pk": "GAME#game123", "home_team": "Lakers", "away_team": "Warriors", "commence_time": "2024-01-15T20:00:00Z"}
        ]
    }
    
    with patch.object(collector, "_find_espn_game_id", side_effect=Exception("Error")):
        count = collector.collect_stats_for_sport("basketball_nba")
        # Should handle error and continue
        assert count == 0


def test_convert_to_decimal(collector):
    """Test converting stats to Decimal"""
    stats = {
        "home": {"fieldGoalPct": 0.45},
        "away": {"fieldGoalPct": 0.48}
    }
    
    result = collector._convert_to_decimal(stats)
    
    from decimal import Decimal
    assert isinstance(result["home"]["fieldGoalPct"], Decimal)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
