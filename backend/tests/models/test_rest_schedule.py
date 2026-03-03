"""Tests for RestSchedule model"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from ml.models.rest_schedule import RestScheduleModel
from ml.types import AnalysisResult


class TestRestScheduleModel:
    @pytest.fixture
    def model(self):
        with patch('travel_fatigue_calculator.TravelFatigueCalculator'), \
             patch('boto3.resource'):
            model = RestScheduleModel()
            model.table = Mock()
            return model

    def test_analyze_game_with_fatigue_calculator(self, model):
        model.fatigue_calculator.calculate_fatigue_score = Mock(side_effect=[
            {'fatigue_score': 30, 'back_to_back': False, 'total_miles': 500, 'days_rest': 2, 'impact': 'low'},
            {'fatigue_score': 60, 'back_to_back': True, 'total_miles': 1500, 'days_rest': 0, 'impact': 'high'}
        ])

        result = model.analyze_game_odds(
            "game123",
            [],
            {
                "sport": "NBA",
                "home_team": "Boston Celtics",
                "away_team": "Los Angeles Lakers",
                "commence_time": "2024-01-15T19:00:00Z"
            }
        )

        assert result.prediction == "Boston Celtics"
        assert result.confidence > 0.5
        assert "back-to-back" in result.reasoning
        assert "1500 miles" in result.reasoning

    def test_analyze_game_fallback_to_rest_score(self, model):
        model.fatigue_calculator.calculate_fatigue_score = Mock(side_effect=Exception("API error"))
        model.table.query.return_value = {
            "Items": [{"rest_days": 3}]
        }

        result = model.analyze_game_odds(
            "game123",
            [],
            {
                "sport": "NBA",
                "home_team": "Boston Celtics",
                "away_team": "Los Angeles Lakers",
                "commence_time": "2024-01-15T19:00:00Z"
            }
        )

        assert result.prediction in ["Boston Celtics", "Los Angeles Lakers"]
        assert 0.3 <= result.confidence <= 0.9
        assert "Rest advantage" in result.reasoning

    def test_analyze_prop_well_rested(self, model):
        model.table.query.side_effect = [
            {"Items": [{"team": "Boston Celtics"}]},
            {"Items": [{"rest_days": 3}]}
        ]

        result = model.analyze_prop_odds({
            "sport": "NBA",
            "player_name": "Jayson Tatum",
            "commence_time": "2024-01-15T19:00:00Z",
            "point": 28.5,
            "event_id": "evt123",
            "home_team": "Boston Celtics",
            "away_team": "Los Angeles Lakers",
            "market_key": "player_points"
        })

        assert result.prediction == "Over 28.5"
        assert "well-rested" in result.reasoning

    def test_analyze_prop_fatigued(self, model):
        model.table.query.side_effect = [
            {"Items": [{"team": "Los Angeles Lakers"}]},
            {"Items": [{"rest_days": 0}]}
        ]

        result = model.analyze_prop_odds({
            "sport": "NBA",
            "player_name": "LeBron James",
            "commence_time": "2024-01-15T19:00:00Z",
            "point": 25.5,
            "event_id": "evt123",
            "home_team": "Boston Celtics",
            "away_team": "Los Angeles Lakers",
            "market_key": "player_points"
        })

        assert result.prediction == "Under 25.5"
        assert "fatigued" in result.reasoning

    def test_get_rest_score_well_rested(self, model):
        model.table.query.return_value = {
            "Items": [{"rest_days": 3}]
        }

        score = model._get_rest_score("NBA", "boston_celtics", "2024-01-15T19:00:00Z", is_home=True)
        assert score == 4.0

    def test_get_rest_score_back_to_back(self, model):
        model.table.query.return_value = {
            "Items": [{"rest_days": 0}]
        }

        score = model._get_rest_score("NBA", "boston_celtics", "2024-01-15T19:00:00Z", is_home=False)
        assert score == -3.5
