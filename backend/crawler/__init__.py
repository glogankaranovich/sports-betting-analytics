"""
Crawler initialization and usage examples.

This module demonstrates how to set up and use the crawler system
for collecting sports data from various sources.
"""

import asyncio
import logging
from typing import List, Dict, Any
from .base_crawler import CrawlerManager, TheOddsAPICrawler, SportsDataIOCrawler, SportEvent, create_the_odds_api_crawler, create_sportsdata_io_crawler
from .config import CrawlerConfigManager
from .reddit_crawler import RedditCrawler
from .referee_crawler import RefereeCrawler, RefereeStats

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SportsCrawlerService:
    """High-level service for managing sports data collection."""
    
    def __init__(self):
        self.config_manager = CrawlerConfigManager()
        self.crawler_manager = CrawlerManager()
        self._initialize_crawlers()
    
    def _initialize_crawlers(self):
        """Initialize crawlers based on configuration."""
        enabled_configs = self.config_manager.get_enabled_crawlers()
        
        for name, config in enabled_configs.items():
            if name == 'sportsdata_io':
                crawler = SportsDataIOCrawler(config)
                self.crawler_manager.add_crawler(crawler)
            elif name == 'the_odds_api':
                crawler = TheOddsAPICrawler(config)
                self.crawler_manager.add_crawler(crawler)
            # Add other crawler types here as they're implemented
            
        logger.info(f"Initialized {len(enabled_configs)} crawlers")
    
    async def collect_sports_data(self, sports: List[str] = None) -> Dict[str, List[SportEvent]]:
        """Collect data for specified sports (or default sports)."""
        if sports is None:
            sports = self.config_manager.settings.default_sports
        
        logger.info(f"Starting data collection for sports: {sports}")
        
        try:
            results = await self.crawler_manager.collect_all_data(sports)
            
            # Log collection summary
            total_events = sum(len(events) for events in results.values())
            logger.info(f"Collected {total_events} events across {len(sports)} sports")
            
            for sport, events in results.items():
                logger.info(f"  {sport}: {len(events)} events")
            
            return results
            
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            raise
    
    async def get_available_sports(self) -> Dict[str, List[str]]:
        """Get available sports from all crawlers."""
        results = {}
        
        for name, crawler in self.crawler_manager.crawlers.items():
            try:
                async with crawler:
                    sports = await crawler.get_available_sports()
                    results[name] = sports
            except Exception as e:
                logger.error(f"Failed to get sports from {name}: {e}")
                results[name] = []
        
        return results
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of the crawler service."""
        return {
            'config': self.config_manager.get_config_summary(),
            'crawlers': self.crawler_manager.get_crawler_status(),
        }


# Example usage functions
async def example_basic_collection():
    """Example: Basic data collection."""
    print("=== Basic Data Collection Example ===")
    
    service = SportsCrawlerService()
    
    # Collect data for default sports
    results = await service.collect_sports_data()
    
    # Display results
    for sport, events in results.items():
        print(f"\n{sport.upper()}:")
        for event in events[:3]:  # Show first 3 events
            print(f"  {event.away_team} @ {event.home_team}")
            print(f"  Start: {event.commence_time}")
            print(f"  Bookmakers: {len(event.bookmaker_odds)}")


async def example_specific_sports():
    """Example: Collect data for specific sports."""
    print("=== Specific Sports Collection Example ===")
    
    service = SportsCrawlerService()
    
    # Collect only NFL and NBA data
    results = await service.collect_sports_data(['nfl', 'nba'])
    
    for sport, events in results.items():
        print(f"\n{sport.upper()}: {len(events)} events")


async def example_crawler_status():
    """Example: Check crawler status."""
    print("=== Crawler Status Example ===")
    
    service = SportsCrawlerService()
    status = service.get_service_status()
    
    print("Configuration:")
    print(f"  Default sports: {status['config']['settings']['default_sports']}")
    print(f"  Collection interval: {status['config']['settings']['collection_interval_minutes']} minutes")
    
    print("\nCrawlers:")
    for name, info in status['config']['crawlers'].items():
        print(f"  {name}: {'enabled' if info['enabled'] else 'disabled'}")
        print(f"    Type: {info['source_type']}")
        print(f"    Rate limit: {info['rate_limit_per_minute']}/min")
        print(f"    Has API key: {info['has_api_key']}")


async def example_available_sports():
    """Example: Get available sports from all sources."""
    print("=== Available Sports Example ===")
    
    service = SportsCrawlerService()
    available_sports = await service.get_available_sports()
    
    for source, sports in available_sports.items():
        print(f"\n{source.upper()}:")
        for sport in sports[:10]:  # Show first 10 sports
            print(f"  - {sport}")
        if len(sports) > 10:
            print(f"  ... and {len(sports) - 10} more")


# Main function for testing
async def main():
    """Run all examples."""
    try:
        await example_crawler_status()
        await example_available_sports()
        await example_basic_collection()
        await example_specific_sports()
    except Exception as e:
        logger.error(f"Example failed: {e}")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
