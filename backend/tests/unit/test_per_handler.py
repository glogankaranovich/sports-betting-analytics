"""
Unit tests for per_handler
"""
import json
import pytest
from unittest.mock import Mock, patch
from per_handler import handler


@patch('per_handler.PERCalculator')
def test_handler_success(mock_per_class):
    """Test successful PER calculation"""
    mock_per = Mock()
    mock_per.calculate_rolling_per.return_value = {"per": 25.5, "games": 10}
    mock_per_class.return_value = mock_per
    
    event = {
        "body": json.dumps({
            "player_name": "LeBron James",
            "games": 10
        })
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["per"] == 25.5
    assert body["games"] == 10
    mock_per.store_player_per.assert_called_once()


@patch('per_handler.PERCalculator')
def test_handler_missing_player_name(mock_per_class):
    """Test error when player_name is missing"""
    event = {
        "body": json.dumps({
            "games": 10
        })
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


@patch('per_handler.PERCalculator')
def test_handler_player_not_found(mock_per_class):
    """Test error when player has no stats"""
    mock_per = Mock()
    mock_per.calculate_rolling_per.return_value = None
    mock_per_class.return_value = mock_per
    
    event = {
        "body": json.dumps({
            "player_name": "Unknown Player"
        })
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "error" in body


@patch('per_handler.PERCalculator')
def test_handler_default_games(mock_per_class):
    """Test default games parameter"""
    mock_per = Mock()
    mock_per.calculate_rolling_per.return_value = {"per": 20.0}
    mock_per_class.return_value = mock_per
    
    event = {
        "body": json.dumps({
            "player_name": "Stephen Curry"
        })
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 200
    mock_per.calculate_rolling_per.assert_called_with("Stephen Curry", 10)
