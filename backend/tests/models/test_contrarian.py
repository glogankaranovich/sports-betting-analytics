"""Tests for Contrarian model"""

import pytest
from unittest.mock import Mock, patch

from ml.models.contrarian import ContrarianModel
from ml.types import AnalysisResult


class TestContrarianModel:
    @pytest.fixture
    def model(self):
        with patch('elo_calculator.EloCalculator'):
            model = ContrarianModel()
            model.elo_calculator = Mock()
            return model

    def test_analyze_game_strong_line_movement(self, model):
        model.elo_calculator.get_team_rating.side_effect = [1500, 1450]

        result = model.analyze_game_odds(
            "game123",
            [
                {"sk": "ODDS#spreads#draftkings", "updated_at": "2024-01-15T10:00:00Z",
                 "outcomes": [{"point": -3.0, "price": -110}, {"point": 3.0, "price": -110}]},
                {"sk": "ODDS#spreads#draftkings", "updated_at": "2024-01-15T18:00:00Z",
                 "outcomes": [{"point": -1.5, "price": -110}, {"point": 1.5, "price": -110}]}
            ],
            {
                "sport": "basketball_nba",
                "home_team": "Boston Celtics",
                "away_team": "Los Angeles Lakers",
                "commence_time": "2024-01-15T19:00:00Z"
            }
        )

        # Line moved from -3 to -1.5 (movement = +1.5), predicts away team
        assert result.prediction == "Los Angeles Lakers"
        assert result.confidence >= 0.75
        assert "Big money" in result.reasoning

    def test_analyze_game_odds_imbalance(self, model):
        result = model.analyze_game_odds(
            "game123",
            [
                {"sk": "ODDS#spreads#draftkings", "updated_at": "2024-01-15T18:00:00Z",
                 "outcomes": [{"point": -3.0, "price": -120}, {"point": 3.0, "price": -100}]}
            ],
            {
                "sport": "basketball_nba",
                "home_team": "Boston Celtics",
                "away_team": "Los Angeles Lakers",
                "commence_time": "2024-01-15T19:00:00Z"
            }
        )

        assert result.prediction in ["Boston Celtics", "Los Angeles Lakers"]
        assert "odds" in result.reasoning.lower()

    def test_analyze_game_fade_favorite(self, model):
        result = model.analyze_game_odds(
            "game123",
            [
                {"sk": "ODDS#spreads#draftkings", "updated_at": "2024-01-15T18:00:00Z",
                 "outcomes": [{"point": -7.0, "price": -110}, {"point": 7.0, "price": -110}]}
            ],
            {
                "sport": "basketball_nba",
                "home_team": "Boston Celtics",
                "away_team": "Los Angeles Lakers",
                "commence_time": "2024-01-15T19:00:00Z"
            }
        )

        assert result.prediction == "Los Angeles Lakers"
        assert "favorite" in result.reasoning.lower()

    def test_analyze_prop_odds_imbalance_over(self, model):
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
                {"name": "Over", "price": -130},
                {"name": "Under", "price": -100}
            ]
        })

        assert result.prediction == "Over 28.5"
        assert "Big money on Over" in result.reasoning

    def test_analyze_prop_default_under(self, model):
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
                {"name": "Over", "price": -110},
                {"name": "Under", "price": -110}
            ]
        })

        assert result.prediction == "Under 28.5"
        assert "crowd" in result.reasoning.lower()
