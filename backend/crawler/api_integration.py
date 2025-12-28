"""
API integration for the sports data crawler.

This module integrates the crawler system with the FastAPI backend,
providing endpoints for data collection and status monitoring.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import logging

from .base_crawler import SportEvent
from .__init__ import SportsCrawlerService

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/crawler", tags=["crawler"])

# Global crawler service instance
crawler_service = None


async def get_crawler_service() -> SportsCrawlerService:
    """Get or create the crawler service instance."""
    global crawler_service
    if crawler_service is None:
        crawler_service = SportsCrawlerService()
    return crawler_service


@router.get("/status")
async def get_crawler_status():
    """Get current status of all crawlers."""
    service = await get_crawler_service()
    return service.get_service_status()


@router.get("/sports/available")
async def get_available_sports():
    """Get list of available sports from all data sources."""
    service = await get_crawler_service()
    try:
        return await service.get_available_sports()
    except Exception as e:
        logger.error(f"Failed to get available sports: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available sports")


@router.post("/collect")
async def trigger_data_collection(
    background_tasks: BackgroundTasks,
    sports: Optional[List[str]] = None
):
    """Trigger data collection for specified sports."""
    service = await get_crawler_service()
    
    # Add collection task to background
    background_tasks.add_task(collect_and_store_data, service, sports)
    
    return {
        "message": "Data collection started",
        "sports": sports or service.config_manager.settings.default_sports,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/collect/{sport}")
async def collect_sport_data(sport: str):
    """Collect data for a specific sport immediately."""
    service = await get_crawler_service()
    
    try:
        results = await service.collect_sports_data([sport])
        events = results.get(sport, [])
        
        return {
            "sport": sport,
            "events_collected": len(events),
            "events": [
                {
                    "event_id": event.event_id,
                    "home_team": event.home_team,
                    "away_team": event.away_team,
                    "commence_time": event.commence_time.isoformat(),
                    "bookmaker_count": len(event.bookmaker_odds),
                    "source": event.source
                }
                for event in events
            ],
            "collected_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to collect data for {sport}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect data for {sport}")


async def collect_and_store_data(service: SportsCrawlerService, sports: Optional[List[str]]):
    """Background task to collect and store sports data."""
    try:
        logger.info(f"Starting background data collection for sports: {sports}")
        results = await service.collect_sports_data(sports)
        
        # TODO: Store results in database
        # This will be implemented when we add database integration
        
        total_events = sum(len(events) for events in results.values())
        logger.info(f"Background collection completed: {total_events} events collected")
        
    except Exception as e:
        logger.error(f"Background data collection failed: {e}")


# Integration with main FastAPI app
def setup_crawler_routes(app):
    """Add crawler routes to the main FastAPI app."""
    app.include_router(router)
