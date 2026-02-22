"""More momentum model tests"""

import os
from unittest.mock import Mock

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from ml.models import MomentumModel


def test_momentum_model_insufficient_data():
    """Test momentum with insufficient data points"""
    model = MomentumModel()
    
    game_items = [{
        "sk": "draftkings#spreads#LATEST",
        "outcomes": [{"name": "Lakers", "point": -5.5}]
    }]
    
    result = model.analyze_game_odds("game123", game_items, {})
    assert result is None


def test_momentum_model_missing_outcomes():
    """Test momentum with missing outcomes"""
    model = MomentumModel()
    
    game_items = [
        {"sk": "draftkings#spreads#old", "outcomes": []},
        {"sk": "draftkings#spreads#LATEST", "outcomes": []}
    ]
    
    result = model.analyze_game_odds("game123", game_items, {})
    assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
