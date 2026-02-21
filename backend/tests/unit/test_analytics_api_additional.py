"""More analytics API tests"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from api.analytics import AnalyticsHandler


@pytest.fixture
def handler():
    return AnalyticsHandler()


def test_get_analytics_by_sport_cache_miss(handler):
    """Test analytics by_sport with cache miss"""
    with patch("api.analytics.table") as mock_table, \
         patch("model_analytics.ModelAnalytics") as mock_analytics:
        
        mock_table.query.return_value = {"Items": []}
        
        mock_instance = Mock()
        mock_instance.get_model_performance_by_sport.return_value = {"basketball_nba": {"accuracy": 0.65}}
        mock_analytics.return_value = mock_instance
        
        response = handler.get_analytics({"type": "by_sport", "model": "consensus", "days": "30"})
        assert response["statusCode"] == 200


def test_get_analytics_confidence_cache_miss(handler):
    """Test analytics confidence with cache miss"""
    with patch("api.analytics.table") as mock_table, \
         patch("model_analytics.ModelAnalytics") as mock_analytics:
        
        mock_table.query.return_value = {"Items": []}
        
        mock_instance = Mock()
        mock_instance.get_model_confidence_analysis.return_value = {"high": 10, "medium": 5}
        mock_analytics.return_value = mock_instance
        
        response = handler.get_analytics({"type": "confidence", "model": "value"})
        assert response["statusCode"] == 200


def test_get_analytics_over_time_cache_miss(handler):
    """Test analytics over_time with cache miss"""
    with patch("api.analytics.table") as mock_table, \
         patch("model_analytics.ModelAnalytics") as mock_analytics:
        
        mock_table.query.return_value = {"Items": []}
        
        mock_instance = Mock()
        mock_instance.get_performance_over_time.return_value = [{"date": "2024-01-15", "accuracy": 0.65}]
        mock_analytics.return_value = mock_instance
        
        response = handler.get_analytics({"type": "over_time", "model": "consensus"})
        assert response["statusCode"] == 200


def test_get_analytics_recent_predictions(handler):
    """Test analytics recent_predictions"""
    with patch("api.analytics.table") as mock_table, \
         patch("model_analytics.ModelAnalytics") as mock_analytics:
        
        mock_table.query.return_value = {"Items": []}
        
        mock_instance = Mock()
        mock_instance.get_recent_predictions.return_value = [{"prediction": "Lakers -5.5"}]
        mock_analytics.return_value = mock_instance
        
        response = handler.get_analytics({"type": "recent_predictions", "model": "consensus", "limit": "10"})
        assert response["statusCode"] == 200


def test_get_analytics_by_bet_type_all_models(handler):
    """Test analytics by_bet_type for all models"""
    with patch("api.analytics.table") as mock_table, \
         patch("model_analytics.ModelAnalytics") as mock_analytics:
        
        mock_instance = Mock()
        mock_instance.get_model_performance_by_bet_type.return_value = {"game": {"accuracy": 0.65}}
        mock_analytics.return_value = mock_instance
        
        response = handler.get_analytics({"type": "by_bet_type", "model": "all"})
        assert response["statusCode"] == 200


def test_get_analytics_invalid_type(handler):
    """Test analytics with invalid type"""
    response = handler.get_analytics({"type": "invalid_type"})
    assert response["statusCode"] == 400


def test_get_analytics_missing_model_param(handler):
    """Test analytics missing required model param"""
    response = handler.get_analytics({"type": "by_sport"})
    assert response["statusCode"] == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
