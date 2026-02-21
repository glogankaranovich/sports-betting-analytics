"""More ML model tests targeting uncovered paths"""

import os
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from ml.models import ConsensusModel, ValueModel, MomentumModel, AnalysisResult


def test_consensus_prop_missing_outcomes():
    """Test consensus prop with missing outcomes"""
    model = ConsensusModel()
    
    prop_item = {
        "event_id": "game123",
        "sport": "basketball_nba",
        "player_name": "LeBron James",
        "outcomes": []
    }
    
    result = model.analyze_prop_odds(prop_item)
    assert result is None


def test_consensus_prop_missing_over():
    """Test consensus prop with missing Over outcome"""
    model = ConsensusModel()
    
    prop_item = {
        "event_id": "game123",
        "sport": "basketball_nba",
        "player_name": "LeBron James",
        "outcomes": [{"name": "Under", "price": -110}]
    }
    
    result = model.analyze_prop_odds(prop_item)
    assert result is None


def test_consensus_elo_error_handling():
    """Test consensus handles Elo calculator errors"""
    model = ConsensusModel()
    model.elo_calculator.get_team_rating = Mock(side_effect=Exception("Elo error"))
    
    game_items = [{
        "sk": "draftkings#spreads#LATEST",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "outcomes": [
            {"name": "Lakers", "price": -110, "point": -5.5},
            {"name": "Warriors", "price": -110, "point": 5.5}
        ]
    }]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    assert result is not None


def test_value_model_no_variance():
    """Test value model with no odds variance"""
    model = ValueModel()
    
    game_items = [
        {
            "sk": "draftkings#spreads#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [{"name": "Lakers", "price": -110, "point": -5.5}]
        },
        {
            "sk": "fanduel#spreads#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [{"name": "Lakers", "price": -110, "point": -5.5}]
        }
    ]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    assert result is None


def test_momentum_model_single_item():
    """Test momentum model with single item (no history)"""
    model = MomentumModel()
    
    game_items = [{
        "sk": "draftkings#spreads#LATEST",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "outcomes": [{"name": "Lakers", "price": -110, "point": -5.5}]
    }]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    assert result is None


def test_analysis_result_with_bookmaker():
    """Test AnalysisResult with bookmaker field"""
    result = AnalysisResult(
        game_id="game123",
        sport="basketball_nba",
        model="value",
        prediction="Lakers -5.5",
        confidence=0.75,
        reasoning="Value",
        analysis_type="game",
        bookmaker="draftkings"
    )
    
    item = result.to_dynamodb_item()
    assert item["bookmaker"] == "draftkings"


def test_analysis_result_prop_fields():
    """Test AnalysisResult with prop fields"""
    result = AnalysisResult(
        game_id="game123",
        sport="basketball_nba",
        model="consensus",
        prediction="Over 25.5",
        confidence=0.70,
        reasoning="Prop",
        analysis_type="prop",
        player_name="LeBron James",
        market_key="player_points"
    )
    
    item = result.to_dynamodb_item()
    assert item["player_name"] == "LeBron James"
    assert item["market_key"] == "player_points"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
