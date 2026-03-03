"""Schedule collector tests"""

from unittest.mock import Mock, patch

import pytest

from schedule_collector import ScheduleCollector


@pytest.fixture
def collector():
    with patch("schedule_collector.boto3"):
        return ScheduleCollector()


def test_init(collector):
    """Test init"""
    assert collector.espn_base_url is not None


def test_get_teams_empty(collector):
    """Test getting teams with empty response"""
    with patch("schedule_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"sports": []}
        
        teams = collector._get_teams("basketball_nba")
        assert teams == []


def test_get_teams_with_data(collector):
    """Test getting teams with data"""
    with patch("schedule_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "sports": [{"leagues": [{"teams": [{"team": {"id": "1", "displayName": "Lakers"}}]}]}]
        }
        
        teams = collector._get_teams("basketball_nba")
        assert len(teams) > 0


def test_collect_schedules_no_teams(collector):
    """Test collecting schedules with no teams"""
    with patch.object(collector, "_get_teams", return_value=[]):
        
        count = collector.collect_schedules_for_sport("basketball_nba")
        assert count == 0


def test_get_teams_unsupported_sport(collector):
    """Test getting teams for unsupported sport"""
    teams = collector._get_teams("unsupported_sport")
    assert teams == []


def test_get_teams_api_error(collector):
    """Test handling API errors when getting teams"""
    with patch("schedule_collector.requests.get") as mock_get:
        mock_get.side_effect = Exception("API Error")
        
        teams = collector._get_teams("basketball_nba")
        assert teams == []


def test_fetch_team_schedule_success(collector):
    """Test fetching team schedule successfully"""
    with patch("schedule_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "events": [
                {
                    "id": "game1",
                    "date": "2026-03-15T19:00:00Z",
                    "competitions": [
                        {
                            "competitors": [
                                {"id": "1", "homeAway": "home", "team": {"displayName": "Lakers"}},
                                {"id": "2", "homeAway": "away", "team": {"displayName": "Warriors"}}
                            ]
                        }
                    ]
                }
            ]
        }
        
        schedule = collector._fetch_team_schedule("basketball_nba", "1")
        assert schedule is not None
        assert len(schedule) == 1
        assert schedule[0]["game_id"] == "game1"
        assert schedule[0]["is_home"] is True
        assert schedule[0]["opponent"] == "Warriors"


def test_fetch_team_schedule_away_game(collector):
    """Test fetching schedule with away game"""
    with patch("schedule_collector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "events": [
                {
                    "id": "game1",
                    "date": "2026-03-15T19:00:00Z",
                    "competitions": [
                        {
                            "competitors": [
                                {"id": "1", "homeAway": "home", "team": {"displayName": "Lakers"}},
                                {"id": "2", "homeAway": "away", "team": {"displayName": "Warriors"}}
                            ]
                        }
                    ]
                }
            ]
        }
        
        schedule = collector._fetch_team_schedule("basketball_nba", "2")
        assert schedule[0]["is_home"] is False
        assert schedule[0]["opponent"] == "Lakers"


def test_fetch_team_schedule_unsupported_sport(collector):
    """Test fetching schedule for unsupported sport"""
    schedule = collector._fetch_team_schedule("unsupported_sport", "1")
    assert schedule is None


def test_fetch_team_schedule_api_error(collector):
    """Test handling API errors when fetching schedule"""
    with patch("schedule_collector.requests.get") as mock_get:
        mock_get.side_effect = Exception("API Error")
        
        schedule = collector._fetch_team_schedule("basketball_nba", "1")
        assert schedule is None


def test_get_opponent(collector):
    """Test getting opponent from competitors"""
    competitors = [
        {"id": "1", "team": {"displayName": "Lakers"}},
        {"id": "2", "team": {"displayName": "Warriors"}}
    ]
    
    opponent = collector._get_opponent(competitors, "1")
    assert opponent == "Warriors"
    
    opponent = collector._get_opponent(competitors, "2")
    assert opponent == "Lakers"


def test_get_opponent_not_found(collector):
    """Test getting opponent when competitors list is empty"""
    competitors = []
    
    opponent = collector._get_opponent(competitors, "1")
    assert opponent == "Unknown"


def test_store_schedule_calculates_rest_days(collector):
    """Test that rest days are calculated correctly"""
    collector.table = Mock()
    
    schedule = [
        {"game_id": "1", "game_date": "2026-03-10T19:00:00Z", "is_home": True, "opponent": "Team A"},
        {"game_id": "2", "game_date": "2026-03-13T19:00:00Z", "is_home": False, "opponent": "Team B"},
        {"game_id": "3", "game_date": "2026-03-15T19:00:00Z", "is_home": True, "opponent": "Team C"},
    ]
    
    collector._store_schedule("basketball_nba", "lakers", schedule)
    
    # Should call put_item 3 times
    assert collector.table.put_item.call_count == 3
    
    # Check rest days calculation
    calls = collector.table.put_item.call_args_list
    
    # First game: 0 rest days (no previous game)
    assert calls[0][1]["Item"]["rest_days"] == 0
    
    # Second game: 2 rest days (3 days - 1)
    assert calls[1][1]["Item"]["rest_days"] == 2
    
    # Third game: 1 rest day (2 days - 1)
    assert calls[2][1]["Item"]["rest_days"] == 1


def test_store_schedule_includes_ttl(collector):
    """Test that TTL is set correctly"""
    collector.table = Mock()
    
    schedule = [
        {"game_id": "1", "game_date": "2026-03-10T19:00:00Z", "is_home": True, "opponent": "Team A"}
    ]
    
    collector._store_schedule("basketball_nba", "lakers", schedule)
    
    item = collector.table.put_item.call_args[1]["Item"]
    assert "ttl" in item
    assert item["ttl"] > 0


def test_all_sports_supported(collector):
    """Test that all 10 sports are in SPORT_MAP"""
    expected_sports = [
        "basketball_nba",
        "basketball_wnba", 
        "basketball_ncaab",
        "basketball_wncaab",
        "americanfootball_nfl",
        "americanfootball_ncaaf",
        "baseball_mlb",
        "icehockey_nhl",
        "soccer_epl",
        "soccer_usa_mls"
    ]
    
    for sport in expected_sports:
        assert sport in ScheduleCollector.SPORT_MAP


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
