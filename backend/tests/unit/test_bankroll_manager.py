"""Tests for BankrollManager"""
import pytest
from decimal import Decimal
from unittest.mock import Mock
from benny.bankroll_manager import BankrollManager


@pytest.fixture
def mock_table():
    return Mock()


def test_calculate_bet_size_kelly(mock_table):
    """Test Kelly Criterion bet sizing"""
    mock_table.query.return_value = {"Items": [{"amount": "100.00"}]}
    manager = BankrollManager(mock_table)
    
    bet_size = manager.calculate_bet_size(confidence=0.60, odds=2.0)
    
    assert bet_size >= 0
    assert bet_size <= manager.bankroll * Decimal("0.20")


def test_calculate_bet_size_respects_max(mock_table):
    """Test bet size doesn't exceed max percentage"""
    mock_table.query.return_value = {"Items": [{"amount": "100.00"}]}
    manager = BankrollManager(mock_table)
    
    bet_size = manager.calculate_bet_size(confidence=0.99, odds=10.0)
    
    assert bet_size <= Decimal("20.00")


def test_update_bankroll(mock_table):
    """Test bankroll update"""
    mock_table.query.return_value = {"Items": [{"amount": "100.00"}]}
    manager = BankrollManager(mock_table)
    
    manager.update_bankroll(Decimal("150.00"))
    
    assert manager.bankroll == Decimal("150.00")
    mock_table.put_item.assert_called_once()


def test_should_reset_weekly_budget(mock_table):
    """Test weekly budget reset detection"""
    mock_table.query.return_value = {"Items": [{"amount": "0.00"}]}
    manager = BankrollManager(mock_table)
    
    assert manager.should_reset_weekly_budget()


def test_reset_weekly_budget(mock_table):
    """Test weekly budget reset"""
    mock_table.query.return_value = {"Items": [{"amount": "0.00"}]}
    manager = BankrollManager(mock_table)
    
    manager.reset_weekly_budget()
    
    assert manager.bankroll == Decimal("100.00")
