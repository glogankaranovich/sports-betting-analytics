"""
SportsData.io API client for unified sports and betting data.
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from .config import get_sportsdata_api_key

logger = logging.getLogger(__name__)

class SportsDataClient:
    """Unified client for SportsData.io API covering odds, team stats, and player data."""
    
    def __init__(self):
        self.base_url = 'https://api.sportsdata.io'
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
            self._api_key = get_sportsdata_api_key()
            if not self._api_key:
                raise ValueError("SportsData.io API key not found")
        if not self._session:
            self._session = aiohttp.ClientSession()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        headers = {'Ocp-Apim-Subscription-Key': self._api_key}
        
        try:
            async with self._session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {url} - {e}")
            raise
    
    # Betting Data
    async def get_odds(self, sport: str) -> List[Dict[str, Any]]:
        """Get betting odds for games."""
        endpoint = f"v4/odds/{sport}/odds"
        return await self._make_request(endpoint)
    
    # Team Data
    async def get_teams(self, sport: str) -> List[Dict[str, Any]]:
        """Get team information."""
        endpoint = f"v3/{sport}/teams"
        return await self._make_request(endpoint)
    
    async def get_standings(self, sport: str, season: str) -> List[Dict[str, Any]]:
        """Get league standings."""
        endpoint = f"v3/{sport}/standings/{season}"
        return await self._make_request(endpoint)
    
    # Player Data
    async def get_injuries(self, sport: str) -> List[Dict[str, Any]]:
        """Get injury reports."""
        endpoint = f"v3/{sport}/injuries"
        return await self._make_request(endpoint)
    
    # Game Data
    async def get_games(self, sport: str, season: str) -> List[Dict[str, Any]]:
        """Get game schedule."""
        endpoint = f"v3/{sport}/games/{season}"
        return await self._make_request(endpoint)
    
    # Unified Collection
    async def get_enhanced_game_data(self, sport: str) -> Dict[str, Any]:
        """Get comprehensive game data."""
        tasks = [
            self.get_odds(sport),
            self.get_teams(sport),
            self.get_injuries(sport)
        ]
        
        odds, teams, injuries = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'sport': sport,
            'odds': odds if not isinstance(odds, Exception) else [],
            'teams': teams if not isinstance(teams, Exception) else [],
            'injuries': injuries if not isinstance(injuries, Exception) else [],
            'collected_at': datetime.utcnow().isoformat()
        }

# Sport mapping including major soccer leagues
SPORT_MAPPING = {
    # US Sports
    'basketball': 'nba',
    'football': 'nfl', 
    'baseball': 'mlb',
    'hockey': 'nhl',
    
    # Soccer Leagues
    'soccer_mls': 'mls',                    # Major League Soccer (US)
    'soccer_epl': 'epl',                    # English Premier League
    'soccer_championship': 'efl',           # English Championship
    'soccer_bundesliga': 'bundesliga',      # German Bundesliga
    'soccer_serie_a': 'seriea',            # Italian Serie A
    'soccer_la_liga': 'laliga',            # Spanish La Liga
    'soccer_ligue_1': 'ligue1',            # French Ligue 1
    'soccer_champions_league': 'ucl',       # UEFA Champions League
    'soccer_europa_league': 'uel',         # UEFA Europa League
    'soccer_world_cup': 'worldcup',        # FIFA World Cup
    'soccer_euros': 'euros',               # UEFA European Championship
    'soccer_copa_america': 'copaamerica',  # Copa América
    'soccer_liga_mx': 'ligamx',            # Mexican Liga MX
    'soccer_brasileirao': 'brasileirao',   # Brazilian Série A
    'soccer_eredivisie': 'eredivisie',     # Dutch Eredivisie
    'soccer_primeira_liga': 'primeiraliga' # Portuguese Primeira Liga
}

# Popular soccer leagues for betting
MAJOR_SOCCER_LEAGUES = [
    'soccer_epl',
    'soccer_bundesliga', 
    'soccer_serie_a',
    'soccer_la_liga',
    'soccer_ligue_1',
    'soccer_champions_league',
    'soccer_mls'
]
