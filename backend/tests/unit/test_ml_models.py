"""
Test ML models functionality
"""

import pytest
from ml.models import ConsensusModel, GameAnalysis


def test_american_to_decimal():
    model = ConsensusModel()

    # Positive odds
    assert model.american_to_decimal(100) == 2.0
    assert model.american_to_decimal(200) == 3.0

    # Negative odds
    assert model.american_to_decimal(-100) == 2.0
    assert model.american_to_decimal(-200) == 1.5


def test_decimal_to_probability():
    model = ConsensusModel()

    assert model.decimal_to_probability(2.0) == 0.5
    assert model.decimal_to_probability(4.0) == 0.25


def test_analyze_game():
    model = ConsensusModel()

    game_data = {
        "game_id": "test_game",
        "sport": "americanfootball_nfl",
        "home_team": "Team A",
        "away_team": "Team B",
        "commence_time": "2026-01-03T20:00:00Z",
        "odds": {
            "test_bookmaker": {
                "h2h": {
                    "outcomes": [
                        {"name": "Team A", "price": -110},
                        {"name": "Team B", "price": 100},
                    ]
                }
            }
        },
    }

    prediction = model.analyze_game(game_data)

    assert isinstance(prediction, GameAnalysis)
    assert prediction.game_id == "test_game"
    assert prediction.home_win_probability > 0
    assert prediction.away_win_probability > 0
    assert prediction.confidence_score > 0


def test_combat_sports_analysis():
    """Test that combat sports can be analyzed"""
    model = ConsensusModel()

    # MMA fight data
    mma_data = {
        "game_id": "mma_fight_1",
        "sport": "mma_mixed_martial_arts",
        "home_team": "Fighter A",
        "away_team": "Fighter B",
        "commence_time": "2026-01-03T20:00:00Z",
        "odds": {
            "test_bookmaker": {
                "h2h": {
                    "outcomes": [
                        {"name": "Fighter A", "price": -150},
                        {"name": "Fighter B", "price": 120},
                    ]
                }
            }
        },
    }

    prediction = model.analyze_game(mma_data)

    assert isinstance(prediction, GameAnalysis)
    assert prediction.sport == "mma_mixed_martial_arts"
    assert prediction.home_win_probability > 0
    assert prediction.away_win_probability > 0


def test_boxing_analysis():
    """Test that boxing matches can be analyzed"""
    model = ConsensusModel()

    # Boxing match data
    boxing_data = {
        "game_id": "boxing_match_1",
        "sport": "boxing_boxing",
        "home_team": "Boxer A",
        "away_team": "Boxer B",
        "commence_time": "2026-01-03T20:00:00Z",
        "bookmakers": [
            {
                "bookmaker": "test_bookmaker",
                "market_key": "h2h",
                "outcomes": [
                    {"name": "Boxer A", "price": -200},
                    {"name": "Boxer B", "price": 170},
                ],
            }
        ],
    }

    prediction = model.analyze_game(boxing_data)

    assert isinstance(prediction, GameAnalysis)
    assert prediction.sport == "boxing_boxing"
    assert (
        prediction.home_win_probability > 0.5
    )  # Favorite should have higher probability


def test_consensus_analysis_multiple_bookmakers():
    """Test consensus analysis with multiple bookmakers"""
    model = ConsensusModel()

    # Game with multiple bookmaker odds
    game_data = {
        "game_id": "test_game",
        "sport": "americanfootball_nfl",
        "home_team": "Team A",
        "away_team": "Team B",
        "commence_time": "2026-01-03T20:00:00Z",
        "bookmakers": [
            {
                "key": "fanduel",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Team A", "price": -110},
                            {"name": "Team B", "price": -110},
                        ],
                    }
                ],
            },
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Team A", "price": -105},
                            {"name": "Team B", "price": -115},
                        ],
                    }
                ],
            },
        ],
    }

    # Should handle multiple bookmakers for consensus
    prediction = model.analyze_game(game_data)
    assert isinstance(prediction, GameAnalysis)
    assert prediction.confidence_score > 0


if __name__ == "__main__":
    pytest.main([__file__])
