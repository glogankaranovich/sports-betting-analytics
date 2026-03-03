"""Unit tests for Matchup model"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal

import sys
sys.path.insert(0, '/Users/glkaranovich/workplace/sports-betting-analytics/backend')

from ml.models.matchup import MatchupModel
from ml.types import AnalysisResult


class TestMatchupModel:
    
    @pytest.fixture
    def model(self):
        """Create a Matchup model instance with mocked dependencies"""
        mock_table = Mock()
        with patch('ml.models.matchup.WeatherCollector'):
            model = MatchupModel(dynamodb_table=mock_table)
            model.weather_collector = Mock()
            return model

    def test_analyze_game_odds_with_h2h_advantage(self, model):
        """Test game analysis with strong H2H advantage"""
        model.table.query.return_value = {
            "Items": [
                {"winner": "Boston Celtics"},
                {"winner": "Boston Celtics"},
                {"winner": "Boston Celtics"},
                {"winner": "Miami Heat"},
            ]
        }
        model.table.get_item.return_value = {"Item": None}
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", [], game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Boston Celtics"
        assert result.confidence > 0.5
        assert "head-to-head" in result.reasoning.lower()

    def test_analyze_game_odds_with_style_matchup(self, model):
        """Test game analysis with style matchup advantage"""
        model.table.query.side_effect = [
            {"Items": []},  # No H2H history
            {"Items": [{"stats": {"Field Goal %": "50", "Defensive Rebounds": "45"}}]},  # Home stats
            {"Items": [{"stats": {"Field Goal %": "42", "Defensive Rebounds": "40"}}]},  # Away stats
        ]
        model.table.get_item.return_value = {"Item": None}
        
        game_info = {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Miami Heat",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", [], game_info)
        
        assert isinstance(result, AnalysisResult)
        assert result.prediction == "Boston Celtics"
        assert result.confidence >= 0.3

    def test_analyze_game_odds_with_weather(self, model):
        """Test game analysis includes weather impact"""
        model.table.query.return_value = {"Items": []}
        model.table.get_item.return_value = {
            "Item": {
                "impact": "high",
                "wind_mph": 20,
                "temp_f": 28,
                "precip_in": 0.3
            }
        }
        
        game_info = {
            "sport": "americanfootball_nfl",
            "home_team": "Green Bay Packers",
            "away_team": "Chicago Bears",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_game_odds("test_game", [], game_info)
        
        assert isinstance(result, AnalysisResult)
        assert "Weather impact" in result.reasoning

    def test_analyze_prop_odds_over(self, model):
        """Test prop analysis predicts over"""
        model.table.get_item.return_value = {
            "Item": {
                "home_team": "Boston Celtics",
                "away_team": "Miami Heat"
            }
        }
        model.table.query.return_value = {
            "Items": [
                {"sk": "2026-03-01#vs_miami_heat", "stats": {"PTS": "28"}},
                {"sk": "2026-02-15#vs_miami_heat", "stats": {"PTS": "32"}},
                {"sk": "2026-01-20#vs_miami_heat", "stats": {"PTS": "30"}},
            ]
        }
        
        prop_item = {
            "player_name": "Jayson Tatum",
            "sport": "basketball_nba",
            "event_id": "test_game",
            "team": "Boston Celtics",
            "market_key": "player_points",
            "point": 25.5,
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert isinstance(result, AnalysisResult)
        assert "Over" in result.prediction
        assert result.confidence > 0.5

    def test_analyze_prop_odds_under(self, model):
        """Test prop analysis predicts under"""
        model.table.get_item.return_value = {
            "Item": {
                "home_team": "Boston Celtics",
                "away_team": "Miami Heat"
            }
        }
        model.table.query.return_value = {
            "Items": [
                {"sk": "2026-03-01#vs_miami_heat", "stats": {"PTS": "18"}},
                {"sk": "2026-02-15#vs_miami_heat", "stats": {"PTS": "16"}},
                {"sk": "2026-01-20#vs_miami_heat", "stats": {"PTS": "20"}},
            ]
        }
        
        prop_item = {
            "player_name": "Jayson Tatum",
            "sport": "basketball_nba",
            "event_id": "test_game",
            "team": "Boston Celtics",
            "market_key": "player_points",
            "point": 25.5,
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert isinstance(result, AnalysisResult)
        assert "Under" in result.prediction

    def test_analyze_prop_odds_no_data(self, model):
        """Test prop analysis returns None with no historical data"""
        model.table.get_item.return_value = {
            "Item": {
                "home_team": "Boston Celtics",
                "away_team": "Miami Heat"
            }
        }
        model.table.query.return_value = {"Items": []}
        
        prop_item = {
            "player_name": "Jayson Tatum",
            "sport": "basketball_nba",
            "event_id": "test_game",
            "team": "Boston Celtics",
            "market_key": "player_points",
            "point": 25.5
        }
        
        result = model.analyze_prop_odds(prop_item)
        
        assert result is None

    def test_get_h2h_advantage_home_favored(self, model):
        """Test H2H calculation favors home team"""
        model.table.query.return_value = {
            "Items": [
                {"winner": "Boston Celtics"},
                {"winner": "Boston Celtics"},
                {"winner": "Boston Celtics"},
                {"winner": "Miami Heat"},
            ]
        }
        
        advantage = model._get_h2h_advantage("basketball_nba", "Boston Celtics", "Miami Heat")
        
        assert advantage > 0
        assert advantage == pytest.approx(1.0, abs=0.1)

    def test_get_h2h_advantage_no_history(self, model):
        """Test H2H returns 0 with no history"""
        model.table.query.return_value = {"Items": []}
        
        advantage = model._get_h2h_advantage("basketball_nba", "Boston Celtics", "Miami Heat")
        
        assert advantage == 0.0

    def test_get_style_matchup_nba(self, model):
        """Test style matchup for NBA"""
        model.table.query.side_effect = [
            {"Items": [{"stats": {"Field Goal %": "50", "Defensive Rebounds": "45"}}]},
            {"Items": [{"stats": {"Field Goal %": "42", "Defensive Rebounds": "40"}}]},
        ]
        
        advantage = model._get_style_matchup("basketball_nba", "Boston Celtics", "Miami Heat")
        
        assert advantage > 0

    def test_get_style_matchup_nhl(self, model):
        """Test style matchup for NHL"""
        model.table.query.side_effect = [
            {"Items": [{"stats": {"Shots": "35", "Power Play Percentage": "25.0"}}]},
            {"Items": [{"stats": {"Shots": "28", "Power Play Percentage": "20.0"}}]},
        ]
        
        advantage = model._get_style_matchup("icehockey_nhl", "Boston Bruins", "Montreal Canadiens")
        
        assert advantage > 0

    def test_get_style_matchup_soccer(self, model):
        """Test style matchup for soccer"""
        model.table.query.side_effect = [
            {"Items": [{"stats": {"ON GOAL": "8", "Effective Tackles": "15"}}]},
            {"Items": [{"stats": {"ON GOAL": "5", "Effective Tackles": "12"}}]},
        ]
        
        advantage = model._get_style_matchup("soccer_epl", "Liverpool", "Manchester United")
        
        assert advantage > 0

    def test_get_style_matchup_no_stats(self, model):
        """Test style matchup returns 0 with no stats"""
        model.table.query.return_value = {"Items": []}
        
        advantage = model._get_style_matchup("basketball_nba", "Boston Celtics", "Miami Heat")
        
        assert advantage == 0.0

    def test_get_style_matchup_unsupported_sport(self, model):
        """Test style matchup returns 0 for unsupported sport"""
        model.table.query.side_effect = [
            {"Items": [{"stats": {"some_stat": "10"}}]},
            {"Items": [{"stats": {"some_stat": "8"}}]},
        ]
        
        advantage = model._get_style_matchup("unknown_sport", "Team A", "Team B")
        
        assert advantage == 0.0
