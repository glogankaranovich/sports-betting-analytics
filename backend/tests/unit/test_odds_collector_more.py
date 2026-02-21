"""More odds collector tests"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from odds_collector import OddsCollector, convert_floats_to_decimal, get_secret


def test_get_secret():
    """Test secret retrieval"""
    with patch("odds_collector.boto3.client") as mock_client:
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {"SecretString": "test-key"}
        mock_client.return_value = mock_sm
        
        secret = get_secret("arn:aws:secretsmanager:us-east-1:123456789012:secret:test")
        assert secret == "test-key"


def test_convert_floats_nested():
    """Test converting nested floats"""
    obj = {
        "price": 1.91,
        "nested": {"value": 2.5},
        "list": [1.1, 2.2]
    }
    
    result = convert_floats_to_decimal(obj)
    assert isinstance(result["price"], Decimal)
    assert isinstance(result["nested"]["value"], Decimal)
    assert isinstance(result["list"][0], Decimal)


def test_get_active_sports():
    """Test getting active sports"""
    with patch("odds_collector.boto3"), \
         patch("odds_collector.os.getenv", return_value="test-key"), \
         patch("odds_collector.requests.get") as mock_get:
        
        mock_get.return_value.json.return_value = [
            {"key": "basketball_nba", "active": True},
            {"key": "cricket_test", "active": True},  # Not supported
            {"key": "americanfootball_nfl", "active": False}  # Not active
        ]
        
        collector = OddsCollector()
        sports = collector.get_active_sports()
        
        assert "basketball_nba" in sports
        assert "cricket_test" not in sports
        assert "americanfootball_nfl" not in sports


def test_get_odds_with_limit():
    """Test getting odds with limit"""
    with patch("odds_collector.boto3"), \
         patch("odds_collector.os.getenv", return_value="test-key"), \
         patch("odds_collector.requests.get") as mock_get:
        
        mock_get.return_value.json.return_value = [
            {"id": "game1"},
            {"id": "game2"},
            {"id": "game3"}
        ]
        
        collector = OddsCollector()
        odds = collector.get_odds("basketball_nba", limit=2)
        
        assert len(odds) == 2


def test_get_player_props_api_call():
    """Test player props API call"""
    with patch("odds_collector.boto3"), \
         patch("odds_collector.os.getenv", return_value="test-key"), \
         patch("odds_collector.requests.get") as mock_get:
        
        mock_get.return_value.json.return_value = {"bookmakers": []}
        
        collector = OddsCollector()
        props = collector.get_player_props("basketball_nba", "game123")
        
        assert isinstance(props, dict)


def test_odds_collector_init_with_secret():
    """Test OddsCollector init with secret ARN"""
    with patch("odds_collector.boto3"), \
         patch("odds_collector.os.getenv") as mock_env, \
         patch("odds_collector.get_secret", return_value="secret-key"):
        
        mock_env.side_effect = lambda key, default=None: {
            "ODDS_API_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123:secret:test",
            "DYNAMODB_TABLE": "test-table"
        }.get(key, default)
        
        collector = OddsCollector()
        assert collector.api_key == "secret-key"


def test_odds_collector_init_fallback():
    """Test OddsCollector init with fallback key"""
    with patch("odds_collector.boto3"), \
         patch("odds_collector.os.getenv") as mock_env:
        
        mock_env.side_effect = lambda key, default=None: {
            "ODDS_API_KEY": "fallback-key",
            "DYNAMODB_TABLE": "test-table"
        }.get(key, default)
        
        collector = OddsCollector()
        assert collector.api_key == "fallback-key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
