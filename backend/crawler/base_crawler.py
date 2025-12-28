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
class SportEvent:
    """Standardized sports event data structure."""
    event_id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker_odds: List[Dict[str, Any]]
    source: str
    collected_at: datetime


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
                    source=self.config.name,
                    collected_at=datetime.utcnow()
                )
                events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse game data: {e}")
                continue
        
        return events


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


# Factory function for creating pre-configured crawlers
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
