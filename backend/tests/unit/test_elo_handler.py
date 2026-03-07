"""
Unit tests for elo_handler
"""
import json
import pytest
from unittest.mock import Mock, patch
from elo_handler import handler


@patch('elo_handler.EloCalculator')
def test_handler_success(mock_elo_class):
    """Test successful Elo rating query"""
    mock_elo = Mock()
    mock_elo.get_team_rating.side_effect = lambda sport, team: 1500 if team == "Team A" else 1600
    mock_elo_class.return_value = mock_elo
    
    event = {
        "body": json.dumps({
            "sport": "basketball_nba",
            "teams": ["Team A", "Team B"]
        })
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["ratings"]["Team A"] == 1500
    assert body["ratings"]["Team B"] == 1600


@patch('elo_handler.EloCalculator')
def test_handler_missing_sport(mock_elo_class):
    """Test error when sport is missing"""
    event = {
        "body": json.dumps({
            "teams": ["Team A"]
        })
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


@patch('elo_handler.EloCalculator')
def test_handler_missing_teams(mock_elo_class):
    """Test error when teams are missing"""
    event = {
        "body": json.dumps({
            "sport": "basketball_nba"
        })
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


@patch('elo_handler.EloCalculator')
def test_handler_empty_body(mock_elo_class):
    """Test error when body is empty"""
    event = {}
    
    response = handler(event, None)
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body
