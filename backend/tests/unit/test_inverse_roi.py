"""
Unit tests for inverse prediction ROI calculation
"""
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import os

# Mock the table before importing
os.environ["TABLE_NAME"] = "test-table"

with patch("boto3.resource") as mock_resource:
    mock_dynamodb = MagicMock()
    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    mock_resource.return_value = mock_dynamodb
    from analysis_generator import create_inverse_prediction


class TestInverseROI(unittest.TestCase):
    """Test inverse prediction ROI and risk level calculation"""

    def test_inverse_game_prediction_roi(self):
        """Test that inverse game prediction recalculates ROI correctly"""
        original_item = {
            "pk": "ANALYSIS#basketball_nba#game123#fanduel",
            "sk": "consensus#game#LATEST",
            "prediction": "Lakers",
            "confidence": Decimal("0.60"),
            "recommended_odds": -110,
            "roi": Decimal("14.5"),
            "risk_level": "moderate",
            "analysis_type": "game",
            "home_team": "Lakers",
            "away_team": "Grizzlies",
            "all_outcomes": [
                {"name": "Lakers", "price": -110},
                {"name": "Grizzlies", "price": 90}
            ]
        }

        inverse = create_inverse_prediction(original_item)

        # Check inverse prediction
        self.assertEqual(inverse["prediction"], "Grizzlies")
        self.assertEqual(float(inverse["confidence"]), 0.40)
        self.assertEqual(inverse["recommended_odds"], 90)
        
        # Check ROI is recalculated (not same as original)
        self.assertNotEqual(float(inverse["roi"]), float(original_item["roi"]))
        
        # Verify ROI calculation: (0.40 * 0.9) - (1 - 0.40) = 0.36 - 0.60 = -0.24 = -24%
        expected_roi = (0.40 * (90 / 100)) - (1 - 0.40)
        self.assertAlmostEqual(float(inverse["roi"]), expected_roi * 100, places=1)
        
        # Check risk level is recalculated (40% confidence = aggressive)
        self.assertEqual(inverse["risk_level"], "aggressive")

    def test_inverse_prop_prediction_roi(self):
        """Test that inverse prop prediction recalculates ROI correctly"""
        original_item = {
            "pk": "ANALYSIS#basketball_nba#prop#player123#fanduel",
            "sk": "consensus#prop#LATEST",
            "prediction": "Over 25.5 points",
            "confidence": Decimal("0.70"),
            "recommended_odds": -120,
            "roi": Decimal("8.3"),
            "risk_level": "conservative",
            "analysis_type": "prop",
            "player_name": "LeBron James",
            "all_outcomes": [
                {"name": "Over", "price": -120},
                {"name": "Under", "price": 100}
            ]
        }

        inverse = create_inverse_prediction(original_item)

        # Check inverse prediction
        self.assertIn("Under", inverse["prediction"])
        self.assertAlmostEqual(float(inverse["confidence"]), 0.30, places=2)
        self.assertEqual(inverse["recommended_odds"], 100)
        
        # Check ROI is recalculated
        self.assertNotEqual(float(inverse["roi"]), float(original_item["roi"]))
        
        # Verify ROI calculation: (0.30 * 1.0) - (1 - 0.30) = 0.30 - 0.70 = -0.40 = -40%
        expected_roi = (0.30 * (100 / 100)) - (1 - 0.30)
        self.assertAlmostEqual(float(inverse["roi"]), expected_roi * 100, places=1)
        
        # Check risk level is recalculated (30% confidence = aggressive)
        self.assertEqual(inverse["risk_level"], "aggressive")

    def test_inverse_high_confidence_prediction(self):
        """Test inverse of high confidence prediction becomes low confidence"""
        original_item = {
            "pk": "ANALYSIS#basketball_nba#game123#fanduel",
            "sk": "consensus#game#LATEST",
            "prediction": "Warriors",
            "confidence": Decimal("0.75"),
            "recommended_odds": -200,
            "roi": Decimal("12.5"),
            "risk_level": "conservative",
            "analysis_type": "game",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "all_outcomes": [
                {"name": "Lakers", "price": 170},
                {"name": "Warriors", "price": -200}
            ]
        }

        inverse = create_inverse_prediction(original_item)

        # Inverse confidence should be 25% (aggressive risk)
        self.assertEqual(float(inverse["confidence"]), 0.25)
        self.assertEqual(inverse["risk_level"], "aggressive")
        
        # ROI should be negative for low confidence underdog
        self.assertLess(float(inverse["roi"]), 0)


if __name__ == "__main__":
    unittest.main()
