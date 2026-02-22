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


def test_collect_schedules_no_teams(collector):
    """Test collecting schedules with no teams"""
    with patch.object(collector, "_get_teams", return_value=[]):
        
        count = collector.collect_schedules_for_sport("basketball_nba")
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
