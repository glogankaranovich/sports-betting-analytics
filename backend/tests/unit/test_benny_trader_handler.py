"""Unit tests for Benny trader Lambda handler."""
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest
from benny_trader_handler import handler


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = MagicMock()
    context.function_name = "test-benny-trader"
    context.memory_limit_in_mb = 1024
    context.invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:test-benny-trader"
    )
    return context


@pytest.fixture
def mock_env(monkeypatch):
    """Set environment variables."""
    monkeypatch.setenv("BETS_TABLE", "test-table")


@patch("benny_trader_handler.BennyTrader")
def test_handler_success(mock_trader_class, lambda_context, mock_env):
    """Test successful handler execution."""
    from decimal import Decimal
    
    mock_trader = MagicMock()
    mock_trader.run_daily_analysis.return_value = {
        "bets_placed": 3,
        "opportunities_found": 10,
        "total_bet_amount": 15.0,
        "remaining_bankroll": 85.0,
    }
    mock_trader_class.return_value = mock_trader

    response = handler({}, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["bets_placed"] == 3
    assert "timestamp" in body

    mock_trader_class.assert_called_once()
    mock_trader.run_daily_analysis.assert_called_once()


@patch("benny_trader_handler.BennyTrader")
def test_handler_no_bets(mock_trader_class, lambda_context, mock_env):
    """Test handler when no bets are placed."""
    mock_trader = MagicMock()
    mock_trader.run_daily_analysis.return_value = {
        "bets_placed": 0,
        "opportunities_found": 5,
        "total_bet_amount": 0.0,
        "remaining_bankroll": 100.0,
    }
    mock_trader_class.return_value = mock_trader

    response = handler({}, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["bets_placed"] == 0


@patch("benny_trader_handler.BennyTrader")
def test_handler_time_window(mock_trader_class, lambda_context, mock_env):
    """Test handler executes successfully."""
    mock_trader = MagicMock()
    mock_trader.run_daily_analysis.return_value = {
        "bets_placed": 2,
        "opportunities_found": 8,
        "total_bet_amount": 10.0,
        "remaining_bankroll": 90.0,
    }
    mock_trader_class.return_value = mock_trader

    response = handler({}, lambda_context)

    assert response["statusCode"] == 200
    mock_trader.run_daily_analysis.assert_called_once()
