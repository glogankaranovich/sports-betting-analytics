"""ESPN collector tests"""

from unittest.mock import Mock, patch

import pytest

from espn_collector import ESPNCollector


@pytest.fixture
def collector():
    return ESPNCollector()


def test_init(collector):
    """Test init"""
    assert collector.base_url is not None
    assert "basketball_nba" in collector.sport_mappings


def test_collect_news_unsupported_sport(collector):
    """Test unsupported sport"""
    result = collector.collect_news_for_sport("cricket")
    assert result["news_collected"] == 0


def test_sport_mappings(collector):
    """Test sport mappings exist"""
    assert "americanfootball_nfl" in collector.sport_mappings
    assert "baseball_mlb" in collector.sport_mappings
    assert "icehockey_nhl" in collector.sport_mappings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
