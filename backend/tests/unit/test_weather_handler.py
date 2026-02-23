"""Unit tests for weather_handler"""
import json
from unittest.mock import Mock, patch, MagicMock
import pytest
from weather_handler import lambda_handler


@patch.dict('os.environ', {'DYNAMODB_TABLE': 'test-table'})
@patch('weather_handler.boto3')
@patch('weather_handler.WeatherCollector')
def test_lambda_handler_success(mock_collector_class, mock_boto3):
    """Test successful weather collection"""
    # Mock DynamoDB
    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table
    mock_table.query.return_value = {
        'Items': [
            {
                'pk': 'GAME#test123',
                'venue': 'Test Arena',
                'home_team': 'Test City Team',
                'sport': 'basketball_nba',
                'commence_time': '2026-02-23T00:00:00Z'
            }
        ]
    }
    
    # Mock weather collector
    mock_collector = Mock()
    mock_collector_class.return_value = mock_collector
    mock_collector.get_weather_for_game.return_value = {'condition': 'Clear'}
    
    event = {'sport': 'basketball_nba'}
    result = lambda_handler(event, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['games_checked'] == 1
    assert body['weather_collected'] == 1


@patch.dict('os.environ', {'DYNAMODB_TABLE': 'test-table'})
@patch('weather_handler.boto3')
@patch('weather_handler.WeatherCollector')
def test_lambda_handler_no_games(mock_collector_class, mock_boto3):
    """Test when no games found"""
    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table
    mock_table.query.return_value = {'Items': []}
    
    event = {'sport': 'basketball_nba'}
    result = lambda_handler(event, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['games_checked'] == 0
    assert body['weather_collected'] == 0


@patch('weather_handler.boto3')
def test_lambda_handler_error(mock_boto3):
    """Test error handling"""
    mock_boto3.resource.side_effect = Exception("DynamoDB error")
    
    event = {'sport': 'basketball_nba'}
    result = lambda_handler(event, None)
    
    assert result['statusCode'] == 500
    body = json.loads(result['body'])
    assert 'error' in body
