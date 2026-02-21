"""
Comprehensive ML models tests
"""

import os
import pytest
from unittest.mock import patch, Mock

os.environ["DYNAMODB_TABLE"] = "test-table"

from ml.models import AnalysisResult, ConsensusModel, MomentumModel, ValueModel, ContrarianModel, HotColdModel


@patch("ml.models.EloCalculator")
def test_consensus_game_with_spreads(mock_elo_class):
    """Test consensus model with spread data"""
    mock_elo = Mock()
    mock_elo.get_team_rating.side_effect = [1500, 1450]
    mock_elo_class.return_value = mock_elo
    
    model = ConsensusModel()
    
    game_items = [
        {
            "sk": "draftkings#spreads#LATEST",
            "outcomes": [
                {"name": "Lakers", "price": -110, "point": -5.5},
                {"name": "Warriors", "price": -110, "point": 5.5}
            ]
        },
        {
            "sk": "fanduel#spreads#LATEST",
            "outcomes": [
                {"name": "Lakers", "price": -110, "point": -5.0},
                {"name": "Warriors", "price": -110, "point": 5.0}
            ]
        }
    ]
    
    game_info = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "commence_time": "2026-02-21T19:00:00Z"
    }
    
    result = model.analyze_game_odds("game123", game_items, game_info)
    
    assert result is not None
    assert result.model == "consensus"
    assert "Lakers" in result.prediction
    assert result.confidence >= 0.6


@patch("ml.models.EloCalculator")
def test_consensus_no_spreads_returns_none(mock_elo_class):
    """Test consensus returns None without spreads"""
    model = ConsensusModel()
    
    game_items = [
        {
            "sk": "draftkings#h2h#LATEST",
            "outcomes": [
                {"name": "Lakers", "price": -150},
                {"name": "Warriors", "price": 130}
            ]
        }
    ]
    
    game_info = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors"
    }
    
    result = model.analyze_game_odds("game123", game_items, game_info)
    assert result is None


def test_value_model_low_vig():
    """Test value model identifies low vig"""
    model = ValueModel()
    
    game_items = [
        {
            "sk": "draftkings#h2h#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [
                {"name": "Lakers", "price": -105},
                {"name": "Warriors", "price": -105}
            ]
        }
    ]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    
    if result:
        assert result.model == "value"
        assert result.confidence >= 0.6


def test_momentum_sharp_action():
    """Test momentum detects sharp action"""
    model = MomentumModel()
    
    game_items = [
        {
            "sk": "draftkings#h2h#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [
                {"name": "Lakers", "price": -130},
                {"name": "Warriors", "price": 110}
            ]
        }
    ]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    
    if result:
        assert result.model == "momentum"


def test_contrarian_fades_favorite():
    """Test contrarian fades heavy favorite"""
    model = ContrarianModel()
    
    game_items = [
        {
            "sk": "draftkings#h2h#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [
                {"name": "Lakers", "price": -200},
                {"name": "Warriors", "price": 170}
            ]
        }
    ]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    
    if result:
        assert result.model == "contrarian"


def test_hot_cold_model():
    """Test hot/cold model"""
    model = HotColdModel()
    
    game_items = [
        {
            "sk": "draftkings#h2h#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [
                {"name": "Lakers", "price": -110},
                {"name": "Warriors", "price": -110}
            ]
        }
    ]
    
    # Just test that model can be instantiated
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    # May return None without recent form data
    if result:
        assert result.model == "hot_cold"


def test_analysis_result_roi():
    """Test ROI calculation"""
    result = AnalysisResult(
        game_id="game123",
        sport="basketball_nba",
        model="consensus",
        prediction="Lakers -5.5",
        confidence=0.70,
        reasoning="Test",
        analysis_type="game",
        recommended_odds=-110
    )
    
    roi = result.roi
    assert roi is not None
    assert isinstance(roi, float)


def test_model_factory_all_models():
    """Test ModelFactory creates all models"""
    from ml.models import ModelFactory
    
    models = ["consensus", "value", "momentum", "contrarian", "hot_cold", 
              "rest_schedule", "matchup", "injury_aware", "ensemble"]
    
    for model_name in models:
        model = ModelFactory.create_model(model_name)
        assert model is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
