"""
Base Data Collector Framework
Implements the foundation for all ML model data collectors
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import boto3
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """Result of a data collection operation"""

    success: bool
    data: Optional[Dict]
    error: Optional[str]
    timestamp: datetime
    source: str
    data_quality_score: float
    records_collected: int = 0


class BaseDataCollector(ABC):
    """Base class for all data collectors"""

    def __init__(self, name: str, update_frequency_minutes: int):
        self.name = name
        self.update_frequency = update_frequency_minutes
        self.last_update = None
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table("sports-analytics-data")

    @abstractmethod
    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect data for specified games"""
        pass

    @abstractmethod
    def validate_data(self, data: Dict) -> float:
        """Validate data quality (0-1 score)"""
        pass

    def should_update(self) -> bool:
        """Check if data should be updated based on frequency"""
        if not self.last_update:
            return True

        time_since_update = datetime.utcnow() - self.last_update
        return time_since_update.total_seconds() >= (self.update_frequency * 60)

    async def store_data(self, data: Dict, game_id: str, sport: str):
        """Store collected data in DynamoDB"""
        try:
            item = {
                "PK": f"DATA#{game_id}",
                "SK": f"{self.name.upper()}#{datetime.utcnow().isoformat()}",
                "GSI1PK": f"COLLECTOR#{self.name}",
                "GSI1SK": f"SPORT#{sport}#{datetime.utcnow().isoformat()}",
                "collector_name": self.name,
                "sport": sport,
                "game_id": game_id,
                "data": data,
                "collected_at": datetime.utcnow().isoformat(),
                "ttl": int((datetime.utcnow() + timedelta(days=90)).timestamp()),
            }

            self.table.put_item(Item=item)
            logger.info(f"Stored {self.name} data for game {game_id}")

        except Exception as e:
            logger.error(f"Failed to store {self.name} data for game {game_id}: {e}")
            raise

    def log_collection_attempt(
        self, sport: str, games_count: int, result: CollectionResult
    ):
        """Log collection attempt for monitoring"""
        log_entry = {
            "collector": self.name,
            "sport": sport,
            "games_count": games_count,
            "success": result.success,
            "data_quality_score": result.data_quality_score,
            "records_collected": result.records_collected,
            "error": result.error,
            "timestamp": result.timestamp.isoformat(),
        }

        logger.info(f"Collection attempt: {json.dumps(log_entry)}")
