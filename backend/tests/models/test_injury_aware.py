"""Tests for InjuryAware model"""

import pytest
from unittest.mock import Mock, patch

from ml.models.injury_aware import InjuryAwareModel
from ml.types import AnalysisResult


class TestInjuryAwareModel:
    @pytest.fixture
    def model(self):
        with patch('boto3.resource'):
            model = InjuryAwareModel()
            model.table = Mock()
            return model

    def test_analyze_game_away_team_injured(self, model):
        model.table.query.side_effect = [
            {"Items": []},
            {"Items": [{"injuries": [{"status": "Out", "usage_rate": 30, "per": 20, "win_shares": 5, "avg_minutes": 35}]}]}
        ]

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
        assert result.confidence >= 0.65
        assert "injuries" in result.reasoning.lower()

    def test_analyze_game_both_healthy(self, model):
        model.table.query.return_value = {"Items": []}

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

        assert result.prediction in ["Boston Celtics", "Los Angeles Lakers"]
        assert "healthy" in result.reasoning.lower()

    def test_analyze_prop_player_out(self, model):
        model.table.query.return_value = {
            "Items": [{"status": "Out", "injury_type": "knee"}]
        }

        result = model.analyze_prop_odds({
            "sport": "basketball_nba",
            "player_name": "LeBron James",
            "point": 25.5,
            "event_id": "evt123",
            "home_team": "Los Angeles Lakers",
            "away_team": "Boston Celtics",
            "commence_time": "2024-01-15T19:00:00Z",
            "market_key": "player_points"
        })

        assert result.prediction == "Under 25.5"
        assert result.confidence == 0.9
        assert "Out" in result.reasoning

    def test_analyze_prop_player_questionable(self, model):
        model.table.query.return_value = {
            "Items": [{"status": "Questionable", "injury_type": "ankle"}]
        }

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

        assert result.prediction == "Under 28.5"
        assert result.confidence == 0.65
        assert "Questionable" in result.reasoning

    def test_analyze_prop_player_healthy(self, model):
        model.table.query.return_value = {"Items": []}

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
        assert "healthy" in result.reasoning.lower()

    def test_calculate_injury_impact(self, model):
        injuries = [
            {"status": "Out", "usage_rate": 30, "per": 25, "win_shares": 8, "avg_minutes": 36}
        ]
        
        impact = model._calculate_injury_impact(injuries)
        assert 0.5 < impact <= 1.0

    def test_calculate_injury_impact_empty(self, model):
        assert model._calculate_injury_impact([]) == 0.0
