"""Shared test fixtures for BennyTrader tests"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch


@pytest.fixture
def mock_benny_table():
    """Mock table with proper responses for composition pattern"""
    with patch("benny_trader.table") as mock:
        # Mock for BankrollManager (uses query)
        mock.query.return_value = {
            "Items": [{
                "amount": Decimal("100.00"),
                "timestamp": datetime.utcnow().isoformat(),
            }]
        }
        # Mock for LearningEngine (uses get_item)
        mock.get_item.return_value = {
            "Item": {
                "performance_by_sport": {},
                "performance_by_market": {}
            }
        }
        yield mock


@pytest.fixture
def mock_benny_bedrock():
    """Mock bedrock client"""
    with patch("benny_trader.bedrock") as mock:
        yield mock
