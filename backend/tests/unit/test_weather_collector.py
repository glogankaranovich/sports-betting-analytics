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

    def test_is_indoor_venue_mlb(self):
        """Test indoor venue detection for MLB"""
        self.assertTrue(self.collector._is_indoor_venue('baseball_mlb', 'Tropicana Field'))
        self.assertTrue(self.collector._is_indoor_venue('baseball_mlb', 'Globe Life Field'))
        self.assertFalse(self.collector._is_indoor_venue('baseball_mlb', 'Fenway Park'))

    def test_assess_weather_impact_nfl_high(self):
        """Test high weather impact for NFL"""
        forecast = {'maxwind_mph': 25, 'avgtemp_f': 15, 'totalprecip_in': 0.6}
        impact = self.collector._assess_weather_impact('americanfootball_nfl', forecast)
        self.assertEqual(impact, 'high')

    def test_assess_weather_impact_nfl_moderate(self):
        """Test moderate weather impact for NFL"""
        forecast = {'maxwind_mph': 16, 'avgtemp_f': 30, 'totalprecip_in': 0.25}
        impact = self.collector._assess_weather_impact('americanfootball_nfl', forecast)
        self.assertEqual(impact, 'moderate')

    def test_assess_weather_impact_nfl_low(self):
        """Test low weather impact for NFL"""
        forecast = {'maxwind_mph': 10, 'avgtemp_f': 50, 'totalprecip_in': 0.1}
        impact = self.collector._assess_weather_impact('americanfootball_nfl', forecast)
        self.assertEqual(impact, 'low')

    def test_assess_weather_impact_mlb_high(self):
        """Test high weather impact for MLB"""
        forecast = {'maxwind_mph': 18, 'avgtemp_f': 70, 'totalprecip_in': 0.4}
        impact = self.collector._assess_weather_impact('baseball_mlb', forecast)
        self.assertEqual(impact, 'high')

    def test_assess_weather_impact_mlb_low(self):
        """Test low weather impact for MLB"""
        forecast = {'maxwind_mph': 8, 'avgtemp_f': 75, 'totalprecip_in': 0.05}
        impact = self.collector._assess_weather_impact('baseball_mlb', forecast)
        self.assertEqual(impact, 'low')

    def test_assess_weather_impact_soccer_high(self):
        """Test high weather impact for soccer"""
        forecast = {'maxwind_mph': 30, 'avgtemp_f': 60, 'totalprecip_in': 0.6}
        impact = self.collector._assess_weather_impact('soccer_epl', forecast)
        self.assertEqual(impact, 'high')

    def test_assess_weather_impact_mls(self):
        """Test weather impact for MLS"""
        forecast = {'maxwind_mph': 20, 'avgtemp_f': 65, 'totalprecip_in': 0.3}
        impact = self.collector._assess_weather_impact('soccer_usa_mls', forecast)
        self.assertEqual(impact, 'moderate')

    def test_store_weather_creates_latest_and_historical(self):
        """Test that _store_weather creates both latest and historical records"""
        weather_data = {
            'temp_f': 72,
            'wind_mph': 10,
            'precip_in': 0.1,
            'condition': 'Partly cloudy',
            'humidity': 60,
            'impact': 'low'
        }
        
        self.collector._store_weather('game123', 'americanfootball_nfl', weather_data)
        
        # Should call put_item twice: once for 'latest', once for timestamp
        self.assertEqual(self.mock_table.put_item.call_count, 2)
        
        # Check first call has sk='latest'
        first_call = self.mock_table.put_item.call_args_list[0][1]['Item']
        self.assertEqual(first_call['sk'], 'latest')
        self.assertEqual(first_call['pk'], 'WEATHER#game123')
        
        # Check second call has timestamp sk
        second_call = self.mock_table.put_item.call_args_list[1][1]['Item']
        self.assertNotEqual(second_call['sk'], 'latest')
        self.assertEqual(second_call['pk'], 'WEATHER#game123')

    def test_get_weather_for_non_outdoor_sport(self):
        """Test weather collection skips non-outdoor sports"""
        weather = self.collector.get_weather_for_game(
            "game123", "Staples Center", "Los Angeles",
            "basketball_nba", "2026-02-20T19:00:00"
        )
        
        self.assertIsNone(weather)

    @patch("weather_collector.requests.get")
    def test_get_weather_api_error(self, mock_get):
        """Test handling of API errors"""
        mock_get.side_effect = Exception("API Error")
        
        weather = self.collector.get_weather_for_game(
            "game123", "Lambeau Field", "Green Bay",
            "americanfootball_nfl", "2026-02-20T13:00:00"
        )
        
        self.assertIsNone(weather)

    def test_get_weather_no_api_key(self):
        """Test behavior when API key is not configured"""
        self.collector.api_key = None
        
        weather = self.collector.get_weather_for_game(
            "game123", "Lambeau Field", "Green Bay",
            "americanfootball_nfl", "2026-02-20T13:00:00"
        )
        
        self.assertIsNone(weather)


if __name__ == "__main__":
    unittest.main()
