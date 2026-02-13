"""Unit tests for model comparison cache."""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Set required env vars before importing
os.environ["DYNAMODB_TABLE"] = "test-table"

from model_comparison_cache import compute_model_comparison


@pytest.fixture
def mock_table():
    with patch("model_comparison_cache.table") as mock:
        yield mock


def test_compute_model_comparison_basic(mock_table):
    """Test basic model comparison computation."""
    # Mock DynamoDB responses
    mock_table.query.return_value = {
        "Items": [
            {
                "model": "consensus",
                "prediction": "Lakers",
                "analysis_correct": True,
                "bet_type": "game",
            },
            {
                "model": "consensus",
                "prediction": "Celtics",
                "analysis_correct": False,
                "bet_type": "game",
            },
        ]
    }

    result = compute_model_comparison("basketball_nba", 90)

    assert len(result) > 0
    assert all(isinstance(m["original_accuracy"], Decimal) for m in result)
    assert all(isinstance(m["inverse_accuracy"], Decimal) for m in result)


def test_compute_model_comparison_inverse_better(mock_table):
    """Test when inverse accuracy is better than original."""
    # Function queries twice per bet type: original then inverse
    # Return alternating results: original (bad), inverse (good), original (bad), inverse (good)...
    query_results = [
        # Game original (30% correct)
        {"Items": [{"analysis_correct": False} for _ in range(7)] + [{"analysis_correct": True} for _ in range(3)]},
        # Game inverse (70% correct)  
        {"Items": [{"analysis_correct": True} for _ in range(7)] + [{"analysis_correct": False} for _ in range(3)]},
        # Prop original (30% correct)
        {"Items": [{"analysis_correct": False} for _ in range(7)] + [{"analysis_correct": True} for _ in range(3)]},
        # Prop inverse (70% correct)
        {"Items": [{"analysis_correct": True} for _ in range(7)] + [{"analysis_correct": False} for _ in range(3)]},
    ]
    mock_table.query.side_effect = query_results * 10  # Repeat for all models

    result = compute_model_comparison("basketball_nba", 90)

    contrarian = next((m for m in result if m["model"] == "contrarian" and m["bet_type"] == "game"), None)
    assert contrarian is not None
    assert contrarian["inverse_accuracy"] > contrarian["original_accuracy"]
    assert contrarian["recommendation"] == "INVERSE"


def test_compute_model_comparison_decimal_types(mock_table):
    """Test that all numeric values are Decimal for DynamoDB."""
    mock_table.query.return_value = {
        "Items": [
            {"model": "value", "analysis_correct": True, "bet_type": "game"}
            for _ in range(6)
        ]
        + [
            {"model": "value", "analysis_correct": False, "bet_type": "game"}
            for _ in range(4)
        ]
    }

    result = compute_model_comparison("basketball_nba", 90)

    for model in result:
        assert isinstance(model["original_accuracy"], Decimal)
        assert isinstance(model["inverse_accuracy"], Decimal)
        assert isinstance(model["sample_size"], (int, Decimal))
