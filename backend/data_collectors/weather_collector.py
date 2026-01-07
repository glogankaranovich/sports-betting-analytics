"""
Weather Data Collector
Collects weather conditions for outdoor NFL games
"""

import os
from typing import Dict, List
from datetime import datetime
import logging
from .base_collector import BaseDataCollector, CollectionResult

# Optional aiohttp import
try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

logger = logging.getLogger(__name__)


class WeatherDataCollector(BaseDataCollector):
    """Collects weather data for outdoor games"""

    def __init__(self):
        super().__init__("weather", update_frequency_minutes=30)
        self.weather_api_key = os.environ.get("OPENWEATHER_API_KEY", "demo_key")

        # NFL outdoor venues (lat, lon)
        self.outdoor_venues = {
            "Arrowhead Stadium": (39.0489, -94.4839),
            "Lambeau Field": (44.5013, -88.0622),
            "Soldier Field": (41.8623, -87.6167),
            "FirstEnergy Stadium": (41.5061, -81.6995),
            "Heinz Field": (40.4468, -80.0158),
            "M&T Bank Stadium": (39.2780, -76.6227),
            "Gillette Stadium": (42.0909, -71.2643),
            "MetLife Stadium": (40.8135, -74.0745),
            "Lincoln Financial Field": (39.9008, -75.1675),
            "FedExField": (38.9076, -76.8645),
            "Bank of America Stadium": (35.2258, -80.8528),
            "TIAA Bank Stadium": (30.3240, -81.6374),
            "Hard Rock Stadium": (25.9580, -80.2389),
            "Nissan Stadium": (36.1665, -86.7713),
            "NRG Stadium": (29.6847, -95.4107),  # Retractable roof
            "Empower Field at Mile High": (39.7439, -104.9965),
            "Allegiant Stadium": (36.0909, -115.1833),  # Indoor
            "SoFi Stadium": (33.9535, -118.3392),  # Indoor
            "Levi's Stadium": (37.4032, -121.9698),
            "CenturyLink Field": (47.5952, -122.3316),
        }

        # Indoor venues don't need weather data
        self.indoor_venues = {
            "Mercedes-Benz Superdome",
            "AT&T Stadium",
            "Ford Field",
            "Lucas Oil Stadium",
            "U.S. Bank Stadium",
            "State Farm Stadium",
            "Allegiant Stadium",
            "SoFi Stadium",
        }

    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect weather data for outdoor games"""
        try:
            weather_data = {}
            records_collected = 0

            # Only collect weather for NFL games
            if sport != "americanfootball_nfl":
                return CollectionResult(
                    success=True,
                    data={},
                    error=None,
                    timestamp=datetime.utcnow(),
                    source="weather_collector",
                    data_quality_score=1.0,
                    records_collected=0,
                )

            for game in games:
                venue = game.get("venue", "")

                if venue in self.indoor_venues:
                    # Indoor venue - no weather impact
                    weather_data[game["id"]] = {
                        "venue_type": "indoor",
                        "weather_impact_score": 0.0,
                        "collected_at": datetime.utcnow().isoformat(),
                    }
                    records_collected += 1

                elif venue in self.outdoor_venues:
                    # Outdoor venue - get weather forecast
                    lat, lon = self.outdoor_venues[venue]
                    weather_info = await self.get_weather_forecast(
                        lat, lon, game.get("commence_time", "")
                    )

                    if weather_info:
                        weather_data[game["id"]] = {
                            "venue_type": "outdoor",
                            "venue_name": venue,
                            "temperature": weather_info["temperature"],
                            "wind_speed": weather_info["wind_speed"],
                            "wind_direction": weather_info.get("wind_direction", 0),
                            "precipitation_chance": weather_info[
                                "precipitation_chance"
                            ],
                            "humidity": weather_info["humidity"],
                            "conditions": weather_info["conditions"],
                            "weather_impact_score": self.calculate_weather_impact(
                                weather_info
                            ),
                            "collected_at": datetime.utcnow().isoformat(),
                        }
                        records_collected += 1
                else:
                    # Unknown venue - assume indoor
                    weather_data[game["id"]] = {
                        "venue_type": "unknown",
                        "weather_impact_score": 0.0,
                        "collected_at": datetime.utcnow().isoformat(),
                    }
                    records_collected += 1

            quality_score = self.validate_data(weather_data)

            return CollectionResult(
                success=True,
                data=weather_data,
                error=None,
                timestamp=datetime.utcnow(),
                source="weather_collector",
                data_quality_score=quality_score,
                records_collected=records_collected,
            )

        except Exception as e:
            logger.error(f"Weather collection failed: {e}")
            return CollectionResult(
                success=False,
                data=None,
                error=str(e),
                timestamp=datetime.utcnow(),
                source="weather_collector",
                data_quality_score=0.0,
                records_collected=0,
            )

    async def get_weather_forecast(
        self, lat: float, lon: float, game_time: str
    ) -> Dict:
        """Get weather forecast for game location and time"""
        if self.weather_api_key == "demo_key" or not HAS_AIOHTTP:
            # Return mock data for testing
            return {
                "temperature": 45.0,
                "wind_speed": 8.5,
                "wind_direction": 180,
                "precipitation_chance": 20,
                "humidity": 65,
                "conditions": "partly cloudy",
            }

        try:
            if not HAS_AIOHTTP:
                logger.warning("aiohttp not available, using mock weather data")
                return None

            async with aiohttp.ClientSession() as session:
                url = "https://api.openweathermap.org/data/2.5/forecast"
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.weather_api_key,
                    "units": "imperial",
                }

                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Weather API error: {response.status}")
                        return None

                    data = await response.json()

                    # Find forecast closest to game time
                    game_datetime = datetime.fromisoformat(
                        game_time.replace("Z", "+00:00")
                    )
                    closest_forecast = self.find_closest_forecast(
                        data["list"], game_datetime
                    )

                    if not closest_forecast:
                        return None

                    return {
                        "temperature": closest_forecast["main"]["temp"],
                        "wind_speed": closest_forecast.get("wind", {}).get("speed", 0),
                        "wind_direction": closest_forecast.get("wind", {}).get(
                            "deg", 0
                        ),
                        "precipitation_chance": closest_forecast.get("pop", 0) * 100,
                        "humidity": closest_forecast["main"]["humidity"],
                        "conditions": closest_forecast["weather"][0]["description"],
                    }

        except Exception as e:
            logger.error(f"Failed to get weather forecast: {e}")
            return None

    def find_closest_forecast(
        self, forecasts: List[Dict], target_time: datetime
    ) -> Dict:
        """Find forecast entry closest to game time"""
        if not forecasts:
            return None

        closest_forecast = None
        min_time_diff = float("inf")

        for forecast in forecasts:
            forecast_time = datetime.fromtimestamp(forecast["dt"])
            time_diff = abs((forecast_time - target_time).total_seconds())

            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_forecast = forecast

        return closest_forecast

    def calculate_weather_impact(self, weather_info: Dict) -> float:
        """Calculate weather impact score (0-1, higher = more impact)"""
        impact_score = 0.0

        # Temperature impact (extreme cold/heat)
        temp = weather_info["temperature"]
        if temp < 20:  # Very cold
            impact_score += 0.4
        elif temp < 32:  # Cold
            impact_score += 0.2
        elif temp > 90:  # Very hot
            impact_score += 0.3
        elif temp > 80:  # Hot
            impact_score += 0.1

        # Wind impact
        wind_speed = weather_info["wind_speed"]
        if wind_speed > 20:  # Very windy
            impact_score += 0.4
        elif wind_speed > 15:  # Windy
            impact_score += 0.2
        elif wind_speed > 10:  # Moderate wind
            impact_score += 0.1

        # Precipitation impact
        precip_chance = weather_info["precipitation_chance"]
        if precip_chance > 70:  # High chance of rain/snow
            impact_score += 0.3
        elif precip_chance > 40:  # Moderate chance
            impact_score += 0.2
        elif precip_chance > 20:  # Low chance
            impact_score += 0.1

        # Cap at 1.0
        return min(1.0, impact_score)

    def validate_data(self, data: Dict) -> float:
        """Validate weather data quality"""
        if not data:
            return 0.0

        total_games = len(data)
        valid_games = 0

        for game_data in data.values():
            if game_data.get("venue_type") == "indoor":
                valid_games += 1  # Indoor venues are always valid
            elif game_data.get("venue_type") == "outdoor":
                # Check required outdoor weather fields
                required_fields = [
                    "temperature",
                    "wind_speed",
                    "precipitation_chance",
                    "weather_impact_score",
                ]
                if all(field in game_data for field in required_fields):
                    valid_games += 1
            else:
                # Unknown venues default to valid
                valid_games += 1

        return valid_games / total_games if total_games > 0 else 0.0
