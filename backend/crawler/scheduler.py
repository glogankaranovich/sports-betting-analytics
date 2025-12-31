"""
Data collection automation for sports betting analytics.

This module provides execution logic for automated data collection,
designed to be triggered by external schedulers (CloudWatch Events, API calls).
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .__init__ import SportsCrawlerService
from .data_processor import create_data_processor
from .reddit_crawler import RedditCrawler
# Note: RefereeCrawler moved to separate Lambda function

logger = logging.getLogger(__name__)


class DataCollectionExecutor:
    """Executes data collection tasks when triggered externally."""
    
    def __init__(self):
        self.crawler_service = SportsCrawlerService()
        self.data_processor = create_data_processor()
        self.reddit_crawler = RedditCrawler()
        # Note: RefereeCrawler now runs as separate Lambda function
    
    async def collect_all_sports(self) -> Dict[str, Any]:
        """Collect data for all default sports."""
        sports = self.crawler_service.config_manager.settings.default_sports
        return await self.collect_sports(sports)
    
    async def collect_sports(self, sports: List[str]) -> Dict[str, Any]:
        """Collect and store data for specified sports."""
        start_time = datetime.utcnow()
        logger.info(f"Starting data collection for sports: {sports}")
        
        # Skip actual collection in dev environment
        stage = os.getenv('STAGE', 'dev')
        if stage == 'dev':
            logger.info("Dev environment detected - skipping actual data collection")
            return {
                "success": True,
                "execution_time_seconds": 0.1,
                "sports_processed": len(sports),
                "total_events_stored": 0,
                "processing_results": {sport: {"message": "Skipped in dev environment"} for sport in sports},
                "executed_at": start_time.isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
                "dev_mode": True
            }
        
        # Lambda timeout safety - limit to 12 minutes max
        timeout_seconds = 12 * 60  # 12 minutes (3 min buffer)
        
        try:
            # Collect data from all sources with timeout
            results = await asyncio.wait_for(
                self.crawler_service.collect_sports_data(sports),
                timeout=timeout_seconds
            )
            
            # Process and store data
            processing_results = {}
            total_stored = 0
            
            for sport, events in results.items():
                if events:
                    stats = await self.data_processor.process_and_store(events, sport)
                    processing_results[sport] = self.data_processor.get_processing_summary(stats)
                    total_stored += stats.stored_events
                else:
                    processing_results[sport] = {"message": "No events collected"}
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            summary = {
                "success": True,
                "execution_time_seconds": round(execution_time, 2),
                "sports_processed": len(sports),
                "total_events_stored": total_stored,
                "processing_results": processing_results,
                "executed_at": start_time.isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
                "timeout_limit_seconds": timeout_seconds
            }
            
            logger.info(f"Collection completed: {total_stored} events stored in {execution_time:.1f}s")
            return summary
            
        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            timeout_summary = {
                "success": False,
                "error": f"Collection timed out after {timeout_seconds} seconds",
                "execution_time_seconds": round(execution_time, 2),
                "sports_requested": sports,
                "executed_at": start_time.isoformat(),
                "timed_out_at": datetime.utcnow().isoformat()
            }
            
            logger.error(f"Collection timed out after {execution_time:.1f}s")
            return timeout_summary
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_summary = {
                "success": False,
                "error": str(e),
                "execution_time_seconds": round(execution_time, 2),
                "sports_requested": sports,
                "executed_at": start_time.isoformat(),
                "failed_at": datetime.utcnow().isoformat()
            }
            
            logger.error(f"Collection failed after {execution_time:.1f}s: {e}")
            return error_summary
    
    async def collect_reddit_insights(self) -> Dict[str, Any]:
        """Collect betting insights from Reddit discussions."""
        start_time = datetime.utcnow()
        logger.info("Starting Reddit insights collection")
        
        # Skip actual collection in dev environment
        stage = os.getenv('STAGE', 'dev')
        if stage == 'dev':
            logger.info("Dev environment detected - skipping actual Reddit collection")
            return {
                "success": True,
                "execution_time_seconds": 0.1,
                "insights_collected": 0,
                "insights_stored": 0,
                "executed_at": start_time.isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
                "dev_mode": True
            }
        
        try:
            insights = await self.reddit_crawler.crawl_betting_insights()
            
            # Store insights in DynamoDB (convert to dict format)
            insight_events = []
            for insight in insights:
                event_data = {
                    "id": f"reddit_{insight.post_id}",
                    "sport": insight.sport,
                    "teams": insight.teams,
                    "bet_type": insight.bet_type,
                    "confidence": insight.confidence,
                    "reasoning": insight.reasoning,
                    "source": "reddit",
                    "source_url": insight.source_url,
                    "created_at": insight.created_at.isoformat()
                }
                insight_events.append(event_data)
            
            # Store using data processor
            if insight_events:
                stats = await self.data_processor.process_and_store(insight_events, "reddit_insights")
                stored_count = stats.stored_events
            else:
                stored_count = 0
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            summary = {
                "success": True,
                "execution_time_seconds": round(execution_time, 2),
                "insights_collected": len(insights),
                "insights_stored": stored_count,
                "executed_at": start_time.isoformat(),
                "completed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Reddit collection completed: {stored_count} insights stored in {execution_time:.1f}s")
            return summary
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_summary = {
                "success": False,
                "error": str(e),
                "execution_time_seconds": round(execution_time, 2),
                "executed_at": start_time.isoformat(),
                "failed_at": datetime.utcnow().isoformat()
            }
            
            logger.error(f"Reddit collection failed after {execution_time:.1f}s: {e}")
            return error_summary

    async def collect_referee_data(self) -> Dict[str, Any]:
        """Collect and store referee statistics and bias metrics.
        
        Note: This method is deprecated. Referee data collection now runs
        as a separate Lambda function (RefereeCrawlerFunction).
        """
        logger.warning("Referee data collection moved to separate Lambda function")
        return {
            "status": "deprecated",
            "message": "Referee data collection now runs as separate Lambda function",
            "referee_events": 0,
            "execution_time": 0
        }


# Lambda handler function
async def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for scheduled data collection.
    
    Event structure:
    {
        "collection_type": "sports" | "reddit" | "referees",  # Type of collection
        "sports": ["nfl", "nba"],  # Optional for sports collection
        "source": "cloudwatch-event"  # Optional, for tracking trigger source
    }
    """
    executor = DataCollectionExecutor()
    
    # Check collection type
    collection_type = event.get('collection_type', 'sports')
    
    if collection_type == 'reddit':
        result = await executor.collect_reddit_insights()
    elif collection_type == 'referees':
        result = await executor.collect_referee_data()
    elif collection_type == 'sports':
        # Extract sports from event, or use defaults
        sports = event.get('sports')
        if sports:
            result = await executor.collect_sports(sports)
        else:
            result = await executor.collect_all_sports()
    else:
        result = {
            "success": False,
            "error": f"Unknown collection type: {collection_type}",
            "supported_types": ["sports", "reddit", "referees"]
        }
    
    # Add event context to result
    result['trigger_source'] = event.get('source', 'unknown')
    result['lambda_request_id'] = getattr(context, 'aws_request_id', 'unknown')
    result['collection_type'] = collection_type
    
    return result


# Factory function for API usage
def create_executor() -> DataCollectionExecutor:
    """Create a data collection executor."""
    return DataCollectionExecutor()
