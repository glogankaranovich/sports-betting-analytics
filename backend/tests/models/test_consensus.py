"""Tests for Consensus model"""

import pytest
from unittest.mock import Mock, patch

from ml.models.consensus import ConsensusModel
from ml.types import AnalysisResult


class TestConsensusModel:
    @pytest.fixture
    def model(self):
        with patch('elo_calculator.EloCalculator'), \
             patch('boto3.resource'):
            model = ConsensusModel()
            model.table = Mock()
            model.elo_calculator = Mock()
            return model

    def test_analyze_game_consensus_spread(self, model):
        model.elo_calculator.get_team_rating.side_effect = [1550, 1450]
        model.table.query.return_value = {"Items": []}

        result = model.analyze_game_odds(
            "game123",
            [
                {"sk": "ODDS#spreads#draftkings", "outcomes": [{"point": -3.5, "price": -110}, {"point": 3.5, "price": -110}]},
                {"sk": "ODDS#spreads#fanduel", "outcomes": [{"point": -3.0, "price": -110}, {"point": 3.0, "price": -110}]},
                {"sk": "ODDS#spreads#betmgm", "outcomes": [{"point": -3.5, "price": -110}, {"point": 3.5, "price": -110}]}
            ],
            {
                "sport": "basketball_nba",
                "home_team": "Boston Celtics",
                "away_team": "Los Angeles Lakers",
                "commence_time": "2024-01-15T19:00:00Z"
            }
        )

        assert result.prediction == "Boston Celtics"  # avg_spread = -3.33 (negative = home favored)
        assert result.confidence >= 0.6
        assert "3 sportsbooks" in result.reasoning

    def test_analyze_game_no_spreads(self, model):
        result = model.analyze_game_odds(
            "game123",
            [],
            {
                "sport": "basketball_nba",
                "home_team": "Boston Celtics",
                "away_team": "Los Angeles Lakers",
                "commence_time": "2024-01-15T19:00:00Z"
            }
        )

        assert result is None

    def test_analyze_prop_over_favored(self, model):
        result = model.analyze_prop_odds({
            "sport": "basketball_nba",
            "player_name": "Jayson Tatum",
            "point": 28.5,
            "event_id": "evt123",
            "home_team": "Boston Celtics",
            "away_team": "Los Angeles Lakers",
            "commence_time": "2024-01-15T19:00:00Z",
            "market_key": "player_points",
            "outcomes": [
                {"name": "Over", "price": -120},
                {"name": "Under", "price": +100}
            ],
            "bookmakers": ["draftkings", "fanduel"]
        })

        assert result.prediction == "Over 28.5"
        assert result.confidence > 0.5

    def test_analyze_prop_under_favored(self, model):
        result = model.analyze_prop_odds({
            "sport": "basketball_nba",
            "player_name": "Jayson Tatum",
            "point": 28.5,
            "event_id": "evt123",
            "home_team": "Boston Celtics",
            "away_team": "Los Angeles Lakers",
            "commence_time": "2024-01-15T19:00:00Z",
            "market_key": "player_points",
            "outcomes": [
                {"name": "Over", "price": +100},
                {"name": "Under", "price": -120}
            ],
            "bookmakers": ["draftkings"]
        })

        assert result.prediction == "Under 28.5"
        assert result.confidence > 0.5
