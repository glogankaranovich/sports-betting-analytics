"""Lambda handler for daily coaching memo generation."""

import json
import os

import boto3

TABLE_NAME = os.environ.get("BETS_TABLE", "carpool-bets-v2-dev")
table = boto3.resource("dynamodb").Table(TABLE_NAME)

ACTIVE_MODELS = ["BENNY", "BENNY_V3"]


def lambda_handler(event, context):
    from benny.coaching_agent import CoachingAgent

    models = event.get("models", ACTIVE_MODELS)
    results = {}

    for pk in models:
        try:
            coach = CoachingAgent(table, pk)
            memo = coach.generate_memo()
            results[pk] = {"status": "ok", "length": len(memo)} if memo else {"status": "skipped", "reason": "empty memo"}
            print(f"[{pk}] Generated memo ({len(memo)} chars)" if memo else f"[{pk}] No memo generated")
        except Exception as e:
            results[pk] = {"status": "error", "error": str(e)}
            print(f"[{pk}] Error: {e}")

    return {"statusCode": 200, "body": json.dumps(results)}
