"""Additional benny trader tests"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from benny_trader import BennyTrader


@pytest.fixture
def trader():
    with patch("benny_trader.table") as mock_table:
        mock_table.query.return_value = {
            "Items": [{
                "amount": Decimal("100.00"),
                "timestamp": datetime.utcnow().isoformat(),
            }]
        }
        mock_table.get_item.return_value = {
            "Item": {
                "performance_by_sport": {},
                "performance_by_market": {}
            }
        }
        with patch("benny_trader.bedrock"):
            return BennyTrader(version="v1")


# _normalize_prediction tests removed - function was unused and removed in model refactor


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
