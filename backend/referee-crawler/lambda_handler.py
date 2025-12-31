import json
import asyncio
import logging
from typing import Dict, Any
from referee_crawler import RefereeCrawler
from config import CrawlerConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for referee data collection
    """
    try:
        logger.info(f"Starting referee crawler with event: {event}")
        
        # Initialize configuration
        config_manager = CrawlerConfigManager()
        
        # Initialize referee crawler
        crawler = RefereeCrawler(config_manager)
        
        # Extract parameters from event
        league = event.get('league', 'nfl')
        season = event.get('season', '2024')
        
        # Run the crawler
        results = await crawler.collect_referee_data(league, season)
        
        logger.info(f"Referee crawler completed successfully. Collected {len(results)} records")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Referee data collection completed successfully',
                'records_collected': len(results),
                'league': league,
                'season': season
            })
        }
        
    except Exception as e:
        logger.error(f"Error in referee crawler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Referee data collection failed'
            })
        }
