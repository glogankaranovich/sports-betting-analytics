"""
Weather data collector for outdoor sports
"""
import os
import json
import boto3
import requests
from datetime import datetime
from typing import Dict, Optional
from decimal import Decimal

class WeatherCollector:
    def __init__(self):
        self.table = boto3.resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
        self.api_key = self._get_api_key()
        self.base_url = "http://api.weatherapi.com/v1"
        
        # Domed/indoor stadiums (no weather impact)
        self.indoor_venues = {
            'americanfootball_nfl': [
                'Mercedes-Benz Stadium', 'AT&T Stadium', 'Allegiant Stadium',
                'SoFi Stadium', 'U.S. Bank Stadium', 'Ford Field',
                'Caesars Superdome', 'Lucas Oil Stadium'
            ]
        }
    
    def _get_api_key(self) -> Optional[str]:
        """Get weather API key from Secrets Manager"""
        try:
            secret_arn = os.environ.get('WEATHER_API_SECRET_ARN')
            if not secret_arn:
                print("WEATHER_API_SECRET_ARN not configured")
                return None
            
            secrets_client = boto3.client('secretsmanager')
            response = secrets_client.get_secret_value(SecretId=secret_arn)
            return response['SecretString']
        except Exception as e:
            print(f"Error getting weather API key: {e}")
            return None
    
    def get_weather_for_game(self, game_id: str, venue: str, city: str, 
                            sport: str, game_time: str) -> Optional[Dict]:
        """Get weather forecast for a game"""
        if not self.api_key:
            print("Weather API key not configured")
            return None
        
        # Skip if indoor venue
        if self._is_indoor_venue(sport, venue):
            return {"conditions": "indoor", "impact": "none"}
        
        # Skip if not outdoor sport
        if sport not in ['americanfootball_nfl', 'baseball_mlb', 'soccer_epl']:
            return None
        
        try:
            # Get forecast for game time
            url = f"{self.base_url}/forecast.json"
            params = {
                'key': self.api_key,
                'q': city,
                'dt': game_time[:10]  # YYYY-MM-DD
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant weather data
            forecast = data.get('forecast', {}).get('forecastday', [{}])[0].get('day', {})
            
            weather_data = {
                'temp_f': forecast.get('avgtemp_f'),
                'wind_mph': forecast.get('maxwind_mph'),
                'precip_in': forecast.get('totalprecip_in'),
                'condition': forecast.get('condition', {}).get('text'),
                'humidity': forecast.get('avghumidity'),
                'impact': self._assess_weather_impact(sport, forecast)
            }
            
            # Store weather data
            self._store_weather(game_id, sport, weather_data)
            
            return weather_data
            
        except Exception as e:
            print(f"Error fetching weather: {e}")
            return None
    
    def _is_indoor_venue(self, sport: str, venue: str) -> bool:
        """Check if venue is indoor/domed"""
        indoor_list = self.indoor_venues.get(sport, [])
        return any(indoor in venue for indoor in indoor_list)
    
    def _assess_weather_impact(self, sport: str, forecast: Dict) -> str:
        """Assess weather impact on game"""
        wind = forecast.get('maxwind_mph', 0)
        temp = forecast.get('avgtemp_f', 70)
        precip = forecast.get('totalprecip_in', 0)
        
        if sport == 'americanfootball_nfl':
            if wind > 20 or temp < 20 or precip > 0.5:
                return 'high'
            elif wind > 15 or temp < 32 or precip > 0.2:
                return 'moderate'
            return 'low'
        
        elif sport == 'baseball_mlb':
            if wind > 15 or precip > 0.3:
                return 'high'
            elif wind > 10 or precip > 0.1:
                return 'moderate'
            return 'low'
        
        elif sport == 'soccer_epl':
            if precip > 0.5 or wind > 25:
                return 'high'
            elif precip > 0.2 or wind > 15:
                return 'moderate'
            return 'low'
        
        return 'low'
    
    def _store_weather(self, game_id: str, sport: str, weather_data: Dict):
        """Store weather data in DynamoDB"""
        timestamp = datetime.utcnow().isoformat()
        
        self.table.put_item(Item={
            'pk': f'WEATHER#{game_id}',
            'sk': timestamp,
            'game_id': game_id,
            'sport': sport,
            'temp_f': Decimal(str(weather_data.get('temp_f', 0))),
            'wind_mph': Decimal(str(weather_data.get('wind_mph', 0))),
            'precip_in': Decimal(str(weather_data.get('precip_in', 0))),
            'condition': weather_data.get('condition', 'Unknown'),
            'humidity': Decimal(str(weather_data.get('humidity', 0))),
            'impact': weather_data.get('impact', 'low'),
            'collected_at': timestamp
        })
