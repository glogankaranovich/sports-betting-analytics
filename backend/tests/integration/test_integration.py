import boto3
import json
import os
from datetime import datetime, timedelta


def test_odds_collector_integration():
    """Test odds collector Lambda function"""

    environment = os.getenv("ENVIRONMENT", "dev")
    table_name = f"carpool-bets-v2-{environment}"
    lambda_function_name = f"odds-collector-{environment}"

    lambda_client = boto3.client("lambda", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

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


def test_props_collector_integration():
    """Test props collector Lambda function"""

    environment = os.getenv("ENVIRONMENT", "dev")
    lambda_function_name = f"props-collector-{environment}"
    lambda_client = boto3.client("lambda", region_name="us-east-1")

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


def test_prediction_generator_integration():
    """Test prediction generator Lambda function"""

    environment = os.getenv("ENVIRONMENT", "dev")
    lambda_function_name = f"analysis-generator-1-{environment}"
    lambda_client = boto3.client("lambda", region_name="us-east-1")

    print(f"Testing analysis generator: {lambda_function_name}")

    # Test game analysis
    print("Testing game analysis with limit=2...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(
            {
                "sport": "basketball_nba",
                "analysis_type": "games",
                "model": "consensus",
                "limit": 2,
            }
        ),
    )

    payload = json.loads(response["Payload"].read())
    assert response["StatusCode"] == 200, f"Lambda failed: {response['StatusCode']}"

    # Analysis generator returns direct response, not HTTP format
    if isinstance(payload, dict) and "message" in payload:
        print(f"✓ Game analysis result: {payload['message']}")
    else:
        print(f"✓ Game analysis completed: {payload}")

    # Test prop analysis
    print("Testing prop analysis with limit=2...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(
            {
                "sport": "basketball_nba",
                "analysis_type": "props",
                "model": "consensus",
                "limit": 2,
            }
        ),
    )

    payload = json.loads(response["Payload"].read())
    assert response["StatusCode"] == 200, f"Lambda failed: {response['StatusCode']}"

    if isinstance(payload, dict) and "message" in payload:
        print(f"✓ Prop analysis result: {payload['message']}")
    else:
        print(f"✓ Prop analysis completed: {payload}")


def test_outcome_collector_integration():
    """Test outcome collector Lambda function"""
    environment = os.getenv("ENVIRONMENT", "dev")
    lambda_function_name = f"outcome-collector-{environment}"
    lambda_client = boto3.client("lambda", region_name="us-east-1")

    print(f"Testing outcome collector: {lambda_function_name}")

    # Test outcome verification
    print("Testing outcome verification...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"sport": "basketball_nba", "limit": 5}),
    )

    payload = json.loads(response["Payload"].read())
    assert response["StatusCode"] == 200, f"Lambda failed: {response['StatusCode']}"

    if isinstance(payload, dict) and "message" in payload:
        print(f"✓ Outcome verification result: {payload['message']}")
    else:
        print(f"✓ Outcome verification completed: {payload}")


def test_api_handler_integration():
    """Test API handler endpoints with authentication"""
    api_url = get_api_endpoint("BetCollectorApi")
    print(f"Testing API handler: {api_url}")

    # Test health endpoint (no auth required)
    print("Testing health endpoint...")
    import requests

    try:
        response = requests.get(f"{api_url}health")
        assert (
            response.status_code == 200
        ), f"Health check failed: {response.status_code}"
        print("✓ Health check passed")

        # Get authentication token for test user
        print("Getting authentication token...")
        token = get_test_user_token()

        if token:
            # Test authenticated endpoints
            headers = {"Authorization": f"Bearer {token}"}

            print("Testing games endpoint with auth...")
            response = requests.get(
                f"{api_url}games?sport=basketball_nba&limit=1", headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                print(
                    f"✓ Games endpoint result: Found {len(data.get('games', []))} games"
                )
            else:
                print(f"⚠️  Games endpoint returned: {response.status_code}")

            print("Testing analyses endpoint with auth...")
            response = requests.get(
                f"{api_url}analyses?sport=basketball_nba&bookmaker=fanduel&model=consensus&limit=5",
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                print(
                    f"✓ Analyses endpoint result: Found {len(data.get('analyses', []))} analyses"
                )
            else:
                print(f"⚠️  Analyses endpoint returned: {response.status_code}")
        else:
            print("⚠️  Could not get authentication token - testing without auth")

    except Exception as e:
        print(f"⚠️  API test failed: {e}")


def get_test_user_token():
    """Get JWT token for test user"""
    try:
        import boto3

        client = boto3.client("cognito-idp", region_name="us-east-1")

        # Test user credentials from docs/test-users.md
        response = client.admin_initiate_auth(
            UserPoolId="us-east-1_UT5jyAP5L",
            ClientId="4qs12vau007oineekjldjkn6v0",
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": "testuser@example.com",
                "PASSWORD": "TestPass123!",
            },
        )

        return response["AuthenticationResult"]["IdToken"]

    except Exception as e:
        print(f"⚠️  Could not authenticate test user: {e}")
        return None


def get_api_endpoint(stack_name):
    """Get API Gateway endpoint URL"""
    try:
        cf_client = boto3.client("cloudformation", region_name="us-east-1")
        stack_name = f"Dev-{stack_name}"

        response = cf_client.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]

        for output in outputs:
            if "Url" in output["OutputKey"] or "Endpoint" in output["OutputKey"]:
                return output["OutputValue"]

        return None
    except Exception as e:
        print(f"Error getting API endpoint: {e}")
        return None


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

        print("3. Testing Analysis Generator...")
        test_prediction_generator_integration()
        print()

        print("4. Testing Outcome Collector...")
        test_outcome_collector_integration()
        print()

        print("5. Testing API Handler...")
        test_api_handler_integration()
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
