"""Model analytics tests"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from model_analytics import ModelAnalytics


@pytest.fixture
def analytics():
    with patch("model_analytics.boto3"):
        return ModelAnalytics("test-table")


def test_get_model_performance_summary_empty(analytics):
    """Test summary with no analyses"""
    with patch.object(analytics, "_get_verified_analyses", return_value=[]):
        result = analytics.get_model_performance_summary()
        assert result == {}


def test_get_model_performance_summary_with_data(analytics):
    """Test summary with analyses"""
    analyses = [
        {"model": "consensus", "sport": "basketball_nba", "analysis_correct": True},
        {"model": "consensus", "sport": "basketball_nba", "analysis_correct": False},
        {"model": "value", "sport": "basketball_nba", "analysis_correct": True}
    ]
    
    with patch.object(analytics, "_get_verified_analyses", return_value=analyses):
        result = analytics.get_model_performance_summary()
        
        assert "consensus" in result
        assert result["consensus"]["total_analyses"] == 2
        assert result["consensus"]["correct_analyses"] == 1


def test_get_model_performance_by_sport(analytics):
    """Test performance by sport"""
    analyses = [
        {"model": "consensus", "sport": "basketball_nba", "analysis_correct": True},
        {"model": "consensus", "sport": "americanfootball_nfl", "analysis_correct": False}
    ]
    
    with patch.object(analytics, "_get_verified_analyses", return_value=analyses):
        result = analytics.get_model_performance_by_sport(model="consensus")
        
        assert "consensus" in result
        assert "basketball_nba" in result["consensus"]
        assert "americanfootball_nfl" in result["consensus"]


def test_get_model_performance_by_bet_type(analytics):
    """Test performance by bet type"""
    analyses = [
        {"model": "consensus", "bet_type": "game", "analysis_correct": True},
        {"model": "consensus", "bet_type": "prop", "analysis_correct": False}
    ]
    
    with patch.object(analytics, "_get_verified_analyses", return_value=analyses):
        result = analytics.get_model_performance_by_bet_type(model="consensus")
        
        assert "consensus" in result


def test_get_model_confidence_analysis(analytics):
    """Test confidence analysis"""
    analyses = [
        {"model": "consensus", "confidence": Decimal("0.75"), "analysis_correct": True},
        {"model": "consensus", "confidence": Decimal("0.65"), "analysis_correct": False}
    ]
    
    with patch.object(analytics, "_get_verified_analyses", return_value=analyses):
        result = analytics.get_model_confidence_analysis(model="consensus")
        
        assert isinstance(result, dict)


def test_get_performance_over_time(analytics):
    """Test performance over time"""
    analyses = [
        {
            "model": "consensus",
            "commence_time": "2024-01-15T20:00:00Z",
            "analysis_correct": True
        }
    ]
    
    with patch.object(analytics, "_get_verified_analyses", return_value=analyses):
        result = analytics.get_performance_over_time(model="consensus")
        
        assert isinstance(result, list)


def test_get_recent_predictions_empty(analytics):
    """Test getting recent predictions with no data"""
    analytics.table = Mock()
    analytics.table.query.return_value = {"Items": []}
    
    result = analytics.get_recent_predictions(model="consensus", limit=10)
    assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
