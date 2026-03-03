"""Unit tests for Momentum model"""

import pytest
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, '/Users/glkaranovich/workplace/sports-betting-analytics/backend')

from ml.models.momentum import MomentumModel
from ml.types import AnalysisResult


class TestMomentumModel:
    
    @pytest.fixture
    def model(self):
        """Create a Momentum model instance with mocked dependencies"""
        with patch('elo_calculator.EloCalculator'), \
             patch('travel_fatigue_calculator.TravelFatigueCalculator'), \
             patch('boto3.resource'):
            model = MomentumModel()
            model.elo_calculator = Mock()
            model.fatigue_calculator = Mock()
            return model

    def test_analyze_game_odds_big_movement_toward_home(self, model):
        """Test big line movement toward home team"""
        model.fatigue_calculator.calculate_fatigue_score.return_value = {
            'fatigue_score': 20,
            'days_rest': 2
        }
        model.elo_calculator.get_team_rating.side_effect = [1600, 1550]
        
        odds_items = [
            {
                "sk": "spreads#2026-03-01T10:00:00Z",
                "updated_at": "2026-03-01T10:00:00Z",
                "outcomes": [{"point": -5.5}, {"point": 5.5}]
            },
            {
                "sk": "spreads#2026-03-02T10:00:00Z",
                "updated_at": "2026-03-02T10:00:00Z",
                "outcomes": [{"point": -7.0}, {"point": 7.0}]
            }
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", odds_items, game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Boston Celtics"
        assert result.confidence >= 0.8
        assert "Big line shift" in result.reasoning

    def test_analyze_game_odds_movement_toward_away(self, model):
        """Test line movement toward away team"""
        model.fatigue_calculator.calculate_fatigue_score.return_value = {
            'fatigue_score': 20,
            'days_rest': 2
        }
        model.elo_calculator.get_team_rating.side_effect = [1550, 1600]
        
        odds_items = [
            {
                "sk": "spreads#2026-03-01T10:00:00Z",
                "updated_at": "2026-03-01T10:00:00Z",
                "outcomes": [{"point": -3.0}, {"point": 3.0}]
            },
            {
                "sk": "spreads#2026-03-02T10:00:00Z",
                "updated_at": "2026-03-02T10:00:00Z",
                "outcomes": [{"point": -2.0}, {"point": 2.0}]
            }
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", odds_items, game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Miami Heat"

    def test_analyze_game_odds_with_fatigue(self, model):
        """Test fatigue adjustment boosts confidence"""
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {'fatigue_score': 20, 'days_rest': 2},
            {'fatigue_score': 60, 'days_rest': 0}
        ]
        model.elo_calculator.get_team_rating.side_effect = [1600, 1550]
        
        odds_items = [
            {
                "sk": "spreads#2026-03-01T10:00:00Z",
                "updated_at": "2026-03-01T10:00:00Z",
                "outcomes": [{"point": -5.0}, {"point": 5.0}]
            },
            {
                "sk": "spreads#2026-03-02T10:00:00Z",
                "updated_at": "2026-03-02T10:00:00Z",
                "outcomes": [{"point": -6.0}, {"point": 6.0}]
            }
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", odds_items, game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Boston Celtics"
        assert "fatigued" in result.reasoning

    def test_analyze_game_odds_insufficient_data(self, model):
        """Test returns None with insufficient data"""
        odds_items = [
            {
                "sk": "spreads#2026-03-01T10:00:00Z",
                "updated_at": "2026-03-01T10:00:00Z",
                "outcomes": [{"point": -5.0}, {"point": 5.0}]
            }
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", odds_items, game_info)
        
        assert result is None

    def test_analyze_prop_odds_sharp_over(self, model):
        """Test prop with sharp action on over"""
        prop_item = {
            "event_id": "test_game",
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z",
            "player_name": "Jayson Tatum",
            "market_key": "player_points",
            "point": 28.5,
            "outcomes": [
                {"name": "Over", "price": -130},
                {"name": "Under", "price": 110}
            ]
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert isinstance(result, AnalysisResult)
        assert "Over" in result.prediction
        assert result.confidence == 0.75

    def test_analyze_prop_odds_sharp_under(self, model):
        """Test prop with sharp action on under"""
        prop_item = {
            "event_id": "test_game",
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z",
            "player_name": "Jayson Tatum",
            "market_key": "player_points",
            "point": 28.5,
            "outcomes": [
                {"name": "Over", "price": 110},
                {"name": "Under", "price": -130}
            ]
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert isinstance(result, AnalysisResult)
        assert "Under" in result.prediction
        assert result.confidence == 0.75

    def test_analyze_prop_odds_no_clear_signal(self, model):
        """Test prop returns None with no clear momentum"""
        prop_item = {
            "event_id": "test_game",
            "sport": "basketball_nba",
            "player_name": "Jayson Tatum",
            "point": 28.5,
            "outcomes": [
                {"name": "Over", "price": -105},
                {"name": "Under", "price": -105}
            ]
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert result is None
