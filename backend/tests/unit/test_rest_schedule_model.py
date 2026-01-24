import unittest
from unittest.mock import Mock, MagicMock
from ml.models import RestScheduleModel


class TestRestScheduleModel(unittest.TestCase):
    def setUp(self):
        self.mock_table = Mock()
        self.model = RestScheduleModel(dynamodb_table=self.mock_table)
        self.game_info = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-01-24T00:00:00Z",
        }

    def test_well_rested_home_team(self):
        """Test well-rested home team advantage"""
        self.mock_table.query = MagicMock(
            side_effect=[
                {"Items": [{"rest_days": 3, "is_home": True}]},  # Home: 3 days rest
                {"Items": [{"rest_days": 1, "is_home": False}]},  # Away: 1 day rest
            ]
        )

        odds_items = []
        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "rest_schedule")
        self.assertEqual(result.prediction, "Lakers")
        self.assertGreater(result.confidence, 0.5)

    def test_back_to_back_penalty(self):
        """Test back-to-back game penalty"""
        self.mock_table.query = MagicMock(
            side_effect=[
                {"Items": [{"rest_days": 0, "is_home": True}]},  # Home: back-to-back
                {"Items": [{"rest_days": 2, "is_home": False}]},  # Away: normal rest
            ]
        )

        odds_items = []
        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.prediction, "Warriors")
        self.assertLess(result.confidence, 0.5)

    def test_home_advantage(self):
        """Test home court advantage"""
        self.mock_table.query = MagicMock(
            side_effect=[
                {
                    "Items": [{"rest_days": 2, "is_home": True}]
                },  # Home: normal rest at home
                {
                    "Items": [{"rest_days": 2, "is_home": False}]
                },  # Away: normal rest on road
            ]
        )

        odds_items = []
        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.prediction, "Lakers")

    def test_no_schedule_data(self):
        """Test neutral prediction when no schedule data"""
        self.mock_table.query = MagicMock(side_effect=[{"Items": []}, {"Items": []}])

        odds_items = []
        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result.confidence, 0.5, delta=0.1)

    def test_prop_analysis_well_rested(self):
        """Test prop analysis for well-rested team"""
        self.mock_table.query = MagicMock(
            side_effect=[
                {"Items": [{"team": "Lakers"}]},  # Player team lookup
                {"Items": [{"rest_days": 3, "is_home": True}]},  # Team rest
            ]
        )

        prop_item = {
            "sport": "basketball_nba",
            "player_name": "LeBron James",
            "market_key": "player_points",
            "line": 25.5,
            "game_id": "game123",
            "commence_time": "2026-01-24T00:00:00Z",
        }

        result = self.model.analyze_prop_odds(prop_item)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "rest_schedule")
        self.assertEqual(result.prediction, "over")

    def test_prop_analysis_fatigued(self):
        """Test prop analysis for fatigued team"""
        self.mock_table.query = MagicMock(
            side_effect=[
                {"Items": [{"team": "Lakers"}]},
                {"Items": [{"rest_days": 0, "is_home": False}]},  # Back-to-back on road
            ]
        )

        prop_item = {
            "sport": "basketball_nba",
            "player_name": "LeBron James",
            "market_key": "player_points",
            "line": 25.5,
            "game_id": "game123",
            "commence_time": "2026-01-24T00:00:00Z",
        }

        result = self.model.analyze_prop_odds(prop_item)

        self.assertIsNotNone(result)
        self.assertEqual(result.prediction, "under")


if __name__ == "__main__":
    unittest.main()
