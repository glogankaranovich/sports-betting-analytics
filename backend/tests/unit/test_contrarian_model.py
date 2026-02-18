import unittest

from ml.models import ContrarianModel


class TestContrarianModel(unittest.TestCase):
    def setUp(self):
        self.model = ContrarianModel()
        self.game_info = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-01-24T00:00:00Z",
        }

    def test_strong_line_movement_up(self):
        """Test strong upward line movement (sharp action on away)"""
        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -5.0, "price": -110},
                    {"name": "Warriors", "point": 5.0, "price": -110},
                ],
                "updated_at": "2026-01-23T10:00:00Z",
            },
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -3.5, "price": -110},
                    {"name": "Warriors", "point": 3.5, "price": -110},
                ],
                "updated_at": "2026-01-23T12:00:00Z",
            },
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Warriors", result.prediction)
        self.assertGreaterEqual(result.confidence, 0.65)
        self.assertIn("Big money", result.reasoning)

    def test_strong_line_movement_down(self):
        """Test strong downward line movement (sharp action on home)"""
        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -3.0, "price": -110},
                    {"name": "Warriors", "point": 3.0, "price": -110},
                ],
                "updated_at": "2026-01-23T10:00:00Z",
            },
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -4.5, "price": -110},
                    {"name": "Warriors", "point": 4.5, "price": -110},
                ],
                "updated_at": "2026-01-23T12:00:00Z",
            },
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Lakers", result.prediction)
        self.assertGreaterEqual(result.confidence, 0.65)

    def test_odds_imbalance_home_sharp(self):
        """Test odds imbalance indicating sharp money on home"""
        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -5.0, "price": -120},
                    {"name": "Warriors", "point": 5.0, "price": -100},
                ],
                "updated_at": "2026-01-23T10:00:00Z",
            }
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Lakers", result.prediction)
        self.assertIn("uneven odds", result.reasoning.lower())

    def test_odds_imbalance_away_sharp(self):
        """Test odds imbalance indicating sharp money on away"""
        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -5.0, "price": -100},
                    {"name": "Warriors", "point": 5.0, "price": -120},
                ],
                "updated_at": "2026-01-23T10:00:00Z",
            }
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Warriors", result.prediction)
        self.assertIn("uneven odds", result.reasoning.lower())

    def test_fade_favorite_home(self):
        """Test fading home favorite when no clear signal"""
        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": -5.0, "price": -110},
                    {"name": "Warriors", "point": 5.0, "price": -110},
                ],
                "updated_at": "2026-01-23T10:00:00Z",
            }
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Warriors", result.prediction)  # Fade home favorite
        self.assertIn("Betting against the favorite", result.reasoning)

    def test_fade_favorite_away(self):
        """Test fading away favorite when no clear signal"""
        odds_items = [
            {
                "sk": "spreads#fanduel",
                "outcomes": [
                    {"name": "Lakers", "point": 3.0, "price": -110},
                    {"name": "Warriors", "point": -3.0, "price": -110},
                ],
                "updated_at": "2026-01-23T10:00:00Z",
            }
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Lakers", result.prediction)  # Fade away favorite

    def test_prop_odds_imbalance_over(self):
        """Test prop with odds imbalance favoring over"""
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
                {"name": "Over", "price": -125},
                {"name": "Under", "price": -105},
            ],
        }

        result = self.model.analyze_prop_odds(prop_item)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Over", result.prediction)
        self.assertIn("Big money", result.reasoning)

    def test_prop_odds_imbalance_under(self):
        """Test prop with odds imbalance favoring under"""
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
                {"name": "Over", "price": -105},
                {"name": "Under", "price": -125},
            ],
        }

        result = self.model.analyze_prop_odds(prop_item)

        self.assertIsNotNone(result)
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Under", result.prediction)

    def test_prop_fade_public(self):
        """Test prop fading public when no clear signal"""
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
        self.assertEqual(result.model, "contrarian")
        self.assertIn("Under", result.prediction)  # Fade public (overs)
        self.assertIn("Going against the crowd", result.reasoning)

    def test_no_spreads_returns_none(self):
        """Test that missing spreads returns None"""
        odds_items = [
            {
                "sk": "h2h#fanduel",
                "outcomes": [
                    {"name": "Lakers", "price": -150},
                    {"name": "Warriors", "price": 130},
                ],
            }
        ]

        result = self.model.analyze_game_odds("game123", odds_items, self.game_info)

        self.assertIsNone(result)

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
