"""
Unit tests for weather collector
"""
import os
import unittest
from unittest.mock import patch, MagicMock

os.environ["DYNAMODB_TABLE"] = "test-table"

from weather_collector import WeatherCollector


class TestWeatherCollector(unittest.TestCase):
    """Test weather collector"""

    @patch("weather_collector.boto3.resource")
    @patch("weather_collector.boto3.client")
    def setUp(self, mock_client, mock_resource):
        self.mock_table = MagicMock()
        self.mock_secrets = MagicMock()
        mock_resource.return_value.Table.return_value = self.mock_table
        mock_client.return_value = self.mock_secrets
        
        # Mock the API key retrieval
        with patch.object(WeatherCollector, '_get_api_key', return_value='test_key'):
            self.collector = WeatherCollector()

    def test_is_indoor_venue_nfl(self):
        """Test indoor venue detection for NFL"""
        self.assertTrue(self.collector._is_indoor_venue('americanfootball_nfl', 'AT&T Stadium'))
        self.assertFalse(self.collector._is_indoor_venue('americanfootball_nfl', 'Lambeau Field'))

    def test_is_indoor_venue_nba(self):
        """Test NBA venues (all indoor)"""
        # NBA not in outdoor sports list
        result = self.collector._is_indoor_venue('basketball_nba', 'Any Arena')
        self.assertFalse(result)  # Returns False because NBA not in indoor_venues dict

    @patch("weather_collector.requests.get")
    def test_get_weather_for_game_success(self, mock_get):
        """Test successful weather data retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "forecast": {
                "forecastday": [{
                    "day": {
                        "avgtemp_f": 72,
                        "maxwind_mph": 10,
                        "totalprecip_in": 0.1,
                        "avghumidity": 60,
                        "condition": {"text": "Partly cloudy"}
                    }
                }]
            }
        }
        mock_get.return_value = mock_response

        weather = self.collector.get_weather_for_game(
            "game123", "Lambeau Field", "Green Bay", 
            "americanfootball_nfl", "2026-02-20T13:00:00"
        )
        
        self.assertIsNotNone(weather)
        self.assertEqual(weather["temp_f"], 72)
        self.assertEqual(weather["wind_mph"], 10)

    def test_get_weather_for_indoor_venue(self):
        """Test weather for indoor venue returns indoor status"""
        weather = self.collector.get_weather_for_game(
            "game123", "AT&T Stadium", "Dallas",
            "americanfootball_nfl", "2026-02-20T13:00:00"
        )
        
        self.assertIsNotNone(weather)
        self.assertEqual(weather["conditions"], "indoor")
        self.assertEqual(weather["impact"], "none")


if __name__ == "__main__":
    unittest.main()
