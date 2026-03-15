"""Tests for adaptive threshold logic"""
import unittest
from unittest.mock import Mock
from benny.learning_engine import LearningEngine


class TestAdaptiveThresholdLogic(unittest.TestCase):
    """Test the adaptive threshold calculation logic"""

    def _make_engine(self, thresholds=None):
        mock_table = Mock()
        # First get_item call is for _load_parameters
        # Subsequent calls are for get_adaptive_threshold (THRESHOLDS lookup)
        if thresholds:
            mock_table.get_item.side_effect = [
                {"Item": {"performance_by_sport": {}, "performance_by_market": {}}},
                {"Item": {"thresholds": thresholds}},
            ]
        else:
            mock_table.get_item.return_value = {
                "Item": {"performance_by_sport": {}, "performance_by_market": {}}
            }
        return LearningEngine(mock_table)

    def test_game_market_h2h_requires_80(self):
        engine = self._make_engine()
        self.assertEqual(engine.get_adaptive_threshold("basketball_nba", "h2h"), 0.80)

    def test_game_market_spread_requires_80(self):
        engine = self._make_engine()
        self.assertEqual(engine.get_adaptive_threshold("icehockey_nhl", "spread"), 0.80)

    def test_game_market_totals_requires_80(self):
        engine = self._make_engine()
        self.assertEqual(engine.get_adaptive_threshold("basketball_nba", "totals"), 0.80)

    def test_prop_market_player_points_allows_65(self):
        engine = self._make_engine()
        self.assertEqual(
            engine.get_adaptive_threshold("basketball_nba", "player_points"), 0.65
        )

    def test_prop_market_player_rebounds_allows_65(self):
        engine = self._make_engine()
        self.assertEqual(
            engine.get_adaptive_threshold("basketball_nba", "player_rebounds"), 0.65
        )

    def test_prop_market_player_assists_allows_65(self):
        engine = self._make_engine()
        self.assertEqual(
            engine.get_adaptive_threshold("icehockey_nhl", "player_assists"), 0.65
        )

    def test_learned_sport_threshold_overrides_default(self):
        thresholds = {"by_sport": {"basketball_nba": {"optimal_min_confidence": 0.72}}}
        engine = self._make_engine(thresholds)
        self.assertEqual(engine.get_adaptive_threshold("basketball_nba", "h2h"), 0.72)

    def test_learned_market_threshold_overrides_default(self):
        thresholds = {"by_market": {"h2h": {"optimal_min_confidence": 0.78}}}
        engine = self._make_engine(thresholds)
        self.assertEqual(engine.get_adaptive_threshold("basketball_nba", "h2h"), 0.78)

    def test_learned_global_threshold_overrides_default(self):
        thresholds = {"global": {"optimal_min_confidence": 0.73}}
        engine = self._make_engine(thresholds)
        self.assertEqual(engine.get_adaptive_threshold("basketball_nba", "h2h"), 0.73)


if __name__ == "__main__":
    unittest.main()
