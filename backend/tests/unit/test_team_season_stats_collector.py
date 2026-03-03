"""Comprehensive tests for team_season_stats_collector"""

import os
from unittest.mock import Mock, patch
import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from team_season_stats_collector import TeamSeasonStatsCollector


@pytest.fixture
def collector():
    with patch("team_season_stats_collector.boto3"):
        return TeamSeasonStatsCollector()


def test_all_sports_supported(collector):
    """Test all 10 sports are in SPORT_MAP"""
    expected_sports = [
        "basketball_nba", "basketball_wnba", "basketball_ncaab", "basketball_wncaab",
        "americanfootball_nfl", "americanfootball_ncaaf",
        "baseball_mlb", "icehockey_nhl", "soccer_epl", "soccer_usa_mls"
    ]
    for sport in expected_sports:
        assert sport in TeamSeasonStatsCollector.SPORT_MAP


def test_collect_team_stats_unsupported_sport(collector):
    """Test collecting stats for unsupported sport"""
    result = collector.collect_team_stats("cricket", "team1")
    assert result is None


@patch("team_season_stats_collector.requests.get")
def test_collect_team_stats_api_error(mock_get, collector):
    """Test handling API errors"""
    mock_get.side_effect = Exception("API Error")
    
    result = collector.collect_team_stats("basketball_nba", "lal")
    assert result is None


@patch("team_season_stats_collector.requests.get")
def test_collect_team_stats_unsuccessful_response(mock_get, collector):
    """Test handling unsuccessful API response"""
    mock_response = Mock()
    mock_response.json.return_value = {"status": "error"}
    mock_get.return_value = mock_response
    
    result = collector.collect_team_stats("basketball_nba", "lal")
    assert result is None


def test_parse_nba_stats(collector):
    """Test parsing NBA statistics"""
    data = {
        "results": {
            "stats": {
                "categories": [
                    {
                        "stats": [
                            {"name": "avgPoints", "value": 115.5},
                            {"name": "fieldGoalPct", "value": 0.475},
                            {"name": "threePointPct", "value": 0.365},
                            {"name": "avgRebounds", "value": 45.2},
                            {"name": "avgAssists", "value": 25.8},
                            {"name": "avgTurnovers", "value": 12.5},
                            {"name": "avgFieldGoalsAttempted", "value": 88.0},
                            {"name": "avgOffensiveRebounds", "value": 10.5},
                            {"name": "avgFreeThrowsAttempted", "value": 22.0},
                        ]
                    }
                ]
            }
        }
    }
    
    result = collector._parse_nba_stats(data)
    assert result["adjusted_ppg"] == 115.5
    assert result["fg_pct"] == 0.475
    assert result["three_pt_pct"] == 0.365
    assert result["rebounds_per_game"] == 45.2
    assert result["assists_per_game"] == 25.8
    assert "pace" in result
    assert "offensive_efficiency" in result


def test_parse_nba_stats_missing_fields(collector):
    """Test parsing NBA stats with missing fields"""
    data = {
        "results": {
            "stats": {
                "categories": [
                    {
                        "stats": [
                            {"name": "avgPoints", "value": 115.5},
                        ]
                    }
                ]
            }
        }
    }
    
    result = collector._parse_nba_stats(data)
    assert result["adjusted_ppg"] == 115.5
    assert "pace" not in result  # Missing required fields for calculation


def test_parse_nfl_stats(collector):
    """Test parsing NFL statistics"""
    data = {
        "results": {
            "stats": {
                "categories": [
                    {
                        "name": "passing",
                        "stats": [
                            {"name": "yardsPerGame", "value": 275.5},
                            {"name": "passerRating", "value": 98.5},
                        ]
                    },
                    {
                        "name": "rushing",
                        "stats": [
                            {"name": "yardsPerGame", "value": 125.0},
                        ]
                    },
                    {
                        "name": "miscellaneous",
                        "stats": [
                            {"name": "totalYardsPerGame", "value": 400.5},
                            {"name": "turnovers", "value": 15},
                            {"name": "thirdDownConvPct", "value": 42.5},
                        ]
                    }
                ]
            }
        }
    }
    
    result = collector._parse_nfl_stats(data)
    assert result["pass_yards_per_game"] == 275.5
    assert result["pass_efficiency"] == 98.5
    assert result["rush_yards_per_game"] == 125.0
    assert result["adjusted_total_yards"] == 400.5
    assert result["turnovers"] == 15
    assert result["third_down_pct"] == 42.5
    assert result["turnover_differential"] == -15


def test_parse_nhl_stats(collector):
    """Test parsing NHL statistics"""
    data = {
        "results": {
            "stats": {
                "categories": [
                    {
                        "stats": [
                            {"name": "avgGoals", "value": 3.2},
                            {"name": "avgShots", "value": 32.5},
                            {"name": "powerPlayPct", "value": 22.5},
                            {"name": "penaltyKillPct", "value": 82.0},
                            {"name": "avgShotsAgainst", "value": 28.5},
                        ]
                    }
                ]
            }
        }
    }
    
    result = collector._parse_nhl_stats(data)
    assert result["goals_per_game"] == 3.2
    assert result["shots_per_game"] == 32.5
    assert result["power_play_pct"] == 22.5
    assert result["penalty_kill_pct"] == 82.0
    assert result["shots_against_per_game"] == 28.5


def test_parse_mlb_stats(collector):
    """Test parsing MLB statistics"""
    data = {
        "results": {
            "stats": {
                "categories": [
                    {
                        "name": "batting",
                        "stats": [
                            {"name": "OPS", "value": 0.785},
                            {"name": "avg", "value": 0.265},
                        ]
                    },
                    {
                        "name": "pitching",
                        "stats": [
                            {"name": "ERA", "value": 3.85},
                            {"name": "WHIP", "value": 1.25},
                        ]
                    }
                ]
            }
        }
    }
    
    result = collector._parse_mlb_stats(data)
    assert result["ops"] == 0.785
    assert result["batting_avg"] == 0.265
    assert result["era"] == 3.85
    assert result["whip"] == 1.25


def test_parse_soccer_stats(collector):
    """Test parsing soccer statistics"""
    data = {
        "results": {
            "stats": {
                "categories": [
                    {
                        "stats": [
                            {"name": "avgGoals", "value": 2.1},
                            {"name": "avgGoalsAgainst", "value": 1.2},
                            {"name": "avgShots", "value": 15.5},
                            {"name": "avgShotsOnTarget", "value": 6.2},
                            {"name": "possession", "value": 58.5},
                        ]
                    }
                ]
            }
        }
    }
    
    result = collector._parse_soccer_stats(data)
    assert result["goals_per_game"] == 2.1
    assert result["goals_against_per_game"] == 1.2
    assert result["shots_per_game"] == 15.5
    assert result["shots_on_target_per_game"] == 6.2
    assert result["possession_pct"] == 58.5


def test_store_team_stats(collector):
    """Test storing team stats"""
    collector.table = Mock()
    
    stats = {
        "adjusted_ppg": 115.5,
        "fg_pct": 0.475,
        "pace": 100.5
    }
    
    collector.store_team_stats("basketball_nba", "Los Angeles Lakers", "lal", stats)
    
    assert collector.table.put_item.called
    call_args = collector.table.put_item.call_args[1]["Item"]
    assert call_args["pk"] == "ADJUSTED_METRICS#basketball_nba#los_angeles_lakers"
    assert call_args["sport"] == "basketball_nba"
    assert call_args["team_name"] == "Los Angeles Lakers"
    assert call_args["team_abbr"] == "lal"
    assert "metrics" in call_args


def test_store_team_stats_error(collector):
    """Test handling storage errors"""
    collector.table = Mock()
    collector.table.put_item.side_effect = Exception("DynamoDB Error")
    
    # Should not raise exception
    collector.store_team_stats("basketball_nba", "Lakers", "lal", {})


def test_convert_to_decimal(collector):
    """Test converting floats to Decimal"""
    obj = {
        "float_val": 3.14,
        "int_val": 42,
        "str_val": "test",
        "nested": {
            "float": 2.71
        },
        "list": [1.5, 2.5, 3.5]
    }
    
    result = collector._convert_to_decimal(obj)
    
    from decimal import Decimal
    assert isinstance(result["float_val"], Decimal)
    assert result["int_val"] == 42
    assert result["str_val"] == "test"
    assert isinstance(result["nested"]["float"], Decimal)
    assert all(isinstance(v, Decimal) for v in result["list"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
