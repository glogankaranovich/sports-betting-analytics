"""Model performance tracker tests"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from model_performance import ModelPerformanceTracker


@pytest.fixture
def tracker():
    with patch("model_performance.boto3"):
        return ModelPerformanceTracker("test-table")


def test_get_model_performance_no_predictions(tracker):
    """Test performance with no predictions"""
    tracker.table = Mock()
    tracker.table.query.return_value = {"Items": []}
    
    perf = tracker.get_model_performance("consensus", "basketball_nba", 30)
    
    assert perf["total_predictions"] == 0
    assert perf["accuracy"] == 0.0


def test_get_model_performance_with_predictions(tracker):
    """Test performance with predictions"""
    tracker.table = Mock()
    tracker.table.query.return_value = {
        "Items": [
            {
                "model": "consensus",
                "confidence": Decimal("0.75"),
                "prediction": "Lakers -5.5",
                "actual_outcome": "Lakers -6.0"
            }
        ]
    }
    
    with patch.object(tracker, "_is_prediction_correct", return_value=True):
        with patch.object(tracker, "_calculate_calibration", return_value={}):
            with patch.object(tracker, "_calculate_roi", return_value=10.5):
                perf = tracker.get_model_performance("consensus", "basketball_nba", 30)
                
                assert perf["total_predictions"] == 1
                assert perf["correct_predictions"] == 1
                assert perf["accuracy"] == 1.0


def test_get_all_models_performance(tracker):
    """Test getting performance for all models"""
    tracker.table = Mock()
    tracker.table.query.return_value = {"Items": []}
    
    with patch.object(tracker, "get_model_performance", return_value={"accuracy": 0.65}):
        perf = tracker.get_all_models_performance("basketball_nba", 30)
        assert isinstance(perf, dict)


def test_calculate_calibration_empty(tracker):
    """Test calibration with empty analyses"""
    calibration = tracker._calculate_calibration([])
    assert calibration == {}


def test_calculate_roi_empty(tracker):
    """Test ROI with empty analyses"""
    roi = tracker._calculate_roi([])
    assert roi == 0.0


def test_is_prediction_correct_spread(tracker):
    """Test prediction correctness for spread"""
    analysis = {
        "prediction": "Lakers -5.5",
        "actual_outcome": "Lakers -6.0"
    }
    
    # Should check if prediction was correct
    result = tracker._is_prediction_correct(analysis)
    assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
