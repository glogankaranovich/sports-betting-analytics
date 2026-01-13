"""
Test ML models functionality
"""

import pytest
from ml.models import (
    ConsensusModel,
    ValueModel,
    MomentumModel,
    AnalysisResult,
)


def test_american_to_decimal():
    model = ConsensusModel()

    # Positive odds
    assert model.american_to_decimal(100) == 2.0
    assert model.american_to_decimal(200) == 3.0

    # Negative odds
    assert model.american_to_decimal(-100) == 2.0
    assert model.american_to_decimal(-200) == 1.5


# Remove old test that uses non-existent method
# def test_decimal_to_probability():


# Test Consensus Model Prop Analysis
def test_consensus_prop_analysis():
    model = ConsensusModel()

    prop_item = {
        "pk": "PROP#basketball_nba#game123#fanduel",
        "sk": "player_points#LATEST",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "commence_time": "2026-01-13T20:00:00Z",
        "description": "LeBron James - Points",
        "point": 25.5,
        "outcomes": [{"name": "Over", "price": -110}, {"name": "Under", "price": -110}],
    }

    result = model.analyze_prop_odds(prop_item)

    assert isinstance(result, AnalysisResult)
    assert result.model == "consensus"
    assert result.analysis_type == "prop"
    assert result.player_name == "LeBron James"
    assert "Over" in result.prediction or "Under" in result.prediction
    assert result.confidence > 0


# Test Value Model Prop Analysis
def test_value_prop_analysis():
    model = ValueModel()

    # Low vig scenario
    prop_item = {
        "pk": "PROP#basketball_nba#game123#fanduel",
        "sport": "basketball_nba",
        "description": "Stephen Curry - 3-Pointers Made",
        "point": 4.5,
        "outcomes": [{"name": "Over", "price": -105}, {"name": "Under", "price": -105}],
    }

    result = model.analyze_prop_odds(prop_item)

    assert isinstance(result, AnalysisResult)
    assert result.model == "value"
    assert result.confidence >= 0.6


# Test Momentum Model Prop Analysis
def test_momentum_prop_analysis():
    model = MomentumModel()

    prop_item = {
        "pk": "PROP#basketball_nba#game123#fanduel",
        "sport": "basketball_nba",
        "description": "Giannis Antetokounmpo - Rebounds",
        "point": 11.5,
        "outcomes": [
            {"name": "Over", "price": -120},  # Worse odds = money on Under
            {"name": "Under", "price": -100},
        ],
    }

    result = model.analyze_prop_odds(prop_item)

    assert isinstance(result, AnalysisResult)
    assert result.model == "momentum"
    assert "Momentum" in result.reasoning


# Test AnalysisResult DynamoDB conversion
def test_analysis_result_to_dynamodb():
    result = AnalysisResult(
        game_id="test123",
        model="consensus",
        analysis_type="game",
        sport="basketball_nba",
        prediction="Lakers +2.5",
        confidence=0.75,
        reasoning="Test reasoning",
        home_team="Lakers",
        away_team="Warriors",
        commence_time="2026-01-13T20:00:00Z",
        bookmaker="fanduel",
    )

    item = result.to_dynamodb_item()

    assert item["pk"] == "ANALYSIS#basketball_nba#test123#fanduel"
    assert item["sk"] == "consensus#game#LATEST"
    assert item["analysis_time_pk"] == "ANALYSIS#basketball_nba#fanduel#consensus"
    assert item["model"] == "consensus"
    assert item["analysis_type"] == "game"
    assert item["latest"] is True


# Test old methods that are no longer used - remove these tests
# def test_decimal_to_probability():
# def test_analyze_game():
# def test_combat_sports_analysis():
# def test_boxing_analysis():
# def test_consensus_analysis_multiple_bookmakers():


# Test game odds analysis using new method
def test_consensus_game_odds_analysis():
    model = ConsensusModel()

    odds_items = [
        {
            "sk": "spreads#LATEST",
            "outcomes": [{"point": -2.5, "price": -110}, {"point": 2.5, "price": -110}],
        }
    ]

    game_info = {
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "commence_time": "2026-01-13T20:00:00Z",
        "bookmaker": "fanduel",
    }

    result = model.analyze_game_odds("game123", odds_items, game_info)

    assert isinstance(result, AnalysisResult)
    assert result.model == "consensus"
    assert result.analysis_type == "game"
    assert "Lakers" in result.prediction


if __name__ == "__main__":
    pytest.main([__file__])
