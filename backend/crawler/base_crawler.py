"""
Base crawler architecture for sports data collection.

This module provides a configurable framework for collecting sports data
from various sources (APIs, web scraping) with built-in error handling,
rate limiting, and data validation.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import aiohttp
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Types of data sources supported by the crawler."""
    API = "api"
    WEB_SCRAPER = "web_scraper"
    RSS_FEED = "rss_feed"


@dataclass
class CrawlerConfig:
    """Configuration for a data source crawler."""
    name: str
    source_type: DataSourceType
    base_url: str
    api_key: Optional[str] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    retry_attempts: int = 3
    enabled: bool = True


@dataclass
class TeamStats:
    """Team performance statistics."""
    team_id: str
    wins: int
    losses: int
    win_percentage: float
    points_per_game: float
    points_allowed_per_game: float
    home_record: str
    away_record: str
    last_5_games: str
    injuries_count: int


@dataclass
class PlayerInfo:
    """Key player information."""
    player_id: str
    name: str
    position: str
    injury_status: str  # "healthy", "questionable", "doubtful", "out"
    season_stats: Dict[str, float]


@dataclass
class WeatherConditions:
    """Weather conditions for outdoor games."""
    temperature: Optional[float]
    humidity: Optional[float]
    wind_speed: Optional[float]
    precipitation: Optional[str]
    conditions: Optional[str]


@dataclass
class SportEvent:
    """Enhanced sports event data structure with ML context."""
    event_id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker_odds: List[Dict[str, Any]]
    source: str
    
    # Enhanced context data (all optional with defaults)
    home_team_stats: Optional[TeamStats] = None
    away_team_stats: Optional[TeamStats] = None
    key_players: Optional[List[PlayerInfo]] = None
    weather: Optional[WeatherConditions] = None
    referee_id: Optional[str] = None
    venue: Optional[str] = None
    
    def __post_init__(self):
        if self.key_players is None:
            self.key_players = []


class BaseCrawler(ABC):
    """Abstract base class for all data crawlers."""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(config.rate_limit_per_minute)
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def fetch_sports_data(self, sport: str, **kwargs) -> List[SportEvent]:
        """Fetch sports data for a specific sport."""
        pass
    
    @abstractmethod
    async def get_available_sports(self) -> List[str]:
        """Get list of available sports from this source."""
        pass
    
    async def _make_request(self, url: str, params: Dict = None) -> Dict[str, Any]:
        """Make rate-limited HTTP request with retry logic."""
        async with self._rate_limiter:
            for attempt in range(self.config.retry_attempts):
                try:
                    async with self.session.get(url, params=params) as response:
                        response.raise_for_status()
                        return await response.json()
                except Exception as e:
                    logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                    if attempt == self.config.retry_attempts - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff


class TheOddsAPICrawler(BaseCrawler):
    """Crawler for The Odds API."""
    
    SPORT_MAPPING = {
        'nfl': 'americanfootball_nfl',
        'nba': 'basketball_nba',
        'mlb': 'baseball_mlb',
        'nhl': 'icehockey_nhl',
        'soccer_epl': 'soccer_epl',
        'soccer_uefa_champs_league': 'soccer_uefa_champs_league',
    }
    
    async def fetch_sports_data(self, sport: str, **kwargs) -> List[SportEvent]:
        """Fetch odds data from The Odds API."""
        if not self.config.enabled:
            return []
        
        sport_key = self.SPORT_MAPPING.get(sport, sport)
        url = f"{self.config.base_url}/sports/{sport_key}/odds"
        
        params = {
            'apiKey': self.config.api_key,
            'regions': kwargs.get('regions', 'us'),
            'markets': kwargs.get('markets', 'h2h,spreads,totals'),
            'oddsFormat': kwargs.get('odds_format', 'american'),
        }
        
        try:
            data = await self._make_request(url, params)
            return self._parse_odds_data(data, sport)
        except Exception as e:
            logger.error(f"Failed to fetch data for {sport}: {e}")
            return []
    
    async def get_available_sports(self) -> List[str]:
        """Get available sports from The Odds API."""
        url = f"{self.config.base_url}/sports"
        params = {'apiKey': self.config.api_key}
        
        try:
            data = await self._make_request(url, params)
            return [sport['key'] for sport in data if sport['active']]
        except Exception as e:
            logger.error(f"Failed to fetch available sports: {e}")
            return []
    
    def _parse_odds_data(self, data: List[Dict], sport: str) -> List[SportEvent]:
        """Parse The Odds API response into SportEvent objects."""
        events = []
        
        for game in data:
            try:
                event = SportEvent(
                    event_id=game['id'],
                    sport=sport,
                    home_team=game['home_team'],
                    away_team=game['away_team'],
                    commence_time=datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00')),
                    bookmaker_odds=game.get('bookmakers', []),
                    source=self.config.name
                )
                events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse game data: {e}")
                continue
        
        return events


class SportsDataIOCrawler(BaseCrawler):
    """Crawler for SportsData.io unified API."""
    
    from .sportsdata_client import SPORT_MAPPING
    
    async def fetch_sports_data(self, sport: str, **kwargs) -> List[SportEvent]:
        """Fetch enhanced sports data from SportsData.io."""
        if not self.config.enabled:
            return []
        
        from .sportsdata_client import SportsDataClient
        
        try:
            async with SportsDataClient() as client:
                data = await client.get_enhanced_game_data(sport)
                return self._parse_enhanced_data(data, sport)
        except Exception as e:
            logger.error(f"Failed to fetch data for {sport}: {e}")
            return []
    
    async def get_available_sports(self) -> List[str]:
        """Get available sports from SportsData.io."""
        from .sportsdata_client import SPORT_MAPPING
        return list(SPORT_MAPPING.keys())
    
    def _parse_enhanced_data(self, data: Dict, sport: str) -> List[SportEvent]:
        """Parse SportsData.io response into enhanced SportEvent objects."""
        events = []
        
        # Extract and organize data
        odds_data = data.get('odds', [])
        teams_data = {team.get('TeamID'): team for team in data.get('teams', [])}
        injuries_data = data.get('injuries', [])
        
        for game in odds_data:
            try:
                # Basic event info
                home_team = game.get('HomeTeam', '')
                away_team = game.get('AwayTeam', '')
                
                # Enhanced team stats
                home_stats = self._build_team_stats(home_team, teams_data, injuries_data)
                away_stats = self._build_team_stats(away_team, teams_data, injuries_data)
                
                # Key players with injury status
                key_players = self._extract_key_players(game, injuries_data)
                
                # Weather for outdoor sports
                weather = self._extract_weather(game, sport)
                
                event = SportEvent(
                    event_id=f"sportsdata_{game.get('GameID', 'unknown')}",
                    sport=sport,
                    home_team=home_team,
                    away_team=away_team,
                    commence_time=datetime.fromisoformat(game.get('DateTime', '')),
                    bookmaker_odds=self._extract_odds(game),
                    source='sportsdata_io',
                    home_team_stats=home_stats,
                    away_team_stats=away_stats,
                    key_players=key_players,
                    weather=weather,
                    venue=game.get('StadiumDetails', {}).get('Name')
                )
                events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse game data: {e}")
                continue
        
        return events
    
    def _build_team_stats(self, team_name: str, teams_data: Dict, injuries_data: List) -> Optional[TeamStats]:
        """Build team statistics from available data."""
        team_info = None
        for team in teams_data.values():
            if team.get('Name') == team_name or team.get('Key') == team_name:
                team_info = team
                break
        
        if not team_info:
            return None
        
        # Count injuries for this team
        injury_count = sum(1 for injury in injuries_data 
                          if injury.get('Team') == team_name)
        
        return TeamStats(
            team_id=team_info.get('TeamID', ''),
            wins=team_info.get('Wins', 0),
            losses=team_info.get('Losses', 0),
            win_percentage=team_info.get('Percentage', 0.0),
            points_per_game=team_info.get('PointsPerGameFor', 0.0),
            points_allowed_per_game=team_info.get('PointsPerGameAgainst', 0.0),
            home_record=f"{team_info.get('HomeWins', 0)}-{team_info.get('HomeLosses', 0)}",
            away_record=f"{team_info.get('AwayWins', 0)}-{team_info.get('AwayLosses', 0)}",
            last_5_games=team_info.get('Streak', ''),
            injuries_count=injury_count
        )
    
    def _extract_key_players(self, game: Dict, injuries_data: List) -> List[PlayerInfo]:
        """Extract key players with injury status."""
        players = []
        
        # Get injured players for this game's teams
        home_team = game.get('HomeTeam', '')
        away_team = game.get('AwayTeam', '')
        
        for injury in injuries_data:
            if injury.get('Team') in [home_team, away_team]:
                player = PlayerInfo(
                    player_id=injury.get('PlayerID', ''),
                    name=injury.get('Name', ''),
                    position=injury.get('Position', ''),
                    injury_status=injury.get('Status', 'unknown').lower(),
                    season_stats={}  # Would need separate API call for detailed stats
                )
                players.append(player)
        
        return players
    
    def _extract_weather(self, game: Dict, sport: str) -> Optional[WeatherConditions]:
        """Extract weather conditions for outdoor sports."""
        if sport not in ['nfl', 'mlb', 'mls']:  # Only outdoor sports
            return None
        
        weather_data = game.get('Weather')
        if not weather_data:
            return None
        
        return WeatherConditions(
            temperature=weather_data.get('Temperature'),
            humidity=weather_data.get('Humidity'),
            wind_speed=weather_data.get('WindSpeed'),
            precipitation=weather_data.get('Precipitation'),
            conditions=weather_data.get('Conditions')
        )
    
    async def get_available_sports(self) -> List[str]:
        """Get available sports from SportsData.io."""
        # Return supported sports based on our mapping
        from .sportsdata_client import SPORT_MAPPING
        return list(SPORT_MAPPING.keys())
        """Extract weather conditions for outdoor sports."""
        if sport not in ['nfl', 'mlb', 'mls']:  # Only outdoor sports
            return None
        
        weather_data = game.get('Weather')
        if not weather_data:
            return None
        
    def _extract_odds(self, game: Dict) -> List[Dict[str, Any]]:
        """Extract betting odds from SportsData.io game data."""
        odds = []
        
        # SportsData.io provides odds in different format
        if 'Odds' in game:
            for bookmaker_odds in game['Odds']:
                odds.append({
                    'bookmaker': bookmaker_odds.get('Sportsbook', 'unknown'),
                    'markets': {
                        'h2h': [
                            bookmaker_odds.get('HomeMoneyLine'),
                            bookmaker_odds.get('AwayMoneyLine')
                        ],
                        'spreads': [
                            {
                                'point': bookmaker_odds.get('HomePointSpread'),
                                'price': bookmaker_odds.get('HomePointSpreadPayout')
                            },
                            {
                                'point': bookmaker_odds.get('AwayPointSpread'), 
                                'price': bookmaker_odds.get('AwayPointSpreadPayout')
                            }
                        ],
                        'totals': {
                            'over': {
                                'point': bookmaker_odds.get('OverUnder'),
                                'price': bookmaker_odds.get('OverPayout')
                            },
                            'under': {
                                'point': bookmaker_odds.get('OverUnder'),
                                'price': bookmaker_odds.get('UnderPayout')
                            }
                        }
                    }
                })
        
        return odds


class CrawlerManager:
    """Manages multiple data crawlers and coordinates data collection."""
    
    def __init__(self):
        self.crawlers: Dict[str, BaseCrawler] = {}
        self.configs: Dict[str, CrawlerConfig] = {}
    
    def add_crawler(self, crawler: BaseCrawler):
        """Add a crawler to the manager."""
        self.crawlers[crawler.config.name] = crawler
        self.configs[crawler.config.name] = crawler.config
    
    def remove_crawler(self, name: str):
        """Remove a crawler from the manager."""
        self.crawlers.pop(name, None)
        self.configs.pop(name, None)
    
    async def collect_all_data(self, sports: List[str]) -> Dict[str, List[SportEvent]]:
        """Collect data from all enabled crawlers for specified sports."""
        results = {}
        
        for sport in sports:
            sport_data = []
            
            # Collect from all enabled crawlers
            tasks = []
            for name, crawler in self.crawlers.items():
                if self.configs[name].enabled:
                    tasks.append(self._collect_from_crawler(crawler, sport))
            
            # Execute all crawler tasks concurrently
            if tasks:
                crawler_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in crawler_results:
                    if isinstance(result, Exception):
                        logger.error(f"Crawler failed: {result}")
                    elif isinstance(result, list):
                        sport_data.extend(result)
            
            results[sport] = sport_data
        
        return results
    
    async def _collect_from_crawler(self, crawler: BaseCrawler, sport: str) -> List[SportEvent]:
        """Collect data from a single crawler with context management."""
        try:
            async with crawler:
                return await crawler.fetch_sports_data(sport)
        except Exception as e:
            logger.error(f"Failed to collect from {crawler.config.name}: {e}")
            return []
    
    def get_crawler_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all crawlers."""
        status = {}
        for name, config in self.configs.items():
            status[name] = {
                'enabled': config.enabled,
                'source_type': config.source_type.value,
                'rate_limit': config.rate_limit_per_minute,
                'has_api_key': bool(config.api_key),
            }
        return status


# Factory functions for creating pre-configured crawlers
def create_the_odds_api_crawler(api_key: str) -> TheOddsAPICrawler:
    """Create a pre-configured The Odds API crawler."""
    config = CrawlerConfig(
        name="the_odds_api",
        source_type=DataSourceType.API,
        base_url="https://api.the-odds-api.com/v4",
        api_key=api_key,
        rate_limit_per_minute=10,  # Conservative rate limiting
        timeout_seconds=30,
        retry_attempts=3,
        enabled=True
    )
    return TheOddsAPICrawler(config)


def create_sportsdata_io_crawler(api_key: str) -> SportsDataIOCrawler:
    """Create a pre-configured SportsData.io crawler."""
    config = CrawlerConfig(
        name="sportsdata_io",
        source_type=DataSourceType.API,
        base_url="https://api.sportsdata.io",
        api_key=api_key,
        rate_limit_per_minute=60,  # Higher rate limit
        timeout_seconds=30,
        retry_attempts=3,
        enabled=True
    )
    return SportsDataIOCrawler(config)
