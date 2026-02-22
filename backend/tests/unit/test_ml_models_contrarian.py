"""Contrarian model tests"""

import os
from unittest.mock import Mock

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from ml.models import ContrarianModel


def test_contrarian_no_spreads():
    """Test contrarian with no spreads"""
    model = ContrarianModel()
    
    result = model.analyze_game_odds("game123", [], {})
    assert result is None


def test_contrarian_sharp_action_over():
    """Test contrarian prop with sharp action"""
    model = ContrarianModel()
    
    prop_item = {
        "event_id": "game123",
        "sport": "basketball_nba",
        "player_name": "LeBron James",
        "point": 25.5,
        "outcomes": [
            {"name": "Over", "price": -130},
            {"name": "Under", "price": +110}
        ]
    }
    
    result = model.analyze_prop_odds(prop_item)
    assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
