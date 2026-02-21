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
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        trader = BennyTrader()
        assert trader.bankroll == Decimal("100.00")

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_weekly_bankroll_reset(self, mock_bedrock, mock_table):
        """Test bankroll resets weekly"""
        last_week = (datetime.utcnow() - timedelta(days=8)).isoformat()
        mock_table.get_item.return_value = {
            "Item": {"amount": Decimal("50.00"), "last_reset": last_week}
        }
        
        trader = BennyTrader()
        assert trader.bankroll == Decimal("100.00")
        mock_table.put_item.assert_called()

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_calculate_bet_size_kelly_criterion(self, mock_bedrock, mock_table):
        """Test Kelly criterion bet sizing"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        trader = BennyTrader()
        
        # High confidence should bet more
        high_bet = trader.calculate_bet_size(0.85)
        low_bet = trader.calculate_bet_size(0.55)
        
        assert high_bet > low_bet
        assert high_bet <= trader.bankroll * Decimal("0.20")  # Max 20%
        assert low_bet >= Decimal("5.00")  # Min bet

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_normalize_prediction_spreads(self, mock_bedrock, mock_table):
        """Test prediction normalization for spreads"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        trader = BennyTrader()
        
        # Test spread normalization
        assert trader._normalize_prediction("Patriots +5.0") == "Patriots spread"
        assert trader._normalize_prediction("Lakers -3.5 @ draftkings") == "Lakers spread"

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_normalize_prediction_totals(self, mock_bedrock, mock_table):
        """Test prediction normalization for totals"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        trader = BennyTrader()
        
        assert trader._normalize_prediction("Over 220.5") == "Over"
        assert trader._normalize_prediction("Under 45.5") == "Under"

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_normalize_prediction_moneyline(self, mock_bedrock, mock_table):
        """Test prediction normalization for moneyline"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        trader = BennyTrader()
        
        assert trader._normalize_prediction("Lakers") == "Lakers"
        assert trader._normalize_prediction("Warriors") == "Warriors"

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_get_top_models_by_accuracy(self, mock_bedrock, mock_table):
        """Test getting top performing models"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        # Mock verified predictions query
        mock_table.query.return_value = {
            "Items": [
                {"model": "consensus", "analysis_correct": True},
                {"model": "consensus", "analysis_correct": True},
                {"model": "value", "analysis_correct": False},
            ]
        }
        
        trader = BennyTrader()
        top_models = trader._get_top_models(sport="basketball_nba", limit=3)
        
        assert isinstance(top_models, list)
        assert len(top_models) <= 3

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_get_top_models_fallback(self, mock_bedrock, mock_table):
        """Test fallback to default models"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        # Mock empty predictions
        mock_table.query.return_value = {"Items": []}
        
        trader = BennyTrader()
        top_models = trader._get_top_models(sport="basketball_nba", limit=3)
        
        # Should return default models
        assert len(top_models) == 3
        assert "ensemble" in top_models or "consensus" in top_models

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_analyze_games_queries_upcoming(self, mock_bedrock, mock_table):
        """Test analyze_games queries upcoming games"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        # Mock games query
        mock_table.query.return_value = {"Items": []}
        
        trader = BennyTrader()
        trader._get_team_stats = MagicMock(return_value={})
        trader._get_team_injuries = MagicMock(return_value=[])
        trader._get_head_to_head = MagicMock(return_value=[])
        trader._get_recent_form = MagicMock(return_value=[])
        trader._ai_analyze_game = MagicMock(return_value=None)
        
        opportunities = trader.analyze_games()
        
        assert isinstance(opportunities, list)

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_get_week_start_monday(self, mock_bedrock, mock_table):
        """Test week start is Monday"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        trader = BennyTrader()
        week_start = trader._get_week_start()
        
        # Parse and check it's a Monday
        dt = datetime.fromisoformat(week_start)
        assert dt.weekday() == 0  # Monday

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_min_bet_size_enforced(self, mock_bedrock, mock_table):
        """Test minimum bet size is enforced"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("100.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        trader = BennyTrader()
        
        # Very low confidence should still meet minimum
        bet_size = trader.calculate_bet_size(0.50)
        assert bet_size >= Decimal("5.00")

    @patch("benny_trader.table")
    @patch("benny_trader.bedrock")
    def test_max_bet_size_enforced(self, mock_bedrock, mock_table):
        """Test maximum bet size is enforced"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("1000.00"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }
        
        trader = BennyTrader()
        
        # Very high confidence should not exceed 20%
        bet_size = trader.calculate_bet_size(0.95)
        assert bet_size <= Decimal("200.00")  # 20% of 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
