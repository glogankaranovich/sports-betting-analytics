"""
Unit tests for backtesting engine
"""
from unittest.mock import MagicMock, patch

import pytest

from backtest_engine import BacktestEngine


@pytest.fixture
def mock_bets_table():
    with patch("backtest_engine.bets_table") as mock:
        yield mock


@pytest.fixture
def mock_user_models_table():
    with patch("backtest_engine.user_models_table") as mock:
        yield mock


@pytest.fixture
def engine():
    return BacktestEngine()


class TestBacktestEngine:
    def test_calculate_metrics_perfect_accuracy(self, engine):
        """Test metrics calculation with 100% accuracy"""
        predictions = [
            {"correct": True, "confidence": 0.8},
            {"correct": True, "confidence": 0.7},
            {"correct": True, "confidence": 0.9},
        ]

        metrics = engine._calculate_metrics(predictions)

        assert metrics["accuracy"] == 1.0
        assert metrics["total_predictions"] == 3
        assert metrics["correct_predictions"] == 3
        assert metrics["roi"] > 0  # Positive ROI
        assert 0.7 <= metrics["avg_confidence"] <= 0.9

    def test_calculate_metrics_zero_accuracy(self, engine):
        """Test metrics calculation with 0% accuracy"""
        predictions = [
            {"correct": False, "confidence": 0.6},
            {"correct": False, "confidence": 0.5},
        ]

        metrics = engine._calculate_metrics(predictions)

        assert metrics["accuracy"] == 0.0
        assert metrics["total_predictions"] == 2
        assert metrics["correct_predictions"] == 0
        assert metrics["roi"] < 0  # Negative ROI

    def test_calculate_metrics_empty(self, engine):
        """Test metrics with no predictions"""
        metrics = engine._calculate_metrics([])

        assert metrics["accuracy"] == 0
        assert metrics["total_predictions"] == 0
        assert metrics["roi"] == 0

    def test_evaluate_game_home_win(self, engine):
        """Test game evaluation predicting home win"""
        game = {
            "game_id": "test123",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "sport": "basketball_nba",
            "commence_time": "2024-01-01T19:00:00Z",
            "outcome": {"winner": "Lakers"},
        }

        model_config = {
            "data_sources": {
                "team_stats": {"enabled": True, "weight": 0.5},
                "recent_form": {"enabled": True, "weight": 0.5},
            }
        }

        engine.evaluators["team_stats"] = MagicMock(return_value=0.6)
        engine.evaluators["recent_form"] = MagicMock(return_value=0.4)
        result = engine._evaluate_game(game, model_config)

        assert result is not None
        assert result["prediction"] == "Lakers"
        assert result["correct"] is True
        assert result["confidence"] > 0

    def test_evaluate_game_away_win(self, engine):
        """Test game evaluation predicting away win"""
        game = {
            "game_id": "test456",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "sport": "basketball_nba",
            "commence_time": "2024-01-01T19:00:00Z",
            "outcome": {"winner": "Warriors"},
        }

        model_config = {
            "data_sources": {
                "team_stats": {"enabled": True, "weight": 1.0},
            }
        }

        # Mock the evaluator function in the engine's evaluators dict
        engine.evaluators["team_stats"] = MagicMock(return_value=-0.7)
        result = engine._evaluate_game(game, model_config)

        assert result is not None
        assert result["prediction"] == "Warriors"
        assert result["correct"] is True

    def test_store_backtest(self, engine, mock_user_models_table):
        """Test storing backtest results"""
        result = {
            "backtest_id": "bt123",
            "user_id": "user123",
            "model_id": "model123",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "total_predictions": 10,
            "metrics": {"accuracy": 0.6},
            "predictions": [],
            "created_at": "2024-01-31T12:00:00Z",
        }

        engine._store_backtest(result)

        mock_user_models_table.put_item.assert_called_once()
        call_args = mock_user_models_table.put_item.call_args[1]
        assert call_args["Item"]["PK"] == "USER#user123"
        assert call_args["Item"]["SK"] == "BACKTEST#bt123"

    def test_get_backtest(self, mock_user_models_table):
        """Test retrieving backtest"""
        mock_user_models_table.get_item.return_value = {
            "Item": {"backtest_id": "bt123", "metrics": {"accuracy": 0.7}}
        }

        result = BacktestEngine.get_backtest("user123", "bt123")

        assert result["backtest_id"] == "bt123"
        mock_user_models_table.get_item.assert_called_once_with(
            Key={"PK": "USER#user123", "SK": "BACKTEST#bt123"}
        )

    def test_list_backtests(self, mock_user_models_table):
        """Test listing backtests for a model"""
        mock_user_models_table.query.return_value = {
            "Items": [
                {"backtest_id": "bt1"},
                {"backtest_id": "bt2"},
            ]
        }

        results = BacktestEngine.list_backtests("model123")

        assert len(results) == 2
        mock_user_models_table.query.assert_called_once()
