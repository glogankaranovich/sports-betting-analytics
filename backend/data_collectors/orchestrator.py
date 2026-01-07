"""
Data Collection Orchestrator
Coordinates all data collectors and manages parallel execution
"""

import asyncio
import logging
from typing import Dict, List
from datetime import datetime
import boto3
from .base_collector import CollectionResult
from .team_momentum_collector import TeamMomentumCollector
from .weather_collector import WeatherDataCollector
from .public_opinion_collector import PublicOpinionCollector

logger = logging.getLogger(__name__)


class DataCollectionOrchestrator:
    """Orchestrates data collection from all collectors"""

    def __init__(self):
        self.collectors = {
            "team_momentum": TeamMomentumCollector(),
            "weather": WeatherDataCollector(),
            "public_opinion": PublicOpinionCollector(),
            # Add other collectors as they're implemented
        }
        self.dynamodb = boto3.resource("dynamodb")

    async def collect_all_data(
        self, sport: str, games: List[Dict]
    ) -> Dict[str, CollectionResult]:
        """Orchestrate data collection from all active collectors"""

        if not games:
            logger.warning(f"No games provided for {sport} data collection")
            return {}

        # Determine which collectors need updates
        active_collectors = {
            name: collector
            for name, collector in self.collectors.items()
            if collector.should_update()
        }

        if not active_collectors:
            logger.info("No collectors need updates at this time")
            return {}

        logger.info(
            f"Running {len(active_collectors)} collectors for {len(games)} {sport} games"
        )

        # Run collectors in parallel
        tasks = []
        for name, collector in active_collectors.items():
            task = asyncio.create_task(
                self._run_collector_safely(collector, sport, games),
                name=f"collect_{name}",
            )
            tasks.append((name, task))

        # Wait for all collections to complete
        results = {}
        for name, task in tasks:
            try:
                result = await task
                results[name] = result

                # Store successful collections
                if result.success and result.data:
                    await self._store_collection_results(name, result, games, sport)

            except Exception as e:
                logger.error(f"Collector {name} failed with exception: {e}")
                results[name] = CollectionResult(
                    success=False,
                    data=None,
                    error=str(e),
                    timestamp=datetime.utcnow(),
                    source=name,
                    data_quality_score=0.0,
                    records_collected=0,
                )

        # Log collection summary
        await self._log_collection_summary(sport, results)

        return results

    async def _run_collector_safely(
        self, collector, sport: str, games: List[Dict]
    ) -> CollectionResult:
        """Run a collector with error handling"""
        try:
            result = await collector.collect_data(sport, games)
            collector.log_collection_attempt(sport, len(games), result)

            # Update last_update timestamp on success
            if result.success:
                collector.last_update = datetime.utcnow()

            return result

        except Exception as e:
            logger.error(f"Collector {collector.name} failed: {e}")
            return CollectionResult(
                success=False,
                data=None,
                error=str(e),
                timestamp=datetime.utcnow(),
                source=collector.name,
                data_quality_score=0.0,
                records_collected=0,
            )

    async def _store_collection_results(
        self,
        collector_name: str,
        result: CollectionResult,
        games: List[Dict],
        sport: str,
    ):
        """Store successful collection results"""
        try:
            collector = self.collectors[collector_name]

            for game in games:
                game_data = result.data.get(game["id"], {})
                if game_data:
                    await collector.store_data(game_data, game["id"], sport)

        except Exception as e:
            logger.error(f"Failed to store results for {collector_name}: {e}")

    async def _log_collection_summary(
        self, sport: str, results: Dict[str, CollectionResult]
    ):
        """Log summary of data collection run"""

        successful_collections = sum(1 for r in results.values() if r.success)
        total_records = sum(r.records_collected for r in results.values())
        avg_quality = (
            sum(r.data_quality_score for r in results.values()) / len(results)
            if results
            else 0
        )

        summary = {
            "PK": f"COLLECTION_LOG#{sport}",
            "SK": f"RUN#{datetime.utcnow().isoformat()}",
            "sport": sport,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "collectors_run": len(results),
            "successful_collections": successful_collections,
            "failed_collections": len(results) - successful_collections,
            "total_records_collected": total_records,
            "avg_data_quality": round(avg_quality, 3),
            "individual_results": {
                name: {
                    "success": result.success,
                    "data_quality_score": result.data_quality_score,
                    "records_collected": result.records_collected,
                    "error": result.error,
                }
                for name, result in results.items()
            },
        }

        # Store in DynamoDB for monitoring
        try:
            table = self.dynamodb.Table("sports-analytics-data")
            table.put_item(Item=summary)
            logger.info(
                f"Collection summary: {successful_collections}/{len(results)} successful, {total_records} records, {avg_quality:.3f} avg quality"
            )
        except Exception as e:
            logger.error(f"Failed to store collection summary: {e}")

    def get_collector_status(self) -> Dict:
        """Get status of all collectors"""
        status = {}

        for name, collector in self.collectors.items():
            status[name] = {
                "name": collector.name,
                "update_frequency_minutes": collector.update_frequency,
                "last_update": collector.last_update.isoformat()
                if collector.last_update
                else None,
                "should_update": collector.should_update(),
                "minutes_since_update": (
                    (datetime.utcnow() - collector.last_update).total_seconds() / 60
                    if collector.last_update
                    else None
                ),
            }

        return status
