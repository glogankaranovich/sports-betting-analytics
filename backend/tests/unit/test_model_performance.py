"""
Unit tests for Model Performance Tracker
"""

import unittest
from unittest.mock import Mock, patch
from model_performance import ModelPerformanceTracker


class TestModelPerformanceTracker(unittest.TestCase):
    def setUp(self):
        self.table_name = "test-table"

    @patch("model_performance.boto3")
    def test_init(self, mock_boto3):
        """Test tracker initialization"""
        mock_table = Mock()
        mock_table.name = self.table_name
        mock_boto3.resource.return_value.Table.return_value = mock_table

        tracker = ModelPerformanceTracker(self.table_name)
        self.assertEqual(tracker.table.name, self.table_name)

    @patch("model_performance.boto3")
    def test_is_prediction_correct_game(self, mock_boto3):
        """Test game prediction correctness check"""
        tracker = ModelPerformanceTracker(self.table_name)

        # Home team prediction correct
        analysis = {"prediction": "Home Win", "actual_outcome": "home"}
        self.assertTrue(tracker._is_prediction_correct(analysis))

        # Away team prediction correct
        analysis = {"prediction": "Away Win", "actual_outcome": "away"}
        self.assertTrue(tracker._is_prediction_correct(analysis))

        # Incorrect prediction
        analysis = {"prediction": "Home Win", "actual_outcome": "away"}
        self.assertFalse(tracker._is_prediction_correct(analysis))

    @patch("model_performance.boto3")
    def test_is_prediction_correct_prop(self, mock_boto3):
        """Test prop prediction correctness check"""
        tracker = ModelPerformanceTracker(self.table_name)

        # Over prediction correct
        analysis = {"prediction": "Over 10.5", "actual_outcome": "over"}
        self.assertTrue(tracker._is_prediction_correct(analysis))

        # Under prediction correct
        analysis = {"prediction": "Under 10.5", "actual_outcome": "under"}
        self.assertTrue(tracker._is_prediction_correct(analysis))

        # Incorrect prediction
        analysis = {"prediction": "Over 10.5", "actual_outcome": "under"}
        self.assertFalse(tracker._is_prediction_correct(analysis))

    @patch("model_performance.boto3")
    def test_calculate_calibration(self, mock_boto3):
        """Test confidence calibration calculation"""
        tracker = ModelPerformanceTracker(self.table_name)

        analyses = [
            {"prediction": "Home Win", "actual_outcome": "home", "confidence": 0.65},
            {"prediction": "Home Win", "actual_outcome": "away", "confidence": 0.68},
            {"prediction": "Away Win", "actual_outcome": "away", "confidence": 0.75},
            {"prediction": "Away Win", "actual_outcome": "away", "confidence": 0.78},
        ]

        calibration = tracker._calculate_calibration(analyses)

        # 0.6-0.7 bucket: 1 correct out of 2 = 0.5
        self.assertEqual(calibration["0.6-0.7"], 0.5)

        # 0.7-0.8 bucket: 2 correct out of 2 = 1.0
        self.assertEqual(calibration["0.7-0.8"], 1.0)

    @patch("model_performance.boto3")
    def test_calculate_roi(self, mock_boto3):
        """Test ROI calculation"""
        tracker = ModelPerformanceTracker(self.table_name)

        # 2 correct predictions out of 3
        analyses = [
            {"prediction": "Home Win", "actual_outcome": "home", "confidence": 0.7},
            {"prediction": "Home Win", "actual_outcome": "home", "confidence": 0.8},
            {"prediction": "Away Win", "actual_outcome": "home", "confidence": 0.6},
        ]

        roi = tracker._calculate_roi(analyses)

        # Total bet: 3 * $100 = $300
        # Total return: 2 * ($100 + $100/1.1) = 2 * $190.91 = $381.82
        # Profit: $381.82 - $300 = $81.82
        # ROI: $81.82 / $300 = 0.2727
        self.assertAlmostEqual(roi, 0.2727, places=2)


if __name__ == "__main__":
    unittest.main()
