"""Unit tests for team_season_stats_handler"""
import json
from unittest.mock import Mock, patch
import pytest
from team_season_stats_handler import lambda_handler


@patch('team_season_stats_handler.TeamSeasonStatsCollector')
def test_lambda_handler_single_sport(mock_collector_class):
    """Test collecting stats for single sport"""
    mock_collector = Mock()
    mock_collector_class.return_value = mock_collector
    mock_collector.collect_team_stats.return_value = {'stats': 'data'}
    
    event = {'sport': 'basketball_nba'}
    result = lambda_handler(event, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert 'results' in body
    assert 'basketball_nba' in body['results']


@patch('team_season_stats_handler.TeamSeasonStatsCollector')
def test_lambda_handler_multiple_sports(mock_collector_class):
    """Test collecting stats for multiple sports"""
    mock_collector = Mock()
    mock_collector_class.return_value = mock_collector
    mock_collector.collect_team_stats.return_value = {'stats': 'data'}
    
    event = {'sports': ['basketball_nba', 'americanfootball_nfl']}
    result = lambda_handler(event, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert 'results' in body
    assert 'basketball_nba' in body['results']
    assert 'americanfootball_nfl' in body['results']


def test_lambda_handler_no_sport():
    """Test error when no sport specified"""
    event = {}
    result = lambda_handler(event, None)
    
    assert result['statusCode'] == 400
    body = json.loads(result['body'])
    assert 'error' in body


@patch('team_season_stats_handler.TeamSeasonStatsCollector')
def test_lambda_handler_unsupported_sport(mock_collector_class):
    """Test unsupported sport"""
    event = {'sport': 'invalid_sport'}
    result = lambda_handler(event, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert 'results' in body
    assert 'invalid_sport' in body['results']
    assert 'error' in body['results']['invalid_sport']
