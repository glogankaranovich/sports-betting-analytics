"""Unit tests for OutcomeAnalyzer"""
import unittest
from unittest.mock import Mock, MagicMock
from benny.outcome_analyzer import OutcomeAnalyzer


class TestOutcomeAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.mock_table = Mock()
        self.analyzer = OutcomeAnalyzer(self.mock_table, "BENNY_V2")
    
    def test_analyze_numeric_feature(self):
        """Test numeric feature analysis"""
        bets = [
            {"features": {"elo_diff": 120}, "result": "win"},
            {"features": {"elo_diff": 80}, "result": "win"},
            {"features": {"elo_diff": 30}, "result": "loss"},
            {"features": {"elo_diff": -20}, "result": "loss"},
            {"features": {"elo_diff": -80}, "result": "loss"},
        ]
        
        bins = [(50, 150), (0, 50), (-50, 0), (-150, -50)]
        result = self.analyzer._analyze_numeric_feature(bets, "elo_diff", bins)
        
        # High elo_diff (50-150): 2 bets, 2 wins = 100%
        self.assertEqual(result["50_to_150"]["count"], 2)
        self.assertEqual(result["50_to_150"]["wins"], 2)
        self.assertEqual(result["50_to_150"]["win_rate"], 1.0)
        
        # Low elo_diff (0-50): 1 bet, 0 wins = 0%
        self.assertEqual(result["0_to_50"]["count"], 1)
        self.assertEqual(result["0_to_50"]["wins"], 0)
        self.assertEqual(result["0_to_50"]["win_rate"], 0.0)
    
    def test_analyze_categorical_feature(self):
        """Test categorical feature analysis"""
        bets = [
            {"features": {"is_home": True}, "result": "win"},
            {"features": {"is_home": True}, "result": "win"},
            {"features": {"is_home": True}, "result": "loss"},
            {"features": {"is_home": False}, "result": "loss"},
            {"features": {"is_home": False}, "result": "loss"},
        ]
        
        result = self.analyzer._analyze_categorical_feature(bets, "is_home")
        
        # Home bets: 3 total, 2 wins = 66.7%
        self.assertEqual(result["True"]["count"], 3)
        self.assertEqual(result["True"]["wins"], 2)
        self.assertAlmostEqual(result["True"]["win_rate"], 0.667, places=2)
        
        # Away bets: 2 total, 0 wins = 0%
        self.assertEqual(result["False"]["count"], 2)
        self.assertEqual(result["False"]["wins"], 0)
        self.assertEqual(result["False"]["win_rate"], 0.0)
    
    def test_rank_features(self):
        """Test feature ranking by predictive power"""
        insights = {
            "elo_diff": {
                "high": {"count": 10, "wins": 8, "win_rate": 0.8},
                "low": {"count": 10, "wins": 2, "win_rate": 0.2}
            },
            "fatigue": {
                "fresh": {"count": 10, "wins": 6, "win_rate": 0.6},
                "tired": {"count": 10, "wins": 4, "win_rate": 0.4}
            }
        }
        
        rankings = self.analyzer._rank_features(insights)
        
        # elo_diff should rank higher (60% spread vs 20% spread)
        self.assertEqual(rankings[0]["feature"], "elo_diff")
        self.assertAlmostEqual(rankings[0]["spread"], 0.6, places=5)
        self.assertEqual(rankings[1]["feature"], "fatigue")
        self.assertAlmostEqual(rankings[1]["spread"], 0.2, places=5)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        self.mock_table.query.return_value = {"Items": []}
        
        result = self.analyzer.analyze_features()
        
        self.assertIn("error", result)
        self.assertEqual(result["bet_count"], 0)


if __name__ == '__main__':
    unittest.main()
