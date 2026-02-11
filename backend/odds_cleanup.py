"""
Odds Cleanup - Removes stale odds for uncompleted games >7 days old
Runs daily to prevent database bloat from cancelled/postponed games
"""
import os
from datetime import datetime, timedelta

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
BETS_TABLE = os.environ.get("BETS_TABLE", "carpool-bets-v2-dev")
bets_table = dynamodb.Table(BETS_TABLE)


def handler(event, context):
    """Clean up stale odds for games that never completed"""
    print("Starting odds cleanup")

    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    deleted_count = 0

    try:
        # Scan for active games older than 7 days
        response = bets_table.scan(
            FilterExpression="begins_with(pk, :prefix) AND commence_time < :cutoff",
            ExpressionAttributeValues={":prefix": "GAME#", ":cutoff": cutoff},
        )

        items = response.get("Items", [])
        print(f"Found {len(items)} stale game records")

        for item in items:
            pk = item.get("pk")
            sk = item.get("sk")

            # Check if game has outcome (completed)
            game_id = pk.replace("GAME#", "")
            outcome_response = bets_table.query(
                KeyConditionExpression=Key("pk").eq(f"OUTCOME#{game_id}"), Limit=1
            )

            # If game has outcome, it was already archived - skip
            if outcome_response.get("Items"):
                continue

            # Delete stale odds record
            bets_table.delete_item(Key={"pk": pk, "sk": sk})
            deleted_count += 1

        print(f"Deleted {deleted_count} stale odds records")

        return {"statusCode": 200, "deleted_count": deleted_count}

    except Exception as e:
        print(f"Error during cleanup: {e}")
        return {"statusCode": 500, "error": str(e)}
