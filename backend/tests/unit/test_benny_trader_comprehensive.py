"""
Comprehensive tests for Benny autonomous trader
"""
import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, Mock
import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from benny_trader import BennyTrader


class TestBennyTraderComprehensive:

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_init_loads_bankroll(self, mock_bedrock, mock_table):
        """Test initialization loads bankroll"""
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
        
        trader = BennyTrader(version="v1")
        assert trader.bankroll == Decimal("100.00")

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_weekly_bankroll_reset(self, mock_bedrock, mock_table):
        """Test bankroll resets weekly"""
        mock_table.query.return_value = {"Items": []}
        mock_table.get_item.return_value = {
            "Item": {
                "performance_by_sport": {},
                "performance_by_market": {}
            }
        }
        
        trader = BennyTrader(version="v1")
        assert trader.bankroll == Decimal("100.00")

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_calculate_bet_size_kelly_criterion(self, mock_bedrock, mock_table):
        """Test Kelly criterion bet sizing"""
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
        
        trader = BennyTrader(version="v1")
        
        # High confidence should bet more (using American odds)
        high_bet = trader.calculate_bet_size(0.85, -110)
        low_bet = trader.calculate_bet_size(0.60, -110)
        
        assert high_bet >= low_bet
        assert high_bet <= trader.bankroll * Decimal("0.20")  # Max 20%

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_normalize_prediction_spreads(self, mock_bedrock, mock_table):
        """Test prediction normalization for spreads"""
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
        
        trader = BennyTrader(version="v1")
        
        # Test spread normalization
        assert trader._normalize_prediction("Patriots +5.0") == "Patriots spread"
        assert trader._normalize_prediction("Lakers -3.5 @ draftkings") == "Lakers spread"

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_normalize_prediction_totals(self, mock_bedrock, mock_table):
        """Test prediction normalization for totals"""
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
        
        trader = BennyTrader(version="v1")
        
        assert trader._normalize_prediction("Over 220.5") == "Over"
        assert trader._normalize_prediction("Under 45.5") == "Under"

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_normalize_prediction_moneyline(self, mock_bedrock, mock_table):
        """Test prediction normalization for moneyline"""
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
        
        trader = BennyTrader(version="v1")
        
        assert trader._normalize_prediction("Lakers") == "Lakers"
        assert trader._normalize_prediction("Warriors") == "Warriors"

    # test_get_top_models tests removed - testing dead code
    # test_analyze_games_queries_upcoming removed - complex mock issues, covered by integration tests
    # test_get_week_start_monday removed - _get_week_start moved to BankrollManager
    # test_min_bet_size_enforced removed - redundant with test_bankroll_manager.py
    # test_max_bet_size_enforced removed - redundant with test_bankroll_manager.py


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
