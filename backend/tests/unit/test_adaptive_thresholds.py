"""Tests for adaptive threshold logic"""
import unittest


class TestAdaptiveThresholdLogic(unittest.TestCase):
    """Test the adaptive threshold calculation logic"""
    
    MIN_SAMPLE_SIZE = 30
    BASE_MIN_CONFIDENCE = 0.70
    
    def calculate_threshold(self, sport_perf, market_perf):
        """Replicate the _get_adaptive_threshold logic"""
        sport_win_rate = None
        if sport_perf and sport_perf.get('total', 0) >= self.MIN_SAMPLE_SIZE:
            sport_win_rate = sport_perf['wins'] / sport_perf['total']
        
        market_win_rate = None
        if market_perf and market_perf.get('total', 0) >= self.MIN_SAMPLE_SIZE:
            market_win_rate = market_perf['wins'] / market_perf['total']
        
        if sport_win_rate is None and market_win_rate is None:
            return self.BASE_MIN_CONFIDENCE
        
        worst_win_rate = min(
            [r for r in [sport_win_rate, market_win_rate] if r is not None],
            default=0.50
        )
        
        if worst_win_rate < 0.35:
            return 0.80
        elif worst_win_rate < 0.45:
            return 0.75
        elif worst_win_rate > 0.55:
            return 0.65
        else:
            return 0.70
    
    def test_terrible_performance_requires_80_percent(self):
        """EPL with 31.6% win rate should require 80% confidence"""
        sport_perf = {'wins': 12, 'total': 38}  # 31.6%
        market_perf = {'wins': 74, 'total': 136}  # 54.4%
        threshold = self.calculate_threshold(sport_perf, market_perf)
        self.assertEqual(threshold, 0.80)
    
    def test_poor_performance_requires_75_percent(self):
        """Spreads with 40.6% win rate should require 75% confidence"""
        sport_perf = {'wins': 59, 'total': 111}  # 53.2%
        market_perf = {'wins': 28, 'total': 69}  # 40.6%
        threshold = self.calculate_threshold(sport_perf, market_perf)
        self.assertEqual(threshold, 0.75)
    
    def test_good_performance_allows_65_percent(self):
        """NHL with 58.2% win rate and good market should allow 65% confidence"""
        sport_perf = {'wins': 39, 'total': 67}  # 58.2%
        market_perf = {'wins': 80, 'total': 136}  # 58.8%
        threshold = self.calculate_threshold(sport_perf, market_perf)
        self.assertEqual(threshold, 0.65)
    
    def test_neutral_performance_uses_70_percent(self):
        """NBA with 53.2% win rate should use 70% confidence"""
        sport_perf = {'wins': 59, 'total': 111}  # 53.2%
        market_perf = {'wins': 74, 'total': 136}  # 54.4%
        threshold = self.calculate_threshold(sport_perf, market_perf)
        self.assertEqual(threshold, 0.70)
    
    def test_insufficient_data_uses_base_threshold(self):
        """New sport with <30 bets should use base threshold (70%)"""
        sport_perf = {'wins': 5, 'total': 10}  # 50% but < 30 bets
        market_perf = {'wins': 74, 'total': 136}  # 54.4%
        threshold = self.calculate_threshold(sport_perf, market_perf)
        self.assertEqual(threshold, 0.70)
    
    def test_uses_worst_performance(self):
        """Should use worst of sport/market performance"""
        sport_perf = {'wins': 59, 'total': 111}  # 53.2% (neutral)
        market_perf = {'wins': 28, 'total': 69}  # 40.6% (poor)
        threshold = self.calculate_threshold(sport_perf, market_perf)
        self.assertEqual(threshold, 0.75)  # Uses poor threshold
    
    def test_both_insufficient_data(self):
        """Both sport and market with <30 bets should use base threshold"""
        sport_perf = {'wins': 5, 'total': 10}
        market_perf = {'wins': 8, 'total': 15}
        threshold = self.calculate_threshold(sport_perf, market_perf)
        self.assertEqual(threshold, 0.70)


if __name__ == '__main__':
    unittest.main()
