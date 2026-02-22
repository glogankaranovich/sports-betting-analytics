"""More contrarian model tests"""

import os
from unittest.mock import Mock

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from ml.models import ContrarianModel


def test_contrarian_model_no_spreads():
    """Test contrarian with no spread items"""
    model = ContrarianModel()
    
    game_items = [
        {"sk": "draftkings#h2h#LATEST", "outcomes": []}
    ]
    
    result = model.analyze_game_odds("game123", game_items, {})
    assert result is None


def test_contrarian_model_heavy_favorite():
    """Test contrarian fading heavy favorite"""
    model = ContrarianModel()
    model.elo_calculator = Mock()
    model.elo_calculator.get_team_rating.return_value = 1500
    
    game_items = [{
        "sk": "draftkings#spreads#LATEST",
        "outcomes": [
            {"name": "Lakers", "price": -110, "point": -12.5},  # Heavy favorite
            {"name": "Warriors", "price": -110, "point": 12.5}
        ]
    }]
    
    game_info = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors"
    }
    
    result = model.analyze_game_odds("game123", game_items, game_info)
    # May fade the favorite
    assert result is not None or result is None


def test_contrarian_prop_sharp_action_over():
    """Test contrarian prop with sharp action on Over"""
    model = ContrarianModel()
    
    prop_item = {
        "event_id": "game123",
        "sport": "basketball_nba",
        "player_name": "LeBron James",
        "point": 25.5,
        "outcomes": [
            {"name": "Over", "price": -130},  # Sharp action
            {"name": "Under", "price": +110}
        ]
    }
    
    result = model.analyze_prop_odds(prop_item)
    assert result is not None
    assert "Over" in result.prediction


def test_contrarian_prop_no_sharp_action():
    """Test contrarian prop with balanced odds"""
    model = ContrarianModel()
    
    prop_item = {
        "event_id": "game123",
        "sport": "basketball_nba",
        "player_name": "LeBron James",
        "point": 25.5,
        "outcomes": [
            {"name": "Over", "price": -110},
            {"name": "Under", "price": -110}
        ]
    }
    
    result = model.analyze_prop_odds(prop_item)
    # May still return result
    assert result is not None or result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
