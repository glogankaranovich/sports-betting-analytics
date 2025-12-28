"""
Data processing and validation for sports betting data.

This module handles validation, transformation, and storage of collected
sports data into the appropriate database tables.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
import json

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, ValidationError, Field

from .base_crawler import SportEvent

logger = logging.getLogger(__name__)


class BookmakerOdds(BaseModel):
    """Validated bookmaker odds data."""
    bookmaker_key: str = Field(..., min_length=1)
    bookmaker_title: str = Field(..., min_length=1)
    last_update: datetime
    markets: List[Dict[str, Any]] = Field(default_factory=list)


class ValidatedSportEvent(BaseModel):
    """Validated sports event with proper data types."""
    event_id: str = Field(..., min_length=1)
    sport: str = Field(..., min_length=1)
    home_team: str = Field(..., min_length=1)
    away_team: str = Field(..., min_length=1)
    commence_time: datetime
    bookmaker_odds: List[BookmakerOdds] = Field(default_factory=list)
    source: str = Field(..., min_length=1)
    collected_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


@dataclass
class ProcessingStats:
    """Statistics from data processing operation."""
    total_events: int
    valid_events: int
    invalid_events: int
    stored_events: int
    errors: List[str]


class DataProcessor:
    """Processes and stores sports betting data."""
    
    def __init__(self, region: str = 'us-east-1', table_prefix: str = 'sports-betting'):
        self.region = region
        self.table_prefix = table_prefix
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        # Table references
        self.sports_data_table = self.dynamodb.Table(f'{table_prefix}-data-dev')  # TODO: Use stage from env
    
    async def process_and_store(self, events: List[SportEvent], sport: str) -> ProcessingStats:
        """Process and store a list of sport events."""
        stats = ProcessingStats(
            total_events=len(events),
            valid_events=0,
            invalid_events=0,
            stored_events=0,
            errors=[]
        )
        
        if not events:
            return stats
        
        # Validate events
        validated_events = []
        for event in events:
            try:
                validated_event = self._validate_event(event)
                validated_events.append(validated_event)
                stats.valid_events += 1
            except ValidationError as e:
                stats.invalid_events += 1
                stats.errors.append(f"Validation failed for event {event.event_id}: {e}")
                logger.warning(f"Event validation failed: {e}")
        
        # Store validated events
        if validated_events:
            try:
                stored_count = await self._store_events(validated_events, sport)
                stats.stored_events = stored_count
                logger.info(f"Stored {stored_count} events for {sport}")
            except Exception as e:
                stats.errors.append(f"Storage failed: {e}")
                logger.error(f"Failed to store events: {e}")
        
        return stats
    
    def _validate_event(self, event: SportEvent) -> ValidatedSportEvent:
        """Validate and transform a sport event."""
        # Parse bookmaker odds
        validated_odds = []
        for bookmaker in event.bookmaker_odds:
            try:
                odds = BookmakerOdds(
                    bookmaker_key=bookmaker.get('key', ''),
                    bookmaker_title=bookmaker.get('title', ''),
                    last_update=datetime.fromisoformat(
                        bookmaker.get('last_update', '').replace('Z', '+00:00')
                    ) if bookmaker.get('last_update') else datetime.now(timezone.utc),
                    markets=bookmaker.get('markets', [])
                )
                validated_odds.append(odds)
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid bookmaker data: {e}")
                continue
        
        # Create validated event
        return ValidatedSportEvent(
            event_id=event.event_id,
            sport=event.sport,
            home_team=event.home_team,
            away_team=event.away_team,
            commence_time=event.commence_time,
            bookmaker_odds=validated_odds,
            source=event.source,
            collected_at=event.collected_at
        )
    
    async def _store_events(self, events: List[ValidatedSportEvent], sport: str) -> int:
        """Store validated events in DynamoDB."""
        stored_count = 0
        
        # Batch write to DynamoDB
        with self.sports_data_table.batch_writer() as batch:
            for event in events:
                try:
                    # Create DynamoDB item
                    item = {
                        'data_id': f"{sport}#{event.event_id}",
                        'collected_at': event.collected_at.isoformat(),
                        'sport': event.sport,
                        'event_id': event.event_id,
                        'home_team': event.home_team,
                        'away_team': event.away_team,
                        'commence_time': event.commence_time.isoformat(),
                        'source': event.source,
                        'bookmaker_count': len(event.bookmaker_odds),
                        'bookmaker_odds': json.loads(event.json()),  # Convert to dict
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'ttl': int((datetime.now(timezone.utc).timestamp() + (30 * 24 * 3600)))  # 30 days TTL
                    }
                    
                    batch.put_item(Item=item)
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to store event {event.event_id}: {e}")
        
        return stored_count
    
    async def store_raw_data(self, data: Dict[str, Any], sport: str, source: str) -> bool:
        """Store raw API response data in S3 for backup/analysis."""
        try:
            bucket_name = f'{self.table_prefix}-raw-data-dev'  # TODO: Use stage from env
            timestamp = datetime.now(timezone.utc).strftime('%Y/%m/%d/%H')
            key = f'sports-data/{sport}/{source}/{timestamp}/{datetime.now().isoformat()}.json'
            
            self.s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=json.dumps(data, default=str),
                ContentType='application/json'
            )
            
            logger.debug(f"Stored raw data to S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to store raw data to S3: {e}")
            return False
    
    def get_processing_summary(self, stats: ProcessingStats) -> Dict[str, Any]:
        """Generate a summary of processing results."""
        success_rate = (stats.valid_events / stats.total_events * 100) if stats.total_events > 0 else 0
        storage_rate = (stats.stored_events / stats.valid_events * 100) if stats.valid_events > 0 else 0
        
        return {
            'total_events': stats.total_events,
            'valid_events': stats.valid_events,
            'invalid_events': stats.invalid_events,
            'stored_events': stats.stored_events,
            'success_rate': round(success_rate, 2),
            'storage_rate': round(storage_rate, 2),
            'error_count': len(stats.errors),
            'errors': stats.errors[:5],  # Show first 5 errors
            'processed_at': datetime.now(timezone.utc).isoformat()
        }


# Factory function
def create_data_processor(region: str = 'us-east-1', stage: str = 'dev') -> DataProcessor:
    """Create a data processor for the specified stage."""
    table_prefix = f'sports-betting'
    return DataProcessor(region=region, table_prefix=table_prefix)
