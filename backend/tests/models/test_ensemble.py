"""Tests for Ensemble model"""

import pytest
from unittest.mock import Mock, patch

from ml.models.ensemble import EnsembleModel
from ml.types import AnalysisResult


class TestEnsembleModel:
    @pytest.fixture
    def model(self):
        model = EnsembleModel.__new__(EnsembleModel)
        model.weighting = Mock()
        model.models = {}
        return model

    def test_analyze_game_combines_predictions(self, model):
        # Mock model predictions
        mock_result1 = AnalysisResult(
            game_id="game123", model="value", analysis_type="game",
            sport="basketball_nba", prediction="Boston Celtics",
            confidence=0.7, reasoning="Value bet", recommended_odds=-110
        )
        mock_result2 = AnalysisResult(
            game_id="game123", model="momentum", analysis_type="game",
            sport="basketball_nba", prediction="Boston Celtics",
            confidence=0.65, reasoning="Line movement", recommended_odds=-110
        )

        model.models = {
            "value": Mock(analyze_game_odds=Mock(return_value=mock_result1)),
            "momentum": Mock(analyze_game_odds=Mock(return_value=mock_result2)),
            "contrarian": Mock(analyze_game_odds=Mock(return_value=None))
        }

        model.weighting.get_model_weights.return_value = {
            "value": 0.6,
            "momentum": 0.4
        }

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

        assert result.prediction == "Boston Celtics"
        assert abs(result.confidence - 0.68) < 0.01  # 0.7*0.6 + 0.65*0.4
        assert "Combined prediction from 2 models" in result.reasoning
        assert result.model == "ensemble"

    def test_analyze_game_no_predictions(self, model):
        model.models = {
            "value": Mock(analyze_game_odds=Mock(return_value=None)),
            "momentum": Mock(analyze_game_odds=Mock(return_value=None))
        }

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

    def test_analyze_prop_combines_predictions(self, model):
        mock_result = AnalysisResult(
            game_id="evt123", model="player_stats", analysis_type="prop",
            sport="basketball_nba", prediction="Over 28.5",
            confidence=0.75, reasoning="Hot streak", recommended_odds=-110,
            player_name="Jayson Tatum", market_key="player_points",
            home_team="Boston Celtics", away_team="Los Angeles Lakers"
        )

        model.models = {
            "player_stats": Mock(analyze_prop_odds=Mock(return_value=mock_result)),
            "hot_cold": Mock(analyze_prop_odds=Mock(return_value=None))
        }

        model.weighting.get_model_weights.return_value = {"player_stats": 1.0}

        result = model.analyze_prop_odds({
            "sport": "basketball_nba",
            "player_name": "Jayson Tatum",
            "point": 28.5,
            "event_id": "evt123",
            "home_team": "Boston Celtics",
            "away_team": "Los Angeles Lakers",
            "commence_time": "2024-01-15T19:00:00Z",
            "market_key": "player_points"
        })

        assert result.prediction == "Over 28.5"
        assert result.confidence == 0.75
        assert result.model == "ensemble"
