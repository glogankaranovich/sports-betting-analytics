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
    mock_trader = MagicMock()
    mock_trader.analyze_and_bet.return_value = {
        "bets_placed": 3,
        "games_analyzed": 10,
        "current_bankroll": 95.50,
    }
    mock_trader_class.return_value = mock_trader

    response = handler({}, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["bets_placed"] == 3
    assert body["games_analyzed"] == 10
    assert body["current_bankroll"] == 95.50
    assert "timestamp" in body

    mock_trader_class.assert_called_once_with("test-table")
    mock_trader.analyze_and_bet.assert_called_once()


@patch("benny_trader_handler.BennyTrader")
def test_handler_no_bets(mock_trader_class, lambda_context, mock_env):
    """Test handler when no bets are placed."""
    mock_trader = MagicMock()
    mock_trader.analyze_and_bet.return_value = {
        "bets_placed": 0,
        "games_analyzed": 5,
        "current_bankroll": 100.00,
    }
    mock_trader_class.return_value = mock_trader

    response = handler({}, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["bets_placed"] == 0
    assert body["games_analyzed"] == 5


@patch("benny_trader_handler.BennyTrader")
def test_handler_time_window(mock_trader_class, lambda_context, mock_env):
    """Test handler uses correct time window."""
    mock_trader = MagicMock()
    mock_trader.analyze_and_bet.return_value = {
        "bets_placed": 2,
        "games_analyzed": 8,
        "current_bankroll": 98.00,
    }
    mock_trader_class.return_value = mock_trader

    with patch("benny_trader_handler.datetime") as mock_datetime:
        now = datetime(2026, 2, 8, 14, 0, 0)
        mock_datetime.utcnow.return_value = now

        handler({}, lambda_context)

        call_args = mock_trader.analyze_and_bet.call_args
        assert call_args.kwargs["start_time"] == now
        assert call_args.kwargs["end_time"] == now + timedelta(hours=24)
