"""Unit tests for DynamicModelWeighting class."""
from decimal import Decimal
from unittest.mock import patch

import pytest

from ml.dynamic_weighting import DynamicModelWeighting


@pytest.fixture
def mock_table():
    """Mock DynamoDB table."""
    with patch("ml.dynamic_weighting.table") as mock:
        yield mock


def test_get_recent_accuracy_with_data(mock_table):
    """Test accuracy calculation with verified analyses."""
    # Mock verified analyses: 7 correct out of 10
    mock_table.query.return_value = {
        "Items": [
            {
                "model": "consensus",
                "sport": "basketball_nba",
                "analysis_type": "game",
                "analysis_correct": True,
            }
        ]
        * 7
        + [
            {
                "model": "consensus",
                "sport": "basketball_nba",
                "analysis_type": "game",
                "analysis_correct": False,
            }
        ]
        * 3
    }

    weighting = DynamicModelWeighting()
    accuracy = weighting.get_recent_accuracy("consensus", "basketball_nba", "game")

    assert accuracy == 0.7


def test_get_recent_accuracy_no_data(mock_table):
    """Test accuracy calculation with no verified analyses."""
    mock_table.query.return_value = {"Items": []}

    weighting = DynamicModelWeighting()
    accuracy = weighting.get_recent_accuracy("consensus", "basketball_nba", "game")

    assert accuracy is None


def test_get_recent_brier_score(mock_table):
    """Test Brier score calculation."""
    mock_table.query.return_value = {
        "Items": [
            {
                "model": "consensus",
                "sport": "basketball_nba",
                "analysis_type": "game",
                "confidence": Decimal("0.7"),
                "analysis_correct": True,
            },
            {
                "model": "consensus",
                "sport": "basketball_nba",
                "analysis_type": "game",
                "confidence": Decimal("0.6"),
                "analysis_correct": False,
            },
        ]
    }

    weighting = DynamicModelWeighting()
    brier = weighting.get_recent_brier_score("consensus", "basketball_nba", "game")

    # Brier = ((0.7-1)^2 + (0.6-0)^2) / 2 = (0.09 + 0.36) / 2 = 0.225
    assert abs(brier - 0.225) < 0.001


def test_calculate_adjusted_confidence_boost():
    """Test confidence boost for high-performing model."""
    weighting = DynamicModelWeighting()

    with patch.object(weighting, "get_recent_accuracy", return_value=0.7):
        adjusted = weighting.calculate_adjusted_confidence(
            0.6, "consensus", "basketball_nba", "game"
        )
        # 70% accuracy: multiplier = 1.0 + (0.7-0.6)*0.5 = 1.05
        # 0.6 * 1.05 = 0.63
        assert abs(adjusted - 0.63) < 0.01


def test_calculate_adjusted_confidence_reduce():
    """Test confidence reduction for underperforming model."""
    weighting = DynamicModelWeighting()

    # Mock both original and inverse accuracy calls
    def mock_accuracy(model, sport, bet_type, inverse=False):
        if inverse:
            return 0.4  # Inverse is worse
        return 0.5  # Original is 50%
    
    with patch.object(weighting, "get_recent_accuracy", side_effect=mock_accuracy):
        adjusted = weighting.calculate_adjusted_confidence(
            0.7, "consensus", "basketball_nba", "game"
        )
        # 50% accuracy: multiplier = 0.8 + (0.5-0.5)*2 = 0.8
        # 0.7 * 0.8 = 0.56
        assert abs(adjusted - 0.56) < 0.01


def test_calculate_adjusted_confidence_no_data():
    """Test confidence adjustment with no historical data."""
    weighting = DynamicModelWeighting()

    with patch.object(weighting, "get_recent_accuracy", return_value=None):
        adjusted = weighting.calculate_adjusted_confidence(
            0.65, "consensus", "basketball_nba", "game"
        )
        # No data: return base confidence
        assert adjusted == 0.65


def test_calculate_adjusted_confidence_capped():
    """Test confidence is capped at 1.0."""
    weighting = DynamicModelWeighting()

    with patch.object(weighting, "get_recent_accuracy", return_value=0.8):
        adjusted = weighting.calculate_adjusted_confidence(
            0.95, "consensus", "basketball_nba", "game"
        )
        # 80% accuracy: multiplier = 1.0 + (0.8-0.6)*0.5 = 1.1
        # 0.95 * 1.1 = 1.045, capped at 1.0
        assert adjusted == 1.0


def test_get_model_weights_with_data(mock_table):
    """Test model weight calculation with performance data."""

    # Mock different performance for each model
    def mock_query(*args, **kwargs):
        return {
            "Items": [
                {
                    "model": "consensus",
                    "sport": "basketball_nba",
                    "analysis_type": "game",
                    "confidence": Decimal("0.7"),
                    "analysis_correct": True,
                }
            ]
            * 7
            + [
                {
                    "model": "consensus",
                    "sport": "basketball_nba",
                    "analysis_type": "game",
                    "confidence": Decimal("0.7"),
                    "analysis_correct": False,
                }
            ]
            * 3
        }

    mock_table.query.side_effect = mock_query

    weighting = DynamicModelWeighting()
    weights, inversions = weighting.get_model_weights("basketball_nba", "game")

    # Should return normalized weights for all three models
    assert "consensus" in weights
    assert "value" in weights
    assert "momentum" in weights
    assert abs(sum(weights.values()) - 1.0) < 0.01  # Weights sum to 1


def test_get_model_weights_no_data(mock_table):
    """Test model weights with no performance data."""
    mock_table.query.return_value = {"Items": []}

    weighting = DynamicModelWeighting()
    weights, inversions = weighting.get_model_weights("basketball_nba", "game")

    # Equal weights when no data
    assert weights["consensus"] == pytest.approx(1 / 3)
    assert weights["value"] == pytest.approx(1 / 3)
    assert weights["momentum"] == pytest.approx(1 / 3)
    assert inversions["consensus"] == False
    assert inversions["value"] == False
    assert inversions["momentum"] == False
