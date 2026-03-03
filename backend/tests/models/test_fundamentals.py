"""Unit tests for Fundamentals model"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Mock the imports before importing the model
import sys
sys.path.insert(0, '/Users/glkaranovich/workplace/sports-betting-analytics/backend')

from ml.models import FundamentalsModel, AnalysisResult


class TestFundamentalsModel:
    """Test suite for Fundamentals model"""
    
    @pytest.fixture
    def model(self):
        """Create a Fundamentals model instance with mocked dependencies"""
        with patch('ml.models.EloCalculator'), \
             patch('ml.models.TravelFatigueCalculator'), \
             patch('ml.models.boto3'):
            model = FundamentalsModel()
            model.table = Mock()
            model.elo_calculator = Mock()
            model.fatigue_calculator = Mock()
            return model
    
    @pytest.fixture
    def sample_game_info(self):
        """Sample game information"""
        return {
            "sport": "basketball_nba",
            "home_team": "Boston Celtics",
            "away_team": "Los Angeles Lakers",
            "commence_time": "2026-03-02T19:00:00Z"
        }
    
    @pytest.fixture
    def sample_odds(self):
        """Sample odds data"""
        return [
            {
                "bookmaker": "draftkings",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Boston Celtics", "price": -150},
                            {"name": "Los Angeles Lakers", "price": 130}
                        ]
                    }
                ]
            }
        ]
    
    def test_analyze_game_odds_nba_with_metrics(self, model, sample_game_info, sample_odds):
        """Test NBA game analysis with full metrics"""
        # Setup mocks
        model.elo_calculator.get_team_rating.side_effect = [1600, 1550]  # Home, Away
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {"fatigue_score": 10},  # Home
            {"fatigue_score": 30}   # Away
        ]
        
        # Mock metrics
        home_metrics = {
            "adjusted_ppg": 115.0,
            "fg_pct": 48.5,
            "offensive_efficiency": 118.0,
            "pace": 102.0
        }
        away_metrics = {
            "adjusted_ppg": 110.0,
            "fg_pct": 46.0,
            "defensive_efficiency": 112.0,
            "pace": 98.0
        }
        model._get_adjusted_metrics = Mock(side_effect=[home_metrics, away_metrics])
        
        # Execute
        result = model.analyze_game_odds("game123", sample_odds, sample_game_info)
        
        # Verify
        assert isinstance(result, AnalysisResult)
        assert result.model == "fundamentals"
        assert result.sport == "basketball_nba"
        assert result.prediction in ["Boston Celtics", "Los Angeles Lakers"]
        assert 0.5 <= result.confidence <= 0.85
        assert result.game_id == "game123"
        assert "Elo" in result.reasoning or "Efficiency" in result.reasoning
    
    def test_analyze_game_odds_nhl(self, model, sample_odds):
        """Test NHL game analysis"""
        game_info = {
            "sport": "icehockey_nhl",
            "home_team": "Carolina Hurricanes",
            "away_team": "Boston Bruins",
            "commence_time": "2026-03-02T19:00:00Z"
        }
        
        model.elo_calculator.get_team_rating.side_effect = [1580, 1570]
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {"fatigue_score": 15},
            {"fatigue_score": 20}
        ]
        
        home_metrics = {"shots_per_game": 32.0, "power_play_pct": 22.0}
        away_metrics = {"shots_per_game": 30.0, "power_play_pct": 20.0}
        model._get_adjusted_metrics = Mock(side_effect=[home_metrics, away_metrics])
        
        result = model.analyze_game_odds("game456", sample_odds, game_info)
        
        assert result.sport == "icehockey_nhl"
        assert result.prediction in ["Carolina Hurricanes", "Boston Bruins"]
        assert 0.5 <= result.confidence <= 0.85
    
    def test_analyze_game_odds_epl(self, model, sample_odds):
        """Test EPL (soccer) game analysis"""
        game_info = {
            "sport": "soccer_epl",
            "home_team": "Manchester City",
            "away_team": "Liverpool",
            "commence_time": "2026-03-02T15:00:00Z"
        }
        
        model.elo_calculator.get_team_rating.side_effect = [1650, 1640]
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {"fatigue_score": 20},
            {"fatigue_score": 25}
        ]
        
        home_metrics = {"shots_on_goal": 6.0, "possession": 60.0}
        away_metrics = {"shots_on_goal": 5.0, "possession": 40.0}
        model._get_adjusted_metrics = Mock(side_effect=[home_metrics, away_metrics])
        
        result = model.analyze_game_odds("game789", sample_odds, game_info)
        
        assert result.sport == "soccer_epl"
        assert result.prediction in ["Manchester City", "Liverpool"]
    
    def test_analyze_game_odds_nfl(self, model, sample_odds):
        """Test NFL game analysis"""
        game_info = {
            "sport": "americanfootball_nfl",
            "home_team": "Kansas City Chiefs",
            "away_team": "Buffalo Bills",
            "commence_time": "2026-03-02T20:00:00Z"
        }
        
        model.elo_calculator.get_team_rating.side_effect = [1620, 1610]
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {"fatigue_score": 10},
            {"fatigue_score": 15}
        ]
        
        home_metrics = {
            "adjusted_total_yards": 380.0,
            "pass_efficiency": 105.0,
            "turnover_differential": 2.0
        }
        away_metrics = {
            "adjusted_total_yards": 360.0,
            "pass_efficiency": 100.0,
            "turnover_differential": 0.0
        }
        model._get_adjusted_metrics = Mock(side_effect=[home_metrics, away_metrics])
        
        result = model.analyze_game_odds("game101", sample_odds, game_info)
        
        assert result.sport == "americanfootball_nfl"
        assert result.prediction in ["Kansas City Chiefs", "Buffalo Bills"]
    
    def test_analyze_game_odds_no_metrics(self, model, sample_game_info, sample_odds):
        """Test game analysis when metrics are unavailable"""
        model.elo_calculator.get_team_rating.side_effect = [1600, 1550]
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {"fatigue_score": 10},
            {"fatigue_score": 30}
        ]
        model._get_adjusted_metrics = Mock(return_value=None)
        
        result = model.analyze_game_odds("game123", sample_odds, sample_game_info)
        
        # Should still make prediction based on Elo and fatigue
        assert isinstance(result, AnalysisResult)
        assert result.prediction in ["Boston Celtics", "Los Angeles Lakers"]
        assert 0.5 <= result.confidence <= 0.85
    
    def test_analyze_game_odds_mlb_with_metrics(self, model, sample_odds):
        """Test that MLB games work with metrics (after backfill)"""
        game_info = {
            "sport": "baseball_mlb",
            "home_team": "New York Yankees",
            "away_team": "Boston Red Sox",
            "commence_time": "2026-06-15T19:00:00Z"
        }
        
        model.elo_calculator.get_team_rating.side_effect = [1600, 1580]
        model.fatigue_calculator.calculate_fatigue_score.side_effect = [
            {"fatigue_score": 10},
            {"fatigue_score": 15}
        ]
        # MLB will have metrics after backfill, but _compare_metrics doesn't support MLB yet
        home_metrics = {"batting_avg": 0.275, "era": 3.50}
        away_metrics = {"batting_avg": 0.265, "era": 3.80}
        model._get_adjusted_metrics = Mock(side_effect=[home_metrics, away_metrics])
        
        with patch.object(model, '_emit_unsupported_sport_metric') as mock_emit:
            result = model.analyze_game_odds("game202", sample_odds, game_info)
            
            # Should emit metric because _compare_metrics doesn't support MLB
            mock_emit.assert_called_once_with("baseball_mlb")
            assert result.sport == "baseball_mlb"
            assert result.prediction in ["New York Yankees", "Boston Red Sox"]
    
    def test_analyze_prop_odds_returns_none(self, model):
        """Test that prop analysis returns None (not supported)"""
        prop_item = {"player_name": "LeBron James", "market": "player_points"}
        result = model.analyze_prop_odds(prop_item)
        assert result is None
    
    def test_compare_metrics_nba(self, model):
        """Test NBA metrics comparison"""
        home_metrics = {
            "adjusted_ppg": 115.0,
            "fg_pct": 48.5,
            "offensive_efficiency": 118.0
        }
        away_metrics = {
            "adjusted_ppg": 110.0,
            "fg_pct": 46.0,
            "defensive_efficiency": 112.0
        }
        
        diff = model._compare_metrics(home_metrics, away_metrics, "basketball_nba")
        
        # Home team should have positive advantage (better stats)
        assert diff > 0
        # Reasonable range (not clamped here, clamping happens in analyze_game_odds)
        assert diff < 50  # Sanity check
    
    def test_compare_metrics_nhl(self, model):
        """Test NHL metrics comparison"""
        home_metrics = {"shots_per_game": 32.0, "power_play_pct": 22.0}
        away_metrics = {"shots_per_game": 28.0, "power_play_pct": 18.0}
        
        diff = model._compare_metrics(home_metrics, away_metrics, "icehockey_nhl")
        
        assert diff > 0
        assert -15 <= diff <= 15
    
    def test_compare_metrics_epl(self, model):
        """Test EPL metrics comparison"""
        home_metrics = {"shots_on_goal": 6.0, "possession": 60.0}
        away_metrics = {"shots_on_goal": 4.0, "possession": 40.0}
        
        diff = model._compare_metrics(home_metrics, away_metrics, "soccer_epl")
        
        assert diff > 0
        assert -15 <= diff <= 15
    
    def test_compare_metrics_unsupported_sport(self, model):
        """Test that unsupported sports return 0 and emit metric"""
        with patch.object(model, '_emit_unsupported_sport_metric') as mock_emit:
            diff = model._compare_metrics({}, {}, "baseball_mlb")
            
            assert diff == 0.0
            mock_emit.assert_called_once_with("baseball_mlb")
    
    def test_calculate_pace_advantage_nba(self, model):
        """Test NBA pace advantage calculation"""
        home_metrics = {
            "pace": 102.0,
            "offensive_efficiency": 118.0
        }
        away_metrics = {
            "pace": 98.0,
            "defensive_efficiency": 112.0
        }
        
        pace_diff = model._calculate_pace_advantage(home_metrics, away_metrics, "basketball_nba")
        
        # Faster pace + better offense should give advantage
        assert pace_diff > 0
        assert -5 <= pace_diff <= 5
    
    def test_calculate_pace_advantage_nhl(self, model):
        """Test NHL pace (shots) advantage calculation"""
        home_metrics = {"shots_per_game": 32.0}
        away_metrics = {"shots_per_game": 28.0}
        
        pace_diff = model._calculate_pace_advantage(home_metrics, away_metrics, "icehockey_nhl")
        
        assert pace_diff > 0
    
    def test_get_adjusted_metrics_success(self, model):
        """Test successful metrics retrieval"""
        model.table.query.return_value = {
            "Items": [{
                "metrics": {
                    "adjusted_ppg": 115.0,
                    "fg_pct": 48.5
                }
            }]
        }
        
        metrics = model._get_adjusted_metrics("basketball_nba", "Boston Celtics")
        
        assert metrics is not None
        assert "adjusted_ppg" in metrics
        assert metrics["adjusted_ppg"] == 115.0
    
    def test_get_adjusted_metrics_not_found(self, model):
        """Test metrics retrieval when no data exists"""
        model.table.query.return_value = {"Items": []}
        
        metrics = model._get_adjusted_metrics("basketball_nba", "Unknown Team")
        
        assert metrics is None
    
    def test_emit_unsupported_sport_metric(self, model):
        """Test CloudWatch metric emission"""
        with patch('ml.models.boto3.client') as mock_boto:
            mock_cloudwatch = Mock()
            mock_boto.return_value = mock_cloudwatch
            
            model._emit_unsupported_sport_metric("baseball_mlb")
            
            mock_cloudwatch.put_metric_data.assert_called_once()
            call_args = mock_cloudwatch.put_metric_data.call_args[1]
            assert call_args["Namespace"] == "SportsAnalytics/Models"
            assert call_args["MetricData"][0]["MetricName"] == "UnsupportedSportPrediction"
            assert call_args["MetricData"][0]["Value"] == 1
