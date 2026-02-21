"""Additional benny trader tests"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from benny_trader import BennyTrader


@pytest.fixture
def trader():
    with patch("benny_trader.boto3"):
        with patch.object(BennyTrader, "_get_current_bankroll", return_value=Decimal("100")):
            with patch.object(BennyTrader, "_get_week_start", return_value="2024-01-15"):
                with patch.object(BennyTrader, "_get_learning_parameters", return_value={}):
                    return BennyTrader()


def test_normalize_prediction_spread_with_bookmaker(trader):
    """Test normalizing spread with bookmaker"""
    pred = trader._normalize_prediction("Patriots +5.0 @ draftkings")
    assert pred == "Patriots spread"


def test_normalize_prediction_negative_spread(trader):
    """Test normalizing negative spread"""
    pred = trader._normalize_prediction("Lakers -7.5")
    assert pred == "Lakers spread"


def test_normalize_prediction_total_with_decimal(trader):
    """Test normalizing total with decimal"""
    pred = trader._normalize_prediction("Over 220.5")
    assert pred == "Over"
    
    pred = trader._normalize_prediction("Under 45.5")
    assert pred == "Under"


def test_normalize_prediction_moneyline(trader):
    """Test normalizing moneyline"""
    pred = trader._normalize_prediction("Lakers")
    assert pred == "Lakers"


def test_get_learning_parameters_default(trader):
    """Test default learning parameters initialization"""
    trader.table = Mock()
    trader.table.get_item.return_value = {}
    
    params = trader._get_learning_parameters()
    
    # Should create defaults
    trader.table.put_item.assert_called_once()
    assert "min_confidence_adjustment" in params


def test_get_learning_parameters_existing(trader):
    """Test loading existing learning parameters"""
    trader.table = Mock()
    trader.table.get_item.return_value = {
        "Item": {
            "min_confidence_adjustment": Decimal("0.05"),
            "kelly_fraction": Decimal("0.25")
        }
    }
    
    params = trader._get_learning_parameters()
    assert params["min_confidence_adjustment"] == Decimal("0.05")


def test_get_week_start_calculation(trader):
    """Test week start calculation"""
    with patch("benny_trader.datetime") as mock_dt:
        # Mock a Wednesday
        mock_dt.utcnow.return_value = datetime(2024, 1, 17)  # Wednesday
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        week_start = trader._get_week_start()
        # Should return Monday (2024-01-15)
        assert "2024-01-15" in week_start


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
