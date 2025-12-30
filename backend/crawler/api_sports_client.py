"""
API-SPORTS client for free sports data.
Official API with free forever plan covering 2000+ competitions.
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from .config import get_api_sports_key

logger = logging.getLogger(__name__)

class APISportsClient:
    """Official API-SPORTS client for comprehensive sports data."""
    
    def __init__(self):
        self.base_url = 'https://v3.football.api-sports.io'  # Football endpoint
        self.base_url_basketball = 'https://v1.basketball.api-sports.io'
        self.base_url_baseball = 'https://v1.baseball.api-sports.io'
        self.base_url_hockey = 'https://v1.hockey.api-sports.io'
        self.secret_name = 'sports-betting/api-sports-key'
        self._api_key = None
        self._session = None
    
    async def __aenter__(self):
        await self._initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def _initialize(self):
        if not self._api_key:
            self._api_key = get_api_sports_key()
            if not self._api_key:
                raise ValueError("API-SPORTS API key not found")
        if not self._session:
            self._session = aiohttp.ClientSession()
    
    async def _make_request(self, base_url: str, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated request to API-SPORTS."""
        url = f"{base_url}/{endpoint}"
        headers = {
            'X-RapidAPI-Key': self._api_key,
            'X-RapidAPI-Host': base_url.replace('https://', '')
        }
        
        try:
            async with self._session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('response', [])
        except aiohttp.ClientError as e:
            logger.error(f"API-SPORTS request failed: {url} - {e}")
            raise
    
    # Football/Soccer Methods
    async def get_football_fixtures(self, league_id: int, season: int) -> List[Dict[str, Any]]:
        """Get football fixtures for a league and season."""
        params = {'league': league_id, 'season': season}
        return await self._make_request(self.base_url, 'fixtures', params)
    
    async def get_football_teams(self, league_id: int, season: int) -> List[Dict[str, Any]]:
        """Get football teams for a league."""
        params = {'league': league_id, 'season': season}
        return await self._make_request(self.base_url, 'teams', params)
    
    async def get_football_standings(self, league_id: int, season: int) -> List[Dict[str, Any]]:
        """Get football league standings."""
        params = {'league': league_id, 'season': season}
        return await self._make_request(self.base_url, 'standings', params)
    
    async def get_football_odds(self, fixture_id: int) -> List[Dict[str, Any]]:
        """Get betting odds for a football fixture."""
        params = {'fixture': fixture_id}
        return await self._make_request(self.base_url, 'odds', params)
    
    # Basketball Methods
    async def get_basketball_games(self, league_id: int, season: str) -> List[Dict[str, Any]]:
        """Get basketball games for a league and season."""
        params = {'league': league_id, 'season': season}
        return await self._make_request(self.base_url_basketball, 'games', params)
    
    async def get_basketball_teams(self, league_id: int) -> List[Dict[str, Any]]:
        """Get basketball teams for a league."""
        params = {'league': league_id}
        return await self._make_request(self.base_url_basketball, 'teams', params)
    
    async def get_basketball_standings(self, league_id: int, season: str) -> List[Dict[str, Any]]:
        """Get basketball league standings."""
        params = {'league': league_id, 'season': season}
        return await self._make_request(self.base_url_basketball, 'standings', params)
    
    # Baseball Methods  
    async def get_baseball_games(self, league_id: int, season: int) -> List[Dict[str, Any]]:
        """Get baseball games for a league and season."""
        params = {'league': league_id, 'season': season}
        return await self._make_request(self.base_url_baseball, 'games', params)
    
    # Hockey Methods
    async def get_hockey_games(self, league_id: int, season: int) -> List[Dict[str, Any]]:
        """Get hockey games for a league and season."""
        params = {'league': league_id, 'season': season}
        return await self._make_request(self.base_url_hockey, 'games', params)
    
    # Unified Methods
    async def get_sport_data(self, sport: str, data_type: str, **kwargs) -> List[Dict[str, Any]]:
        """Unified method to get data for any sport."""
        sport_mapping = {
            'football': self.base_url,
            'soccer': self.base_url,
            'basketball': self.base_url_basketball,
            'baseball': self.base_url_baseball,
            'hockey': self.base_url_hockey
        }
        
        base_url = sport_mapping.get(sport.lower())
        if not base_url:
            raise ValueError(f"Unsupported sport: {sport}")
        
        return await self._make_request(base_url, data_type, kwargs)

# League ID mappings for major leagues
LEAGUE_IDS = {
    # Football/Soccer
    'premier_league': 39,
    'la_liga': 140,
    'bundesliga': 78,
    'serie_a': 135,
    'ligue_1': 61,
    'champions_league': 2,
    'mls': 253,
    
    # Basketball
    'nba': 12,
    'euroleague': 120,
    
    # Baseball
    'mlb': 1,
    
    # Hockey
    'nhl': 57
}
