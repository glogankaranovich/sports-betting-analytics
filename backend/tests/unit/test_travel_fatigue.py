"""
Unit tests for travel fatigue calculator
"""
import os
import unittest
from unittest.mock import patch, MagicMock

os.environ["DYNAMODB_TABLE"] = "test-table"

from travel_fatigue_calculator import TravelFatigueCalculator


class TestTravelFatigueCalculator(unittest.TestCase):
    """Test travel fatigue calculator"""

    @patch("travel_fatigue_calculator.boto3.resource")
    def setUp(self, mock_resource):
        self.mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = self.mock_table
        self.calculator = TravelFatigueCalculator()

    def test_calculate_distance_nba_teams(self):
        """Test distance calculation between NBA teams"""
        # LA Lakers to Boston Celtics (approximately 2600 miles)
        distance = self.calculator.calculate_distance("Los Angeles Lakers", "Boston Celtics")
        self.assertGreater(distance, 2500)
        self.assertLess(distance, 2700)

    def test_calculate_distance_same_city(self):
        """Test distance for teams in same city"""
        distance = self.calculator.calculate_distance("Los Angeles Lakers", "Los Angeles Clippers")
        self.assertEqual(distance, 0.0)

    def test_calculate_distance_unknown_team(self):
        """Test distance for unknown team returns 0"""
        distance = self.calculator.calculate_distance("Unknown Team", "Boston Celtics")
        self.assertEqual(distance, 0.0)

    def test_team_locations_loaded(self):
        """Test team locations are loaded"""
        self.assertGreater(len(self.calculator.team_locations), 0)
        self.assertIn("Los Angeles Lakers", self.calculator.team_locations)
        self.assertIn("New England Patriots", self.calculator.team_locations)

    def test_calculate_fatigue_score(self):
        """Test fatigue score calculation"""
        self.mock_table.query.return_value = {"Items": []}
        
        result = self.calculator.calculate_fatigue_score(
            "Los Angeles Lakers", "basketball_nba", "2026-02-20"
        )
        
        self.assertIn("fatigue_score", result)
        self.assertIn("total_miles", result)


if __name__ == "__main__":
    unittest.main()
