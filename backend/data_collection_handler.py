"""
Data Collection Lambda Handler
AWS Lambda function for scheduled data collection
"""

import json
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
from data_collectors.orchestrator import DataCollectionOrchestrator
from dao import BettingDAO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler for scheduled data collection"""

    try:
        # Parse event parameters
        sport = event.get("sport", "americanfootball_nfl")
        collection_type = event.get("collection_type", "all")

        logger.info(f"Starting data collection for {sport}, type: {collection_type}")

        # Get upcoming games
        games = get_upcoming_games(sport)

        if not games:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": f"No upcoming {sport} games found",
                        "sport": sport,
                        "collections_run": 0,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
            }

        logger.info(f"Found {len(games)} upcoming games")

        # Run data collection
        orchestrator = DataCollectionOrchestrator()

        # Use asyncio.run for Lambda execution
        results = asyncio.run(orchestrator.collect_all_data(sport, games))

        # Calculate summary metrics
        successful_collections = sum(1 for r in results.values() if r.success)
        total_collections = len(results)
        total_records = sum(r.records_collected for r in results.values())
        avg_quality = (
            sum(r.data_quality_score for r in results.values()) / total_collections
            if total_collections > 0
            else 0
        )

        # Prepare response
        response_body = {
            "message": "Data collection completed",
            "sport": sport,
            "games_processed": len(games),
            "collections_run": total_collections,
            "successful_collections": successful_collections,
            "failed_collections": total_collections - successful_collections,
            "total_records_collected": total_records,
            "avg_data_quality": round(avg_quality, 3),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add individual collector results for debugging
        if results:
            response_body["collector_results"] = {
                name: {
                    "success": result.success,
                    "records": result.records_collected,
                    "quality": result.data_quality_score,
                    "error": result.error,
                }
                for name, result in results.items()
            }

        status_code = (
            200 if successful_collections > 0 else 206
        )  # 206 = Partial Content

        logger.info(
            f"Collection completed: {successful_collections}/{total_collections} successful"
        )

        return {"statusCode": status_code, "body": json.dumps(response_body)}

    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": str(e),
                    "message": "Data collection failed",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        }


def get_upcoming_games(sport: str) -> list:
    """Get upcoming games from existing odds data"""
    try:
        dao = BettingDAO()

        # Get active games from the next 7 days
        # This integrates with existing odds collection system
        games = dao.get_game_ids_from_db(sport)

        # Transform to expected format
        formatted_games = []
        for game_id in games[:10]:  # Limit to 10 games for testing
            # Get game details
            game_data = dao.get_game_data(game_id)
            if game_data:
                formatted_games.append(
                    {
                        "id": game_id,
                        "sport": sport,
                        "home_team": game_data.get("home_team", ""),
                        "away_team": game_data.get("away_team", ""),
                        "commence_time": game_data.get("commence_time", ""),
                        "venue": game_data.get("venue", ""),
                        "season": game_data.get("season", ""),
                        "week": game_data.get("week", ""),
                    }
                )

        return formatted_games

    except Exception as e:
        logger.error(f"Failed to get upcoming games for {sport}: {e}")
        return []


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {"sport": "americanfootball_nfl", "collection_type": "all"}

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
