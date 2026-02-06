import unittest
from unittest.mock import MagicMock, Mock

from ml.models import HotColdModel


class TestHotColdModel(unittest.TestCase):
    def setUp(self):
        # Mock DynamoDB table
        self.mock_table = Mock()
        self.model = HotColdModel(dynamodb_table=self.mock_table)
        self.game_info = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-01-24T00:00:00Z",
        }

    def test_strong_home_form(self):
        """Test strong home team form"""
        # Mock home team hot (8-2), away team cold (3-7)
        self.mock_table.query = MagicMock(
            side_effect=[
                {"Items": []},  # Home team query (will use default)
                {"Items": []},  # Away team query (will use default)
            ]
        )

        # Override _get_recent_record to return specific records
        self.model._get_recent_record = Mock(
            side_effect=[
                {"wins": 8, "losses": 2, "games": 10},  # Home
                {"wins": 3, "losses": 7, "games": 10},  # Away
            ]
        )

        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -5.0, "price": -110},
                    {"name": "Warriors", "point": 5.0, "price": -110},
                ],
            }
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "hot_cold")
        self.assertIn("Lakers", result.prediction)
        self.assertGreaterEqual(result.confidence, 0.65)
        self.assertIn("8-2", result.reasoning)

    def test_strong_away_form(self):
        """Test strong away team form"""
        self.model._get_recent_record = Mock(
            side_effect=[
                {"wins": 3, "losses": 7, "games": 10},  # Home
                {"wins": 8, "losses": 2, "games": 10},  # Away
            ]
        )

        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -5.0, "price": -110},
                    {"name": "Warriors", "point": 5.0, "price": -110},
                ],
            }
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "hot_cold")
        self.assertIn("Warriors", result.prediction)
        self.assertGreaterEqual(result.confidence, 0.65)

    def test_similar_form(self):
        """Test similar form for both teams"""
        self.model._get_recent_record = Mock(
            side_effect=[
                {"wins": 5, "losses": 5, "games": 10},  # Home
                {"wins": 5, "losses": 5, "games": 10},  # Away
            ]
        )

        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -3.0, "price": -110},
                    {"name": "Warriors", "point": 3.0, "price": -110},
                ],
            }
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "hot_cold")
        self.assertIn("Lakers", result.prediction)  # Slight home edge
        self.assertLessEqual(result.confidence, 0.60)

    def test_prop_hot_player(self):
        """Test prop with hot player (averaging well above line)"""
        self.model._get_recent_player_stats = Mock(
            return_value={"games": 10, "average": 28.5, "over_count": 8}
        )

        prop_item = {
            "event_id": "game123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-01-24T00:00:00Z",
            "player_name": "LeBron James",
            "market_key": "player_points",
            "point": 25.5,
            "outcomes": [
                {"name": "Over", "price": -110},
                {"name": "Under", "price": -110},
            ],
        }

        result = self.model.analyze_prop_odds(prop_item)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "hot_cold")
        self.assertIn("Over", result.prediction)
        self.assertGreaterEqual(result.confidence, 0.65)
        self.assertIn("28.5", result.reasoning)

    def test_prop_cold_player(self):
        """Test prop with cold player (averaging well below line)"""
        self.model._get_recent_player_stats = Mock(
            return_value={"games": 10, "average": 18.2, "over_count": 2}
        )

        prop_item = {
            "event_id": "game123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-01-24T00:00:00Z",
            "player_name": "LeBron James",
            "market_key": "player_points",
            "point": 25.5,
            "outcomes": [
                {"name": "Over", "price": -110},
                {"name": "Under", "price": -110},
            ],
        }

        result = self.model.analyze_prop_odds(prop_item)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "hot_cold")
        self.assertIn("Under", result.prediction)
        self.assertGreaterEqual(result.confidence, 0.65)

    def test_prop_no_data(self):
        """Test prop with no historical data"""
        self.model._get_recent_player_stats = Mock(
            return_value={"games": 0, "average": 0, "over_count": 0}
        )

        prop_item = {
            "event_id": "game123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-01-24T00:00:00Z",
            "player_name": "LeBron James",
            "market_key": "player_points",
            "point": 25.5,
            "outcomes": [
                {"name": "Over", "price": -110},
                {"name": "Under", "price": -110},
            ],
        }

        result = self.model.analyze_prop_odds(prop_item)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "hot_cold")
        self.assertIn("Insufficient data", result.reasoning)
        self.assertLessEqual(result.confidence, 0.60)

    def test_calculate_form_score_hot(self):
        """Test form score calculation for hot team"""
        record = {"wins": 8, "losses": 2, "games": 10}
        score = self.model._calculate_form_score(record)
        self.assertGreater(score, 0.8)  # Should be boosted

    def test_calculate_form_score_cold(self):
        """Test form score calculation for cold team"""
        record = {"wins": 2, "losses": 8, "games": 10}
        score = self.model._calculate_form_score(record)
        self.assertLess(score, 0.3)  # Should be reduced

    def test_calculate_form_score_neutral(self):
        """Test form score calculation for neutral team"""
        record = {"wins": 5, "losses": 5, "games": 10}
        score = self.model._calculate_form_score(record)
        self.assertAlmostEqual(score, 0.5, places=1)

    def test_map_market_to_stat(self):
        """Test market key to stat field mapping"""
        self.assertEqual(self.model._map_market_to_stat("player_points"), "PTS")
        self.assertEqual(self.model._map_market_to_stat("player_rebounds"), "REB")
        self.assertEqual(self.model._map_market_to_stat("player_assists"), "AST")
        self.assertEqual(self.model._map_market_to_stat("player_threes"), "3PM")
        self.assertEqual(self.model._map_market_to_stat("unknown"), "PTS")  # Default

    def test_get_current_spread(self):
        """Test extracting current spread from odds items"""
        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -7.5, "price": -110},
                    {"name": "Warriors", "point": 7.5, "price": -110},
                ],
            }
        ]
        spread = self.model._get_current_spread(odds_items)
        self.assertEqual(spread, -7.5)

    def test_get_current_spread_no_spreads(self):
        """Test spread extraction with no spreads available"""
        odds_items = [
            {
                "sk": "h2h#fanduel",
                "outcomes": [
                    {"name": "Lakers", "price": -150},
                    {"name": "Warriors", "price": 130},
                ],
            }
        ]
        spread = self.model._get_current_spread(odds_items)
        self.assertEqual(spread, 0.0)

    def test_invalid_prop_returns_none(self):
        """Test that invalid prop data returns None"""
        prop_item = {
            "event_id": "game123",
            "outcomes": [{"name": "Over", "price": -110}],  # Missing Under
        }

        result = self.model.analyze_prop_odds(prop_item)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
