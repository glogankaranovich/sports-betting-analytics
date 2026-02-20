"""
Unit tests for FundamentalsModel
"""
import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from ml.models import FundamentalsModel


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table"""
    return MagicMock()


@pytest.fixture
def model(mock_table):
    """Create a FundamentalsModel instance with mocked dependencies"""
    os.environ["DYNAMODB_TABLE"] = "test-table"
    
    with patch("ml.models.EloCalculator") as mock_elo, \
         patch("ml.models.TravelFatigueCalculator") as mock_fatigue:
        
        mock_elo_instance = MagicMock()
        mock_elo_instance.get_team_rating.return_value = 1500
        mock_elo.return_value = mock_elo_instance
        
        mock_fatigue_instance = MagicMock()
        mock_fatigue_instance.calculate_fatigue_score.return_value = {"fatigue_score": 30, "total_miles": 500, "days_rest": 2}
        mock_fatigue.return_value = mock_fatigue_instance
        
        model = FundamentalsModel(dynamodb_table=mock_table)
        yield model


class TestFundamentalsModel:
    def test_analyze_game_with_all_metrics(self, model, mock_table):
        """Test game analysis with all advanced metrics available"""
        game_info = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2024-01-15T19:00:00Z",
        }
        
        odds_items = [
            {
                "bookmaker": "draftkings",
                "outcomes": [
                    {"name": "Lakers", "price": -150},
                    {"name": "Warriors", "price": 130},
                ],
            }
        ]
        
        # Mock Elo ratings
        model.elo_calculator.get_team_rating.side_effect = [1650, 1550]
        
        # Mock fatigue
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {"fatigue_score": 20, "total_miles": 300, "days_rest": 2},
            {"fatigue_score": 55, "total_miles": 1500, "days_rest": 1},
        ]
        
        # Mock adjusted metrics
        mock_table.query.side_effect = [
            {"Items": [{"metrics": {"adjusted_ppg": 112.5, "fg_pct": 0.48}}]},  # Home
            {"Items": [{"metrics": {"adjusted_ppg": 108.2, "fg_pct": 0.45}}]},  # Away
        ]
        
        # No weather for NBA
        mock_table.get_item.return_value = {"Item": None}
        
        result = model.analyze_game_odds("test123", odds_items, game_info)
        
        assert result is not None
        assert result.prediction in ["Lakers", "Warriors"]
        assert result.confidence > 0
        assert result.confidence <= 1.0

    def test_analyze_game_elo_advantage(self, model, mock_table):
        """Test prediction favors team with significant Elo advantage"""
        game_info = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2024-01-15T19:00:00Z",
        }
        
        odds_items = [
            {
                "bookmaker": "draftkings",
                "outcomes": [
                    {"name": "Lakers", "price": -110},
                    {"name": "Warriors", "price": -110},
                ],
            }
        ]
        
        # Lakers have 150 point Elo advantage
        model.elo_calculator.get_team_rating.side_effect = [1700, 1550]
        model.fatigue_calculator.calculate_fatigue_score.return_value = {"fatigue_score": 30, "total_miles": 500, "days_rest": 2}
        mock_table.query.return_value = {"Items": []}
        mock_table.get_item.return_value = {"Item": None}
        
        result = model.analyze_game_odds("test123", odds_items, game_info)
        
        assert result.prediction == "Lakers"
        assert result.confidence > 0.6

    def test_analyze_game_fatigue_impact(self, model, mock_table):
        """Test fatigue affects prediction"""
        game_info = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2024-01-15T19:00:00Z",
        }
        
        odds_items = [
            {
                "bookmaker": "draftkings",
                "outcomes": [
                    {"name": "Lakers", "price": -110},
                    {"name": "Warriors", "price": -110},
                ],
            }
        ]
        
        # Equal Elo, but Warriors very fatigued
        model.elo_calculator.get_team_rating.side_effect = [1600, 1600]
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {"fatigue_score": 15, "total_miles": 200, "days_rest": 3},  # Home fresh
            {"fatigue_score": 75, "total_miles": 2500, "days_rest": 1},  # Away tired
        ]
        mock_table.query.side_effect = [
            {"Items": []},  # No adjusted metrics
            {"Items": []},
        ]
        mock_table.get_item.return_value = {"Item": None}  # No weather
        
        result = model.analyze_game_odds("test123", odds_items, game_info)
        
        # Should favor home team due to away fatigue
        assert result.prediction == "Lakers"

    def test_analyze_game_weather_impact(self, model, mock_table):
        """Test weather affects outdoor game predictions"""
        game_info = {
            "game_id": "test123",
            "sport": "americanfootball_nfl",
            "home_team": "Packers",
            "away_team": "Cowboys",
            "commence_time": "2024-01-15T13:00:00Z",
        }
        
        odds_items = [
            {
                "bookmaker": "draftkings",
                "outcomes": [
                    {"name": "Packers", "price": -110},
                    {"name": "Cowboys", "price": -110},
                ],
            }
        ]
        
        # Equal teams, high weather impact
        model.elo_calculator.get_team_rating.side_effect = [1600, 1600]
        model.fatigue_calculator.calculate_fatigue_score.return_value = {"fatigue_score": 30, "total_miles": 500, "days_rest": 2}
        mock_table.query.return_value = {"Items": []}
        mock_table.get_item.return_value = {"Item": {"temp_f": Decimal("10"), "wind_mph": Decimal("25"), "impact": "high"}}
        
        result = model.analyze_game_odds("test123", odds_items, game_info)
        
        assert result is not None
        assert "weather" in result.reasoning.lower() or any("weather" in f.lower() for f in result.key_factors)

    def test_analyze_game_no_data_fallback(self, model, mock_table):
        """Test model handles missing data gracefully"""
        game_info = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2024-01-15T19:00:00Z",
        }
        
        odds_items = [
            {
                "bookmaker": "draftkings",
                "outcomes": [
                    {"name": "Lakers", "price": -110},
                    {"name": "Warriors", "price": -110},
                ],
            }
        ]
        
        # Default values
        model.elo_calculator.get_team_rating.return_value = 1500
        model.fatigue_calculator.calculate_fatigue_score.return_value = {"fatigue_score": 30, "total_miles": 500, "days_rest": 2}
        mock_table.query.return_value = {"Items": []}
        mock_table.get_item.return_value = {"Item": None}
        
        result = model.analyze_game_odds("test123", odds_items, game_info)
        
        # Should still make prediction with defaults
        assert result is not None
        assert result.prediction in ["Lakers", "Warriors"]

    def test_compare_metrics_nba(self, model):
        """Test NBA metric comparison"""
        home_metrics = {"adjusted_ppg": 115.0, "fg_pct": 0.48}
        away_metrics = {"adjusted_ppg": 108.0, "fg_pct": 0.45}
        
        score = model._compare_metrics(home_metrics, away_metrics, "basketball_nba")
        
        assert score > 0  # Home team advantage

    def test_compare_metrics_nfl(self, model):
        """Test NFL metric comparison"""
        home_metrics = {"adjusted_total_yards": 380.0}
        away_metrics = {"adjusted_total_yards": 320.0}
        
        score = model._compare_metrics(home_metrics, away_metrics, "americanfootball_nfl")
        
        assert score > 0  # Home team advantage

    def test_compare_metrics_soccer(self, model):
        """Test soccer metric comparison"""
        home_metrics = {"adjusted_shots_per_game": 15.0}
        away_metrics = {"adjusted_shots_per_game": 12.0}
        
        score = model._compare_metrics(home_metrics, away_metrics, "soccer_epl")
        
        assert score > 0  # Home team advantage
