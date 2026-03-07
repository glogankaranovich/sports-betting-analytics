"""
Unit tests for metrics_calculator_handler
"""
import json
import pytest
from unittest.mock import Mock, patch
from metrics_calculator_handler import lambda_handler


@patch('metrics_calculator_handler.TeamStatsCollector')
@patch('metrics_calculator_handler.SUPPORTED_SPORTS', ['basketball_nba', 'icehockey_nhl'])
def test_lambda_handler_success(mock_collector_class):
    """Test successful metrics calculation"""
    mock_collector = Mock()
    mock_collector.calculate_opponent_adjusted_metrics.side_effect = [10, 8]
    mock_collector_class.return_value = mock_collector
    
    response = lambda_handler({}, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["metrics_calculated"]["basketball_nba"] == 10
    assert body["metrics_calculated"]["icehockey_nhl"] == 8
    assert body["total"] == 18


@patch('metrics_calculator_handler.TeamStatsCollector')
@patch('metrics_calculator_handler.SUPPORTED_SPORTS', ['basketball_nba'])
def test_lambda_handler_sport_error(mock_collector_class):
    """Test handling of sport-specific errors"""
    mock_collector = Mock()
    mock_collector.calculate_opponent_adjusted_metrics.side_effect = Exception("API error")
    mock_collector_class.return_value = mock_collector
    
    response = lambda_handler({}, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["metrics_calculated"]["basketball_nba"] == 0
    assert body["total"] == 0


@patch('metrics_calculator_handler.TeamStatsCollector')
def test_lambda_handler_collector_error(mock_collector_class):
    """Test handling of collector initialization error"""
    mock_collector_class.side_effect = Exception("Collector error")
    
    response = lambda_handler({}, None)
    
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body
