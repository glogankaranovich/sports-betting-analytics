"""
User Model Queue Loader - Loads active user models into SQS queue for execution
"""
import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")

USER_MODELS_TABLE = os.environ.get(
    "USER_MODELS_TABLE", "Dev-UserModels-UserModelsTable"
)
MODEL_EXECUTION_QUEUE_URL = os.environ.get("MODEL_EXECUTION_QUEUE_URL")

user_models_table = dynamodb.Table(USER_MODELS_TABLE)


def get_all_active_models():
    """
    Scan for all active user models
    """
    models = []

    # Scan table for active models
    response = user_models_table.scan(
        FilterExpression="#status = :active",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":active": "active"},
    )

    models.extend(response.get("Items", []))

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = user_models_table.scan(
            FilterExpression="#status = :active",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":active": "active"},
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        models.extend(response.get("Items", []))

    return models


def load_models_to_queue(models):
    """
    Load models into SQS queue in batches
    """
    if not models:
        print("No active models to process")
        return 0

    # Send messages in batches of 10 (SQS limit)
    batch_size = 10
    total_sent = 0

    for i in range(0, len(models), batch_size):
        batch = models[i : i + batch_size]

        entries = []
        for idx, model in enumerate(batch):
            entries.append(
                {
                    "Id": str(idx),
                    "MessageBody": json.dumps(
                        {"model_id": model["model_id"], "user_id": model["user_id"]}
                    ),
                }
            )

        # Send batch to SQS
        response = sqs.send_message_batch(
            QueueUrl=MODEL_EXECUTION_QUEUE_URL, Entries=entries
        )

        successful = len(response.get("Successful", []))
        failed = len(response.get("Failed", []))

        total_sent += successful

        if failed > 0:
            print(f"Failed to send {failed} messages")

    return total_sent


def handler(event, context):
    """
    Lambda handler - runs on schedule to load models into queue
    """
    print("Loading active user models into execution queue")

    # Get all active models
    models = get_all_active_models()
    print(f"Found {len(models)} active models")

    # Load into SQS queue
    sent = load_models_to_queue(models)
    print(f"Loaded {sent} models into queue")

    return {
        "statusCode": 200,
        "body": json.dumps({"models_found": len(models), "models_queued": sent}),
    }
