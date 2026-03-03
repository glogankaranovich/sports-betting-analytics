"""Unit tests for Value model"""

import pytest
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, '/Users/glkaranovich/workplace/sports-betting-analytics/backend')

from ml.models.value import ValueModel
from ml.types import AnalysisResult


class TestValueModel:
    
    @pytest.fixture
    def model(self):
        """Create a Value model instance with mocked dependencies"""
        with patch('elo_calculator.EloCalculator'), \
             patch('boto3.resource'):
            model = ValueModel()
            model.elo_calculator = Mock()
            return model

    def test_analyze_game_odds_value_on_home(self, model):
        """Test value found on home team"""
        model.elo_calculator.get_team_rating.side_effect = [1600, 1550]
        
        odds_items = [
            {
                "sk": "spreads#2026-03-01T10:00:00Z",
                "outcomes": [{"point": -7.0, "price": -110}, {"point": 7.0, "price": -110}]
            },
            {
                "sk": "spreads#2026-03-01T11:00:00Z",
                "outcomes": [{"point": -5.5, "price": -110}, {"point": 5.5, "price": -110}]
            }
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z",
            "bookmaker": "draftkings"
        }
        
        result = model.analyze_game_odds("test_game", odds_items, game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Boston Celtics"
        assert "Value on Boston Celtics" in result.reasoning

    def test_analyze_game_odds_value_on_away(self, model):
        """Test value found on away team"""
        model.elo_calculator.get_team_rating.side_effect = [1550, 1600]
        
        odds_items = [
            {
                "sk": "spreads#2026-03-01T10:00:00Z",
                "outcomes": [{"point": -5.0, "price": -110}, {"point": 5.0, "price": -110}]
            },
            {
                "sk": "spreads#2026-03-01T11:00:00Z",
                "outcomes": [{"point": -6.5, "price": -110}, {"point": 6.5, "price": -110}]
            }
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z",
            "bookmaker": "fanduel"
        }
        
        result = model.analyze_game_odds("test_game", odds_items, game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Miami Heat"

    def test_analyze_game_odds_insufficient_value(self, model):
        """Test returns None when value difference too small"""
        odds_items = [
            {
                "sk": "spreads#2026-03-01T10:00:00Z",
                "outcomes": [{"point": -5.5, "price": -110}, {"point": 5.5, "price": -110}]
            },
            {
                "sk": "spreads#2026-03-01T11:00:00Z",
                "outcomes": [{"point": -5.3, "price": -110}, {"point": 5.3, "price": -110}]
            }
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "bookmaker": "draftkings"
        }
        
        result = model.analyze_game_odds("test_game", odds_items, game_info)
        
        assert result is None

    def test_analyze_prop_odds_low_vig(self, model):
        """Test prop with low vig (good value)"""
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
                {"name": "Over", "price": -105},
                {"name": "Under", "price": -105}
            ]
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert isinstance(result, AnalysisResult)
        assert result.confidence == 0.75
        assert "Great odds" in result.reasoning

    def test_analyze_prop_odds_high_vig_no_edge(self, model):
        """Test prop with high vig and no clear edge returns None"""
        prop_item = {
            "event_id": "test_game",
            "sport": "basketball_nba",
            "player_name": "Jayson Tatum",
            "point": 28.5,
            "outcomes": [
                {"name": "Over", "price": -115},
                {"name": "Under", "price": -115}
            ]
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert result is None
