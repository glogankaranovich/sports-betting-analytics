import boto3
import json
import os
from datetime import datetime, timedelta


def test_odds_collector_integration():
    """Test odds collector Lambda function"""

    environment = os.getenv("ENVIRONMENT", "dev")
    table_name = f"carpool-bets-v2-{environment}"

    lambda_client = boto3.client("lambda", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    # Find the Lambda function
    functions_response = lambda_client.list_functions()
    lambda_function_name = None

    for func in functions_response["Functions"]:
        if "OddsCollectorFunction" in func["FunctionName"]:
            lambda_function_name = func["FunctionName"]
            break

    if not lambda_function_name:
        raise Exception("Could not find OddsCollectorFunction Lambda")

    print(f"Testing odds collector: {lambda_function_name}")

    print("Testing odds collection with limit=2...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"sport": "basketball_nba", "limit": 2}),
    )

    payload = json.loads(response["Payload"].read())
    assert response["StatusCode"] == 200, f"Lambda failed: {response['StatusCode']}"
    assert payload["statusCode"] == 200, f"Function failed: {payload.get('body')}"

    body = json.loads(payload["body"])
    print(f"✓ Odds collection result: {body['message']}")

    # Get the game IDs that were processed
    game_ids = body.get("game_ids", [])
    print(f"📋 Game IDs processed: {game_ids}")

    # Verify Lambda returned game IDs (proves it's working)
    assert len(game_ids) > 0, "Lambda should return game IDs of processed games"
    print(f"✓ Lambda successfully returned {len(game_ids)} game IDs")

    # Verify the specific games exist in the main table
    print(f"🔍 Verifying {len(game_ids)} specific games exist in database...")
    for game_id in game_ids[:2]:  # Check first 2 games
        # Try to get the game directly from main table
        game_response = table.get_item(
            Key={
                "pk": f"GAME#{game_id}",
                "sk": "fanduel#h2h#LATEST",  # Try the most common market/bookmaker combo
            }
        )
        if "Item" not in game_response:
            # Try other combinations if fanduel#h2h doesn't exist
            for bookmaker in ["draftkings", "betmgm", "caesars"]:
                game_response = table.get_item(
                    Key={"pk": f"GAME#{game_id}", "sk": f"{bookmaker}#h2h#LATEST"}
                )
                if "Item" in game_response:
                    break

        assert "Item" in game_response, f"Game {game_id} not found in database"

        # Verify the record was updated recently (within last 5 minutes)
        item = game_response["Item"]
        updated_at = item.get("updated_at")
        if updated_at:
            updated_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            time_diff = datetime.now(updated_time.tzinfo) - updated_time
            assert time_diff < timedelta(
                minutes=5
            ), f"Game {game_id} was not updated recently (updated {time_diff} ago)"

    print(
        f"✓ Verified {min(len(game_ids), 2)} processed games exist and were updated recently"
    )

    return True


def test_props_collector_integration():
    """Test props collector Lambda function"""

    _ = os.getenv("ENVIRONMENT", "dev")  # Environment for function discovery
    lambda_client = boto3.client("lambda", region_name="us-east-1")

    # Find the Lambda function
    functions_response = lambda_client.list_functions()
    lambda_function_name = None

    for func in functions_response["Functions"]:
        if "OddsCollectorFunction" in func["FunctionName"]:
            lambda_function_name = func["FunctionName"]
            break

    if not lambda_function_name:
        raise Exception("Could not find OddsCollectorFunction Lambda")

    print(f"Testing props collector: {lambda_function_name}")

    print("Testing props collection with limit=1...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"sport": "basketball_nba", "props_only": True, "limit": 1}),
    )

    payload = json.loads(response["Payload"].read())
    assert response["StatusCode"] == 200, f"Lambda failed: {response['StatusCode']}"
    assert payload["statusCode"] == 200, f"Function failed: {payload.get('body')}"

    body = json.loads(payload["body"])
    print(f"✓ Props collection result: {body['message']}")

    return True


def test_prediction_generator_integration():
    """Test prediction generator Lambda function"""

    _ = os.getenv("ENVIRONMENT", "dev")  # Environment for function discovery
    lambda_client = boto3.client("lambda", region_name="us-east-1")

    # Find the Lambda function
    functions_response = lambda_client.list_functions()
    lambda_function_name = None

    for func in functions_response["Functions"]:
        if "PredictionGenerator" in func["FunctionName"]:
            lambda_function_name = func["FunctionName"]
            break

    if not lambda_function_name:
        print("⚠️  PredictionGenerator function not found - skipping test")
        return True

    print(f"Testing prediction generator: {lambda_function_name}")

    # Test game predictions
    print("Testing game predictions with limit=2...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(
            {
                "sport": "basketball_nba",
                "bet_type": "games",
                "model": "consensus",
                "limit": 2,
            }
        ),
    )

    payload = json.loads(response["Payload"].read())
    assert response["StatusCode"] == 200, f"Lambda failed: {response['StatusCode']}"
    assert payload["statusCode"] == 200, f"Function failed: {payload.get('body')}"

    body = json.loads(payload["body"])
    print(f"✓ Game predictions result: {body['message']}")

    # Test prop predictions
    print("Testing prop predictions with limit=2...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(
            {
                "sport": "basketball_nba",
                "bet_type": "props",
                "model": "consensus",
                "limit": 2,
            }
        ),
    )

    payload = json.loads(response["Payload"].read())
    assert response["StatusCode"] == 200, f"Lambda failed: {response['StatusCode']}"
    assert payload["statusCode"] == 200, f"Function failed: {payload.get('body')}"

    body = json.loads(payload["body"])
    print(f"✓ Prop predictions result: {body['message']}")

    return True


def test_lambda_integration():
    """Run all integration tests"""

    print("🧪 Running collector integration tests...\n")

    try:
        print("1. Testing Odds Collector...")
        test_odds_collector_integration()
        print()

        print("2. Testing Props Collector...")
        test_props_collector_integration()
        print()

        print("3. Testing Prediction Generator...")
        test_prediction_generator_integration()
        print()

        print("✅ All collector integration tests passed!")
        return True

    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        test_lambda_integration()
        print("\n🎉 All integration tests passed!")
    except Exception as e:
        print(f"\n❌ Integration tests failed: {str(e)}")
        exit(1)
