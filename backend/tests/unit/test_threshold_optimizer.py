"""Unit tests for ThresholdOptimizer"""
import unittest
from unittest.mock import Mock
from decimal import Decimal
from benny.threshold_optimizer import ThresholdOptimizer


class TestThresholdOptimizer(unittest.TestCase):
    
    def setUp(self):
        self.mock_table = Mock()
        self.optimizer = ThresholdOptimizer(self.mock_table, "BENNY_V2")
    
    def test_find_optimal_thresholds(self):
        """Test finding optimal thresholds for a set of bets"""
        bets = []
        # Create clear pattern: high confidence = wins, low confidence = losses
        for i in range(10):
            if i < 5:
                # High confidence winners
                bets.append({
                    "confidence": Decimal("0.80"),
                    "bet_amount": Decimal("10"),
                    "profit": Decimal("5"),
                    "result": "win"
                })
            else:
                # Low confidence losers
                bets.append({
                    "confidence": Decimal("0.65"),
                    "bet_amount": Decimal("10"),
                    "profit": Decimal("-10"),
                    "result": "loss"
                })
        
        result = self.optimizer._find_optimal_thresholds(bets)
        
        # Should find optimal threshold that filters out losing bets
        self.assertIn("optimal_min_confidence", result)
        self.assertIn("optimal_min_ev", result)
        self.assertIn("expected_roi", result)
        self.assertIn("expected_win_rate", result)
        self.assertIn("sample_size", result)
        self.assertGreater(result["sample_size"], 0)
    
    def test_optimize_thresholds_insufficient_data(self):
        """Test handling of insufficient data"""
        self.mock_table.query.return_value = {"Items": []}
        
        result = self.optimizer.optimize_thresholds()
        
        self.assertIn("error", result)
        self.assertEqual(result["bet_count"], 0)
    
    def test_optimize_thresholds_with_data(self):
        """Test optimization with sufficient data"""
        bets = []
        # Create 40 bets with varying confidence and outcomes
        for i in range(40):
            confidence = 0.65 + (i % 4) * 0.05  # 0.65, 0.70, 0.75, 0.80
            result = "win" if i % 3 != 0 else "loss"  # ~67% win rate
            profit = 5 if result == "win" else -10
            
            bets.append({
                "confidence": Decimal(str(confidence)),
                "bet_amount": Decimal("10"),
                "profit": Decimal(str(profit)),
                "result": result,
                "sport": "basketball_nba",
                "market_key": "h2h"
            })
        
        self.mock_table.query.return_value = {"Items": bets}
        
        result = self.optimizer.optimize_thresholds()
        
        self.assertNotIn("error", result)
        self.assertEqual(result["total_bets"], 40)
        self.assertIn("global", result)
        self.assertIn("by_sport", result)
        self.assertIn("by_market", result)
        
        # Check global optimal
        self.assertIn("optimal_min_confidence", result["global"])
        self.assertIn("optimal_min_ev", result["global"])
        self.assertIn("expected_roi", result["global"])
    
    def test_save_optimal_thresholds(self):
        """Test saving thresholds to DynamoDB"""
        thresholds = {
            "global": {"optimal_min_confidence": 0.75},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        self.optimizer.save_optimal_thresholds(thresholds)
        
        self.mock_table.put_item.assert_called_once()
        call_args = self.mock_table.put_item.call_args[1]["Item"]
        self.assertEqual(call_args["pk"], "BENNY_V2#LEARNING")
        self.assertEqual(call_args["sk"], "THRESHOLDS")


if __name__ == '__main__':
    unittest.main()
