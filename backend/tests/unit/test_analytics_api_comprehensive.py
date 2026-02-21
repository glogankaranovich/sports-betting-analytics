"""Comprehensive tests for analytics API handler"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from api.analytics import AnalyticsHandler, _calculate_model_roi, _get_model_comparison_data


@pytest.fixture
def handler():
    return AnalyticsHandler()


@pytest.fixture
def mock_table():
    with patch("api.analytics.table") as mock:
        yield mock


def test_get_model_performance_all_models(handler, mock_table):
    """Test model performance for all models"""
    with patch("model_performance.ModelPerformanceTracker") as mock_tracker:
        mock_instance = Mock()
        mock_instance.get_all_models_performance.return_value = {"consensus": {"accuracy": 0.65}}
        mock_tracker.return_value = mock_instance
        
        response = handler.get_model_performance({"sport": "basketball_nba", "days": "30"})
        assert response["statusCode"] == 200


def test_calculate_model_roi_with_wins(mock_table):
    """Test ROI calculation with winning bets"""
    mock_table.query.return_value = {
        "Items": [
            {
                "model": "consensus",
                "confidence": Decimal("0.75"),
                "outcome": "win",
                "recommended_odds": -110,
                "bet_amount": Decimal("100")
            }
        ]
    }
    
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    results = _calculate_model_roi("consensus", "basketball_nba", cutoff)
    
    assert len(results) > 0


def test_calculate_model_roi_no_bets(mock_table):
    """Test ROI calculation with no bets"""
    mock_table.query.return_value = {"Items": []}
    
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    results = _calculate_model_roi("consensus", "basketball_nba", cutoff)
    
    assert len(results) == 0


def test_get_model_comparison_data(mock_table):
    """Test model comparison data retrieval"""
    mock_table.query.return_value = {
        "Items": [
            {
                "model": "consensus",
                "confidence": Decimal("0.75"),
                "outcome": "win",
                "recommended_odds": -110
            }
        ]
    }
    
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    results = _get_model_comparison_data("consensus", "basketball_nba", cutoff)
    
    assert isinstance(results, list)


def test_get_model_rankings_with_mode(handler, mock_table):
    """Test model rankings with mode parameter"""
    mock_table.query.return_value = {"Items": []}
    
    response = handler.get_model_rankings({"sport": "basketball_nba", "mode": "games"})
    assert response["statusCode"] == 200


def test_get_model_comparison_all_sports(handler, mock_table):
    """Test model comparison for all sports"""
    mock_table.get_item.return_value = {}
    mock_table.query.return_value = {"Items": []}
    
    response = handler.get_model_comparison({"sport": "all", "days": "30"})
    assert response["statusCode"] == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
