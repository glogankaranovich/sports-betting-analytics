"""Unit tests for HotCold model"""

import pytest
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, '/Users/glkaranovich/workplace/sports-betting-analytics/backend')

from ml.models.hot_cold import HotColdModel
from ml.types import AnalysisResult


class TestHotColdModel:
    
    @pytest.fixture
    def model(self):
        """Create a HotCold model instance with mocked dependencies"""
        mock_table = Mock()
        model = HotColdModel(dynamodb_table=mock_table)
        return model

    def test_analyze_game_odds_hot_home_team(self, model):
        """Test hot home team prediction"""
        model.table.query.side_effect = [
            {"Items": [{"winner": "Boston Celtics"}, {"winner": "Boston Celtics"}, {"winner": "Boston Celtics"}, 
                       {"winner": "Miami Heat"}, {"winner": "Boston Celtics"}]},
            {"Items": [{"winner": "Miami Heat"}, {"winner": "New York Knicks"}, {"winner": "New York Knicks"}, 
                       {"winner": "Miami Heat"}, {"winner": "New York Knicks"}]},
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", [], game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Boston Celtics"
        assert result.confidence >= 0.65
        assert "form" in result.reasoning.lower()

    def test_analyze_game_odds_hot_away_team(self, model):
        """Test hot away team prediction"""
        model.table.query.side_effect = [
            {"Items": [{"winner": "Miami Heat"}, {"winner": "Boston Celtics"}, {"winner": "Miami Heat"}]},
            {"Items": [{"winner": "Miami Heat"}, {"winner": "Miami Heat"}, {"winner": "Miami Heat"}, 
                       {"winner": "Miami Heat"}, {"winner": "Miami Heat"}]},
        ]
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", [], game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Miami Heat"

    def test_analyze_prop_odds_hot_player(self, model):
        """Test hot player over prediction"""
        model.table.query.return_value = {
            "Items": [
                {"stats": {"PTS": "32", "MIN": "35"}},
                {"stats": {"PTS": "28", "MIN": "33"}},
                {"stats": {"PTS": "30", "MIN": "36"}},
            ]
        }
        
        prop_item = {
            "event_id": "test_game",
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z",
            "player_name": "Jayson Tatum",
            "market_key": "player_points",
            "point": 25.5,
            "outcomes": [{"name": "Over"}, {"name": "Under"}]
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert isinstance(result, AnalysisResult)
        assert "Over" in result.prediction
        assert "HOT" in result.reasoning

    def test_analyze_prop_odds_cold_player(self, model):
        """Test cold player under prediction"""
        model.table.query.return_value = {
            "Items": [
                {"stats": {"PTS": "18", "MIN": "30"}},
                {"stats": {"PTS": "16", "MIN": "28"}},
                {"stats": {"PTS": "20", "MIN": "32"}},
            ]
        }
        
        prop_item = {
            "event_id": "test_game",
            "sport": "basketball_nba",
            "player_name": "Jayson Tatum",
            "market_key": "player_points",
            "point": 25.5,
            "outcomes": [{"name": "Over"}, {"name": "Under"}]
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert isinstance(result, AnalysisResult)
        assert "Under" in result.prediction
        assert "COLD" in result.reasoning

    def test_analyze_prop_odds_no_data(self, model):
        """Test returns None with no player data"""
        model.table.query.return_value = {"Items": []}
        
        prop_item = {
            "player_name": "Unknown Player",
            "sport": "basketball_nba",
            "market_key": "player_points",
            "point": 25.5,
            "outcomes": [{"name": "Over"}, {"name": "Under"}]
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert result is None
