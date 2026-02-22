"""Unit tests for DynamicModelWeighting class."""
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from ml.dynamic_weighting import DynamicModelWeighting


def test_get_model_weights_with_data():
    """Test model weight calculation with performance data."""
    with patch("ml.dynamic_weighting.ModelPerformanceTracker") as mock_tracker_class:
        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker
        
        # Mock different performance for each model
        def mock_perf(model, sport, days):
            if model == "consensus":
                return {"total_predictions": 20, "accuracy": 0.7}
            elif model == "value":
                return {"total_predictions": 15, "accuracy": 0.6}
            else:
                return {"total_predictions": 5, "accuracy": 0.5}
        
        mock_tracker.get_model_performance.side_effect = mock_perf
        
        weighting = DynamicModelWeighting()
        weights = weighting.get_model_weights("basketball_nba", "game", ["consensus", "value", "momentum"])
        
        # Should return normalized weights
        assert "consensus" in weights
        assert "value" in weights
        assert "momentum" in weights
        assert abs(sum(weights.values()) - 1.0) < 0.01


def test_get_model_weights_no_data():
    """Test model weights with no performance data."""
    with patch("ml.dynamic_weighting.ModelPerformanceTracker") as mock_tracker_class:
        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker
        
        # All models have insufficient data
        mock_tracker.get_model_performance.return_value = {"total_predictions": 5, "accuracy": 0.5}
        
        weighting = DynamicModelWeighting()
        weights = weighting.get_model_weights("basketball_nba", "game", ["consensus", "value", "momentum"])
        
        # Equal weights when insufficient data
        assert weights["consensus"] == pytest.approx(1 / 3)
        assert weights["value"] == pytest.approx(1 / 3)
        assert weights["momentum"] == pytest.approx(1 / 3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
