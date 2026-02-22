"""Backfill tests"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from backfill_historical_odds import HistoricalOddsBackfill


@pytest.fixture
def backfill():
    with patch("backfill_historical_odds.boto3"):
        return HistoricalOddsBackfill("test-key", "dev")


def test_init(backfill):
    """Test init"""
    assert backfill.api_key == "test-key"
    assert backfill.requests_used == 0


def test_fetch_historical_odds(backfill):
    """Test fetch"""
    with patch("backfill_historical_odds.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"data": []}
        
        data = backfill._fetch_historical_odds("basketball_nba", "2024-01-15T12:00:00Z")
        assert data is not None


def test_backfill_sport(backfill):
    """Test backfill"""
    with patch.object(backfill, "_fetch_historical_odds", return_value={"data": []}):
        
        backfill.backfill_sport("basketball_nba", datetime(2024, 1, 1), datetime(2024, 1, 2))
        assert backfill._fetch_historical_odds.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
