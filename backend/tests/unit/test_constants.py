"""Constants tests"""

from constants import SUPPORTED_SPORTS, SYSTEM_MODELS, BET_TYPES


def test_supported_sports():
    """Test supported sports list"""
    assert "basketball_nba" in SUPPORTED_SPORTS
    assert "americanfootball_nfl" in SUPPORTED_SPORTS
    assert len(SUPPORTED_SPORTS) >= 5


def test_system_models():
    """Test system models list"""
    assert "consensus" in SYSTEM_MODELS
    assert "value" in SYSTEM_MODELS
    assert "momentum" in SYSTEM_MODELS


def test_bet_types():
    """Test bet types"""
    assert "game" in BET_TYPES
    assert "prop" in BET_TYPES


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
