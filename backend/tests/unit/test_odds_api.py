"""
Unit tests for odds_api module
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from odds_api import OddsAPIClient


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    with patch.dict(os.environ, {"ODDS_API_KEY": "test_api_key"}):
        yield


@pytest.fixture
def client(mock_env):
    """Create OddsAPIClient instance"""
    return OddsAPIClient()


@pytest.fixture
def mock_response():
    """Mock requests response"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"data": "test"}
    return response


class TestOddsAPIClient:
    """Test OddsAPIClient class"""

    def test_init(self, client):
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://api.the-odds-api.com/v4"
        assert "americanfootball_nfl" in client.supported_sports
        assert "basketball_nba" in client.supported_sports

    def test_init_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            client = OddsAPIClient()
            assert client.api_key is None

    @patch("odds_api.requests.get")
    def test_get_sports_success(self, mock_get, client):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {"key": "americanfootball_nfl", "title": "NFL"},
            {"key": "basketball_nba", "title": "NBA"},
        ]

        result = client.get_sports()

        assert result is not None
        assert len(result) == 2
        assert result[0]["key"] == "americanfootball_nfl"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "api_key" in call_args[1]["params"]

    @patch("odds_api.requests.get")
    def test_get_sports_error(self, mock_get, client):
        mock_get.return_value.status_code = 401
        mock_get.return_value.text = "Unauthorized"

        result = client.get_sports()

        assert result is None

    @patch("odds_api.requests.get")
    def test_get_odds_success(self, mock_get, client):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "id": "game123",
                "sport_key": "basketball_nba",
                "commence_time": "2026-02-08T19:00:00Z",
                "home_team": "Lakers",
                "away_team": "Celtics",
                "bookmakers": [
                    {
                        "key": "fanduel",
                        "title": "FanDuel",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Lakers", "price": -110},
                                    {"name": "Celtics", "price": -110},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]

        result = client.get_odds("basketball_nba")

        assert result is not None
        assert len(result) == 1
        assert result[0]["home_team"] == "Lakers"
        assert result[0]["away_team"] == "Celtics"

        # Verify request parameters
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["api_key"] == "test_api_key"
        assert params["regions"] == "us"
        assert params["markets"] == "h2h"
        assert params["oddsFormat"] == "american"
        assert params["dateFormat"] == "iso"

    @patch("odds_api.requests.get")
    def test_get_odds_with_custom_markets(self, mock_get, client):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        client.get_odds("basketball_nba", markets="spreads,totals")

        call_args = mock_get.call_args
        assert call_args[1]["params"]["markets"] == "spreads,totals"

    @patch("odds_api.requests.get")
    def test_get_odds_error_401(self, mock_get, client):
        mock_get.return_value.status_code = 401
        mock_get.return_value.text = "Invalid API key"

        result = client.get_odds("basketball_nba")

        assert result is None

    @patch("odds_api.requests.get")
    def test_get_odds_error_404(self, mock_get, client):
        mock_get.return_value.status_code = 404
        mock_get.return_value.text = "Sport not found"

        result = client.get_odds("invalid_sport")

        assert result is None

    @patch("odds_api.requests.get")
    def test_get_odds_error_429(self, mock_get, client):
        mock_get.return_value.status_code = 429
        mock_get.return_value.text = "Rate limit exceeded"

        result = client.get_odds("basketball_nba")

        assert result is None

    @patch("odds_api.requests.get")
    def test_get_odds_network_error(self, mock_get, client):
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            client.get_odds("basketball_nba")

    @patch("odds_api.requests.get")
    def test_get_odds_empty_response(self, mock_get, client):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        result = client.get_odds("basketball_nba")

        assert result == []

    @patch("odds_api.requests.get")
    def test_get_sports_url_construction(self, mock_get, client):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        client.get_sports()

        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.the-odds-api.com/v4/sports"

    @patch("odds_api.requests.get")
    def test_get_odds_url_construction(self, mock_get, client):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        client.get_odds("basketball_nba")

        call_args = mock_get.call_args
        assert (
            call_args[0][0]
            == "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
        )
