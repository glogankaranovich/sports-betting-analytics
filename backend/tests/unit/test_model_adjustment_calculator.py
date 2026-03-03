"""Tests for model_adjustment_calculator"""
import unittest
from unittest.mock import Mock, patch

from model_adjustment_calculator import lambda_handler


class TestModelAdjustmentCalculator(unittest.TestCase):
    """Test model_adjustment_calculator"""

    @patch("model_adjustment_calculator.DynamicModelWeighting")
    def test_lambda_handler_success(self, mock_weighting_class):
        """Test successful lambda handler execution"""
        mock_weighting = Mock()
        mock_weighting.store_model_adjustments.return_value = [
            {"model": "consensus", "sport": "basketball_nba", "recommendation": "ORIGINAL"},
            {"model": "value", "sport": "basketball_nba", "recommendation": "INVERSE"},
        ]
        mock_weighting_class.return_value = mock_weighting
        
        result = lambda_handler({}, None)
        
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("total_adjustments", result["body"])
        self.assertIn("inverse_recommended", result["body"])
        
        # Should be called for all 10 sports
        self.assertEqual(mock_weighting.store_model_adjustments.call_count, 10)

    @patch("model_adjustment_calculator.DynamicModelWeighting")
    def test_lambda_handler_counts_recommendations(self, mock_weighting_class):
        """Test lambda handler counts recommendations correctly"""
        mock_weighting = Mock()
        mock_weighting.store_model_adjustments.return_value = [
            {"recommendation": "INVERSE"},
            {"recommendation": "AVOID"},
            {"recommendation": "ORIGINAL"},
        ]
        mock_weighting_class.return_value = mock_weighting
        
        result = lambda_handler({}, None)
        
        self.assertEqual(result["statusCode"], 200)
        # 3 adjustments per sport * 10 sports = 30 total
        self.assertEqual(result["body"]["total_adjustments"], 30)
        # 1 inverse per sport * 10 sports = 10
        self.assertEqual(result["body"]["inverse_recommended"], 10)
        # 1 avoid per sport * 10 sports = 10
        self.assertEqual(result["body"]["avoid_recommended"], 10)

    @patch("model_adjustment_calculator.DynamicModelWeighting")
    def test_lambda_handler_error(self, mock_weighting_class):
        """Test lambda handler error handling"""
        mock_weighting_class.side_effect = Exception("Test error")
        
        result = lambda_handler({}, None)
        
        self.assertEqual(result["statusCode"], 500)
        self.assertIn("error", result["body"])


if __name__ == "__main__":
    unittest.main()
