"""
Additional comprehensive ML model tests - targeting uncovered paths
"""
import os
import pytest
from unittest.mock import patch, Mock

os.environ["DYNAMODB_TABLE"] = "test-table"

from ml.models import (
    ConsensusModel, ValueModel, MomentumModel, ContrarianModel,
    HotColdModel, AnalysisResult
)


@patch("ml.models.EloCalculator")
def test_consensus_elo_agrees_with_spread(mock_elo_class):
    """Test consensus when Elo agrees with spread"""
    mock_elo = Mock()
    mock_elo.get_team_rating.side_effect = [1600, 1400]  # Home much stronger
    mock_elo_class.return_value = mock_elo
    
    model = ConsensusModel()
    
    game_items = [
        {
            "sk": "draftkings#spreads#LATEST",
            "outcomes": [
                {"name": "Lakers", "price": -110, "point": -8.5},  # Home favored
                {"name": "Warriors", "price": -110, "point": 8.5}
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
    assert "Elo ratings confirm" in result.reasoning
    assert result.confidence >= 0.65  # Should boost confidence


@patch("ml.models.EloCalculator")
def test_consensus_elo_disagrees_with_spread(mock_elo_class):
    """Test consensus when Elo disagrees with spread"""
    mock_elo = Mock()
    mock_elo.get_team_rating.side_effect = [1400, 1600]  # Away stronger
    mock_elo_class.return_value = mock_elo
    
    model = ConsensusModel()
    
    game_items = [
        {
            "sk": "draftkings#spreads#LATEST",
            "outcomes": [
                {"name": "Lakers", "price": -110, "point": -5.5},  # Home favored but Elo says away
                {"name": "Warriors", "price": -110, "point": 5.5}
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
    assert "caution" in result.reasoning
    assert result.confidence <= 0.70  # Should reduce confidence


@patch("ml.models.EloCalculator")
def test_consensus_elo_error_handling(mock_elo_class):
    """Test consensus handles Elo errors gracefully"""
    mock_elo = Mock()
    mock_elo.get_team_rating.side_effect = Exception("Elo error")
    mock_elo_class.return_value = mock_elo
    
    model = ConsensusModel()
    
    game_items = [
        {
            "sk": "draftkings#spreads#LATEST",
            "outcomes": [
                {"name": "Lakers", "price": -110, "point": -5.5},
                {"name": "Warriors", "price": -110, "point": 5.5}
            ]
        }
    ]
    
    game_info = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors"
    }
    
    result = model.analyze_game_odds("game123", game_items, game_info)
    
    # Should still return result without Elo
    assert result is not None
    assert "Elo" not in result.reasoning


def test_consensus_prop_over_favored():
    """Test consensus prop when Over is favored"""
    model = ConsensusModel()
    
    prop_item = {
        "pk": "PROP#basketball_nba#game123",
        "sport": "basketball_nba",
        "player_name": "LeBron James",
        "point": 25.5,
        "outcomes": [
            {"name": "Over", "price": -130},  # Over favored
            {"name": "Under", "price": 110}
        ]
    }
    
    result = model.analyze_prop_odds(prop_item)
    
    assert result is not None
    assert "Over" in result.prediction


def test_consensus_prop_under_favored():
    """Test consensus prop when Under is favored"""
    model = ConsensusModel()
    
    prop_item = {
        "pk": "PROP#basketball_nba#game123",
        "sport": "basketball_nba",
        "player_name": "LeBron James",
        "point": 25.5,
        "outcomes": [
            {"name": "Over", "price": 110},
            {"name": "Under", "price": -130}  # Under favored
        ]
    }
    
    result = model.analyze_prop_odds(prop_item)
    
    assert result is not None
    assert "Under" in result.prediction


def test_value_model_high_vig():
    """Test value model rejects high vig"""
    model = ValueModel()
    
    game_items = [
        {
            "sk": "draftkings#h2h#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [
                {"name": "Lakers", "price": -120},  # High vig
                {"name": "Warriors", "price": -120}
            ]
        }
    ]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    
    # Should return None for high vig
    assert result is None


def test_value_model_prop_high_vig():
    """Test value model prop rejects high vig"""
    model = ValueModel()
    
    prop_item = {
        "pk": "PROP#basketball_nba#game123",
        "sport": "basketball_nba",
        "player_name": "LeBron James",
        "point": 25.5,
        "outcomes": [
            {"name": "Over", "price": -120},  # High vig
            {"name": "Under", "price": -120}
        ]
    }
    
    result = model.analyze_prop_odds(prop_item)
    
    assert result is None


def test_momentum_model_no_movement():
    """Test momentum model with no line movement"""
    model = MomentumModel()
    
    game_items = [
        {
            "sk": "draftkings#h2h#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [
                {"name": "Lakers", "price": -110},  # No movement
                {"name": "Warriors", "price": -110}
            ]
        }
    ]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    
    # Should return None without movement
    assert result is None


def test_contrarian_model_no_heavy_favorite():
    """Test contrarian with no heavy favorite"""
    model = ContrarianModel()
    
    game_items = [
        {
            "sk": "draftkings#h2h#LATEST",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "outcomes": [
                {"name": "Lakers", "price": -110},  # Even odds
                {"name": "Warriors", "price": -110}
            ]
        }
    ]
    
    result = model.analyze_game_odds("game123", game_items, game_items[0])
    
    # Should return None without heavy favorite
    assert result is None


def test_analysis_result_to_dynamodb_with_bookmaker():
    """Test AnalysisResult to_dynamodb_item with bookmaker"""
    result = AnalysisResult(
        game_id="game123",
        sport="basketball_nba",
        model="consensus",
        prediction="Lakers -5.5",
        confidence=0.75,
        reasoning="Test",
        analysis_type="game",
        bookmaker="draftkings",
        home_team="Lakers",
        away_team="Warriors"
    )
    
    item = result.to_dynamodb_item()
    
    assert "draftkings" in item["pk"]
    assert item["bookmaker"] == "draftkings"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

