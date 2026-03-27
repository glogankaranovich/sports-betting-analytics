"""Tests for BetExecutor"""
import pytest
from decimal import Decimal
from unittest.mock import Mock
from benny.bet_executor import BetExecutor


@pytest.fixture
def mock_table():
    return Mock()


@pytest.fixture
def mock_sqs():
    return Mock()


def test_place_bet_stores_in_dynamodb(mock_table, mock_sqs):
    """Test bet is stored in DynamoDB"""
    executor = BetExecutor(mock_table, mock_sqs)
    
    opportunity = {
        "game_id": "test123",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Celtics",
        "prediction": "Lakers",
        "confidence": 0.75,
        "reasoning": "Test reasoning",
        "key_factors": ["factor1"],
        "market_key": "h2h",
        "commence_time": "2026-03-08T00:00:00",
        "odds": -150,
        "expected_value": 0.10
    }
    
    result = executor.place_bet(opportunity, Decimal("10.00"), Decimal("100.00"))
    
    assert result["success"]
    assert mock_table.put_item.call_count == 2  # Bet + analysis record


def test_place_bet_returns_bet_info(mock_table, mock_sqs):
    """Test bet placement returns correct info"""
    executor = BetExecutor(mock_table, mock_sqs)
    
    opportunity = {
        "game_id": "test123",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Celtics",
        "prediction": "Lakers",
        "confidence": 0.75,
        "reasoning": "Test reasoning",
        "key_factors": ["factor1"],
        "market_key": "h2h",
        "commence_time": "2026-03-08T00:00:00",
        "odds": -150,
        "expected_value": 0.10
    }
    
    result = executor.place_bet(opportunity, Decimal("10.00"), Decimal("100.00"))
    
    assert result["bet_amount"] == 10.00
    assert "bet_id" in result


def test_send_notification_in_dev(mock_table, mock_sqs, monkeypatch):
    """Test notification sent in dev environment"""
    monkeypatch.setenv("ENVIRONMENT", "dev")
    executor = BetExecutor(mock_table, mock_sqs, "https://queue-url")
    
    opportunity = {
        "game_id": "test123",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Celtics",
        "prediction": "Lakers",
        "confidence": 0.75,
        "reasoning": "Test reasoning",
        "key_factors": ["factor1"],
        "market_key": "h2h",
        "commence_time": "2026-03-08T00:00:00",
        "odds": -150,
        "expected_value": 0.10
    }
    
    executor.place_bet(opportunity, Decimal("10.00"), Decimal("100.00"))
    
    assert mock_sqs.send_message.called


def test_no_notification_without_queue_url(mock_table, mock_sqs, monkeypatch):
    """Test no notification sent without queue URL"""
    monkeypatch.setenv("ENVIRONMENT", "dev")
    executor = BetExecutor(mock_table, mock_sqs, None)
    
    opportunity = {
        "game_id": "test123",
        "sport": "basketball_nba",
        "home_team": "Lakers",
        "away_team": "Celtics",
        "prediction": "Lakers",
        "confidence": 0.75,
        "reasoning": "Test reasoning",
        "key_factors": ["factor1"],
        "market_key": "h2h",
        "commence_time": "2026-03-08T00:00:00",
        "odds": -150,
        "expected_value": 0.10
    }
    
    executor.place_bet(opportunity, Decimal("10.00"), Decimal("100.00"))
    
    assert not mock_sqs.send_message.called
