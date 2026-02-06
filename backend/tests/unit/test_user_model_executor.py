"""
Unit tests for user model executor
"""
import unittest
from unittest.mock import Mock, patch
from user_model_executor import (
    calculate_prediction,
    evaluate_team_stats,
    evaluate_odds_movement,
    evaluate_recent_form,
    evaluate_rest_schedule,
    evaluate_head_to_head,
    process_model,
)
from user_models import UserModel


class TestDataSourceEvaluators(unittest.TestCase):
    def setUp(self):
        self.game_data = {
            "game_id": "game123",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-02-04T19:00:00Z",
        }

    def test_evaluate_team_stats(self):
        """Test team stats evaluator returns normalized score"""
        score = evaluate_team_stats(self.game_data)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    def test_evaluate_odds_movement(self):
        """Test odds movement evaluator returns normalized score"""
        score = evaluate_odds_movement(self.game_data)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    @patch("user_model_executor.bets_table")
    def test_evaluate_odds_movement_sharp_on_home(self, mock_table):
        """Test odds movement with sharp action on home team"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "sk": "fanduel#h2h#2025-01-01T00:00:00",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "outcomes": [
                        {"name": "Lakers", "price": -110},
                        {"name": "Warriors", "price": -110},
                    ],
                },
                {
                    "sk": "fanduel#h2h#LATEST",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "outcomes": [
                        {"name": "Lakers", "price": -140},  # Line moved toward home
                        {"name": "Warriors", "price": 120},
                    ],
                },
            ]
        }
        score = evaluate_odds_movement(self.game_data)
        self.assertGreater(score, 0.5)  # Favors home

    @patch("user_model_executor.bets_table")
    def test_evaluate_odds_movement_sharp_on_away(self, mock_table):
        """Test odds movement with sharp action on away team"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "sk": "fanduel#h2h#2025-01-01T00:00:00",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "outcomes": [
                        {"name": "Lakers", "price": -110},
                        {"name": "Warriors", "price": -110},
                    ],
                },
                {
                    "sk": "fanduel#h2h#LATEST",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "outcomes": [
                        {"name": "Lakers", "price": 120},  # Line moved away from home
                        {"name": "Warriors", "price": -140},
                    ],
                },
            ]
        }
        score = evaluate_odds_movement(self.game_data)
        self.assertLess(score, 0.5)  # Favors away

    @patch("user_model_executor.bets_table")
    def test_evaluate_odds_movement_no_movement(self, mock_table):
        """Test odds movement with no significant line movement"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "sk": "fanduel#h2h#2025-01-01T00:00:00",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "outcomes": [
                        {"name": "Lakers", "price": -110},
                        {"name": "Warriors", "price": -110},
                    ],
                },
                {
                    "sk": "fanduel#h2h#LATEST",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "outcomes": [
                        {"name": "Lakers", "price": -115},  # Small movement
                        {"name": "Warriors", "price": -105},
                    ],
                },
            ]
        }
        score = evaluate_odds_movement(self.game_data)
        self.assertEqual(score, 0.5)  # Neutral

    @patch("user_model_executor.bets_table")
    def test_evaluate_odds_movement_no_data(self, mock_table):
        """Test odds movement with no historical data"""
        mock_table.query.return_value = {"Items": []}
        score = evaluate_odds_movement(self.game_data)
        self.assertEqual(score, 0.5)

    @patch("user_model_executor.bets_table")
    def test_evaluate_odds_movement_error(self, mock_table):
        """Test odds movement handles errors gracefully"""
        mock_table.query.side_effect = Exception("DynamoDB error")
        score = evaluate_odds_movement(self.game_data)
        self.assertEqual(score, 0.5)

    def test_evaluate_recent_form(self):
        """Test recent form evaluator returns normalized score"""
        score = evaluate_recent_form(self.game_data)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    @patch("user_model_executor.bets_table")
    def test_evaluate_recent_form_home_hot(self, mock_table):
        """Test recent form with home team on hot streak"""
        mock_table.query.side_effect = [
            {
                "Items": [
                    {
                        "home_team": "Lakers",
                        "away_team": "Suns",
                        "home_score": 110,
                        "away_score": 95,
                        "winner": "Lakers",
                    },
                    {
                        "home_team": "Lakers",
                        "away_team": "Kings",
                        "home_score": 105,
                        "away_score": 100,
                        "winner": "Lakers",
                    },
                    {
                        "home_team": "Clippers",
                        "away_team": "Lakers",
                        "home_score": 98,
                        "away_score": 102,
                        "winner": "Lakers",
                    },
                ]
            },
            {
                "Items": [
                    {
                        "home_team": "Warriors",
                        "away_team": "Nuggets",
                        "home_score": 95,
                        "away_score": 105,
                        "winner": "Nuggets",
                    },
                    {
                        "home_team": "Warriors",
                        "away_team": "Celtics",
                        "home_score": 100,
                        "away_score": 110,
                        "winner": "Celtics",
                    },
                ]
            },
        ]
        score = evaluate_recent_form(self.game_data)
        self.assertGreater(score, 0.5)  # Favors hot home team

    @patch("user_model_executor.bets_table")
    def test_evaluate_recent_form_away_hot(self, mock_table):
        """Test recent form with away team on hot streak"""
        mock_table.query.side_effect = [
            {
                "Items": [
                    {
                        "home_team": "Lakers",
                        "away_team": "Suns",
                        "home_score": 95,
                        "away_score": 105,
                        "winner": "Suns",
                    },
                ]
            },
            {
                "Items": [
                    {
                        "home_team": "Warriors",
                        "away_team": "Nuggets",
                        "home_score": 100,
                        "away_score": 110,
                        "winner": "Nuggets",
                    },
                    {
                        "home_team": "Celtics",
                        "away_team": "Warriors",
                        "home_score": 95,
                        "away_score": 105,
                        "winner": "Warriors",
                    },
                    {
                        "home_team": "Heat",
                        "away_team": "Warriors",
                        "home_score": 98,
                        "away_score": 108,
                        "winner": "Warriors",
                    },
                ]
            },
        ]
        score = evaluate_recent_form(self.game_data)
        self.assertLess(score, 0.5)  # Favors hot away team

    @patch("user_model_executor.bets_table")
    def test_evaluate_recent_form_no_data(self, mock_table):
        """Test recent form with no historical data"""
        mock_table.query.return_value = {"Items": []}
        score = evaluate_recent_form(self.game_data)
        self.assertEqual(score, 0.5)

    @patch("user_model_executor.bets_table")
    def test_evaluate_recent_form_error(self, mock_table):
        """Test recent form handles errors gracefully"""
        mock_table.query.side_effect = Exception("DynamoDB error")
        score = evaluate_recent_form(self.game_data)
        self.assertEqual(score, 0.5)

    def test_evaluate_rest_schedule(self):
        """Test rest/schedule evaluator returns normalized score"""
        score = evaluate_rest_schedule(self.game_data)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    @patch("user_model_executor.bets_table")
    def test_evaluate_rest_schedule_home_rested(self, mock_table):
        """Test rest schedule with home team well-rested"""
        mock_table.query.side_effect = [
            {"Items": [{"completed_at": "2025-01-01T00:00:00Z"}]},  # 3 days ago
            {
                "Items": [
                    {"completed_at": "2025-01-03T00:00:00Z"}  # 1 day ago (back-to-back)
                ]
            },
        ]
        game_data = {
            **self.game_data,
            "commence_time": "2025-01-04T00:00:00Z",
        }
        score = evaluate_rest_schedule(game_data)
        self.assertGreater(score, 0.5)  # Favors rested home team

    @patch("user_model_executor.bets_table")
    def test_evaluate_rest_schedule_away_rested(self, mock_table):
        """Test rest schedule with away team well-rested"""
        mock_table.query.side_effect = [
            {"Items": [{"completed_at": "2025-01-03T00:00:00Z"}]},  # 1 day ago
            {"Items": [{"completed_at": "2025-01-01T00:00:00Z"}]},  # 3 days ago
        ]
        game_data = {
            **self.game_data,
            "commence_time": "2025-01-04T00:00:00Z",
        }
        score = evaluate_rest_schedule(game_data)
        self.assertLess(score, 0.5)  # Favors rested away team

    @patch("user_model_executor.bets_table")
    def test_evaluate_rest_schedule_no_data(self, mock_table):
        """Test rest schedule with no historical data"""
        mock_table.query.return_value = {"Items": []}
        score = evaluate_rest_schedule(self.game_data)
        self.assertEqual(score, 0.5)

    @patch("user_model_executor.bets_table")
    def test_evaluate_rest_schedule_error(self, mock_table):
        """Test rest schedule handles errors gracefully"""
        mock_table.query.side_effect = Exception("DynamoDB error")
        score = evaluate_rest_schedule(self.game_data)
        self.assertEqual(score, 0.5)

    def test_evaluate_head_to_head(self):
        """Test head-to-head evaluator returns normalized score"""
        score = evaluate_head_to_head(self.game_data)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    @patch("user_model_executor.bets_table")
    def test_evaluate_team_stats_with_data(self, mock_table):
        """Test team stats evaluator with real data"""
        # Mock DynamoDB responses
        mock_table.query.side_effect = [
            # Home team stats
            {
                "Items": [
                    {
                        "stats": {
                            "Field Goal %": "50",
                            "Three Point %": "40",
                            "Rebounds": "45",
                        }
                    }
                ]
            },
            # Away team stats
            {
                "Items": [
                    {
                        "stats": {
                            "Field Goal %": "45",
                            "Three Point %": "35",
                            "Rebounds": "40",
                        }
                    }
                ]
            },
        ]

        score = evaluate_team_stats(self.game_data)
        self.assertGreater(score, 0.5)  # Home team should be favored
        self.assertLess(score, 1.0)

    @patch("user_model_executor.bets_table")
    def test_evaluate_team_stats_no_data(self, mock_table):
        """Test team stats evaluator with no data returns neutral"""
        mock_table.query.return_value = {"Items": []}

        score = evaluate_team_stats(self.game_data)
        self.assertEqual(score, 0.5)  # Should return neutral

    @patch("user_model_executor.bets_table")
    def test_evaluate_team_stats_error_handling(self, mock_table):
        """Test team stats evaluator handles errors gracefully"""
        mock_table.query.side_effect = Exception("DynamoDB error")

        score = evaluate_team_stats(self.game_data)
        self.assertEqual(score, 0.5)  # Should fallback to neutral


class TestCalculatePrediction(unittest.TestCase):
    def setUp(self):
        self.model = UserModel(
            user_id="user123",
            name="Test Model",
            description="Test model for unit testing",
            sport="basketball_nba",
            bet_types=["h2h"],
            data_sources={
                "team_stats": {"enabled": True, "weight": 0.6},
                "odds_movement": {"enabled": True, "weight": 0.4},
            },
            min_confidence=0.6,
        )

        self.game_data = {
            "game_id": "game123",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-02-04T19:00:00Z",
        }

    def test_calculate_prediction_above_threshold(self):
        """Test prediction is generated when above confidence threshold"""
        result = calculate_prediction(self.model, self.game_data)

        # With placeholder evaluators returning 0.5, weighted average is 0.5
        # This is below our 0.6 threshold, so should return None
        self.assertIsNone(result)

    def test_calculate_prediction_weights_applied(self):
        """Test that weights are properly applied"""
        # Mock evaluators to return specific values
        with patch(
            "user_model_executor.DATA_SOURCE_EVALUATORS",
            {"team_stats": lambda x: 0.8, "odds_movement": lambda x: 0.6},
        ):
            result = calculate_prediction(self.model, self.game_data)

            # Expected: 0.8 * 0.6 + 0.6 * 0.4 = 0.48 + 0.24 = 0.72
            # This is above 0.6 threshold and > 0.55, so should predict home team
            self.assertIsNotNone(result)
            self.assertEqual(result["prediction"], "Lakers")
            self.assertAlmostEqual(result["confidence"], 0.72, places=2)

    def test_calculate_prediction_disabled_sources_ignored(self):
        """Test that disabled sources are not evaluated"""
        model = UserModel(
            user_id="user123",
            name="Test Model",
            description="Test model",
            sport="basketball_nba",
            bet_types=["h2h"],
            data_sources={
                "team_stats": {"enabled": True, "weight": 1.0},
                "odds_movement": {"enabled": False, "weight": 0.0},
            },
            min_confidence=0.5,
        )

        # Mock only team_stats evaluator
        with patch(
            "user_model_executor.DATA_SOURCE_EVALUATORS",
            {
                "team_stats": lambda x: 0.6,
                "odds_movement": lambda x: 0.9,  # Should not be called
            },
        ):
            result = calculate_prediction(model, self.game_data)

            # Should use only team_stats (0.6), which is above 0.5 threshold
            self.assertIsNotNone(result)
            self.assertEqual(result["confidence"], 0.6)

    def test_calculate_prediction_no_bet_on_close_games(self):
        """Test that no prediction is made when confidence is between 0.45-0.55"""
        with patch("user_model_executor.evaluate_team_stats", return_value=0.5):
            with patch("user_model_executor.evaluate_odds_movement", return_value=0.5):
                # Lower threshold to allow calculation
                self.model.min_confidence = 0.4
                result = calculate_prediction(self.model, self.game_data)

                # Confidence is 0.5, which is in the "no bet" zone
                self.assertIsNone(result)


class TestProcessModel(unittest.TestCase):
    @patch("user_model_executor.UserModel.get")
    @patch("user_model_executor.get_upcoming_games")
    @patch("user_model_executor.ModelPrediction")
    def test_process_model_creates_predictions(
        self, mock_prediction_class, mock_get_games, mock_get_model
    ):
        """Test that process_model creates predictions for upcoming games"""
        # Setup mock model
        mock_model = Mock()
        mock_model.model_id = "model123"
        mock_model.user_id = "user123"
        mock_model.sport = "basketball_nba"
        mock_model.bet_types = ["h2h"]
        mock_model.status = "active"
        mock_model.data_sources = {"team_stats": {"enabled": True, "weight": 1.0}}
        mock_model.min_confidence = 0.5
        mock_get_model.return_value = mock_model

        # Setup mock games
        mock_get_games.return_value = [
            {
                "game_id": "game1",
                "home_team": "Lakers",
                "away_team": "Warriors",
                "commence_time": "2026-02-04T19:00:00Z",
                "bet_type": "h2h",
            }
        ]

        # Mock prediction calculation to return valid result
        with patch("user_model_executor.calculate_prediction") as mock_calc:
            mock_calc.return_value = {
                "prediction": "Lakers",
                "confidence": 0.7,
                "reasoning": "Test reasoning",
            }

            # Mock prediction instance
            mock_pred_instance = Mock()
            mock_prediction_class.return_value = mock_pred_instance

            # Execute
            process_model("model123", "user123")

            # Verify prediction was created and saved
            mock_prediction_class.assert_called_once()
            mock_pred_instance.save.assert_called_once()

    @patch("user_model_executor.UserModel.get")
    def test_process_model_skips_inactive_models(self, mock_get_model):
        """Test that inactive models are skipped"""
        mock_model = Mock()
        mock_model.status = "archived"
        mock_get_model.return_value = mock_model

        # Should return early without processing
        process_model("model123", "user123")

        # No further processing should occur
        mock_get_model.assert_called_once()


class TestGetUpcomingGames(unittest.TestCase):
    @patch("user_model_executor.bets_table")
    def test_get_upcoming_games_returns_games(self, mock_table):
        """Test get_upcoming_games returns formatted game data"""
        from user_model_executor import get_upcoming_games

        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "game_id": "game123",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": "2026-02-10T19:00:00Z",
                }
            ]
        }

        games = get_upcoming_games("basketball_nba", ["h2h"])

        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["game_id"], "game123")
        self.assertEqual(games[0]["home_team"], "Lakers")

    @patch("user_model_executor.bets_table")
    def test_get_upcoming_games_deduplicates(self, mock_table):
        """Test get_upcoming_games removes duplicate games"""
        from user_model_executor import get_upcoming_games

        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "game_id": "game123",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": "2026-02-10T19:00:00Z",
                },
                {
                    "pk": "GAME#game123",  # Duplicate
                    "game_id": "game123",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": "2026-02-10T19:00:00Z",
                },
            ]
        }

        games = get_upcoming_games("basketball_nba", ["h2h"])

        self.assertEqual(len(games), 1)  # Should deduplicate

    @patch("user_model_executor.bets_table")
    def test_get_upcoming_games_empty(self, mock_table):
        """Test get_upcoming_games handles empty results"""
        from user_model_executor import get_upcoming_games

        mock_table.query.return_value = {"Items": []}

        games = get_upcoming_games("basketball_nba", ["h2h"])

        self.assertEqual(len(games), 0)


if __name__ == "__main__":
    unittest.main()
