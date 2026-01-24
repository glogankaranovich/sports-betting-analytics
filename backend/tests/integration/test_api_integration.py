import requests
import os
import boto3
import pytest


def get_cognito_token(
    user_pool_id: str, client_id: str, username: str, password: str
) -> str:
    """Get JWT ID token from Cognito for testing"""
    cognito = boto3.client("cognito-idp", region_name="us-east-1")

    try:
        response = cognito.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        # Return ID token instead of access token for API Gateway
        return response["AuthenticationResult"]["IdToken"]
    except Exception as e:
        print(f"Failed to get Cognito token: {e}")
        raise


def test_api_integration():
    """Integration test to verify API endpoints work with real AWS resources and auth"""

    # Get environment-specific resources
    environment = os.getenv("ENVIRONMENT", "dev")
    environment_title = environment.title()

    # Get API URL and Cognito details from CloudFormation stack outputs
    cloudformation = boto3.client("cloudformation", region_name="us-east-1")

    try:
        # Get the API URL from BetCollectorApi stack
        api_stack_name = f"{environment_title}-BetCollectorApi"
        api_response = cloudformation.describe_stacks(StackName=api_stack_name)

        api_url = None
        for output in api_response["Stacks"][0]["Outputs"]:
            if output["OutputKey"] == "BetCollectorApiUrl":
                api_url = output["OutputValue"].rstrip("/")
                break

        # Get Cognito details from Auth stack
        auth_stack_name = f"{environment_title}-Auth"
        auth_response = cloudformation.describe_stacks(StackName=auth_stack_name)

        user_pool_id = None
        client_id = None
        for output in auth_response["Stacks"][0]["Outputs"]:
            if output["OutputKey"] == "UserPoolId":
                user_pool_id = output["OutputValue"]
            elif output["OutputKey"] == "UserPoolClientId":
                client_id = output["OutputValue"]

        if not api_url:
            raise Exception(f"Could not find API URL in stack {api_stack_name}")
        if not user_pool_id or not client_id:
            raise Exception(
                f"Could not find Cognito details in stack {auth_stack_name}"
            )

        print(f"Testing API at: {api_url}")
        print(f"Using Cognito User Pool: {user_pool_id}")

        # Test health endpoint (public)
        print("Testing /health endpoint...")
        health_response = requests.get(f"{api_url}/health", timeout=10)
        assert (
            health_response.status_code == 200
        ), f"Health check failed: {health_response.status_code}"

        health_data = health_response.json()
        assert health_data["status"] == "healthy", "Health status not healthy"
        assert (
            health_data["environment"] == environment
        ), f"Environment mismatch: {health_data['environment']}"
        print(f"✅ Health check passed: {health_data}")

        # Test protected endpoints without auth (should return 401)
        print("Testing protected endpoints without auth (should fail)...")
        games_response = requests.get(f"{api_url}/games", timeout=10)
        assert (
            games_response.status_code == 401
        ), f"Expected 401 Unauthorized, got: {games_response.status_code}"
        print("✅ Protected endpoints correctly require authentication")

        # Get JWT token using test user
        print("Getting JWT token for test user...")
        test_email = "testuser@example.com"
        test_password = "TestPass123!"

        try:
            token = get_cognito_token(
                user_pool_id, client_id, test_email, test_password
            )
            print("✅ Successfully obtained JWT token")
        except Exception as e:
            print(f"❌ Failed to get JWT token: {e}")
            print("Note: Test user may not exist in this environment yet")
            pytest.skip("Test user not configured in this environment")

        # Test protected endpoints with auth (should work)
        headers = {
            "Authorization": token
        }  # API Gateway Cognito authorizer expects token directly

        print("Testing /games endpoint with auth...")
        auth_games_response = requests.get(
            f"{api_url}/games?sport=basketball_nba", headers=headers, timeout=10
        )
        assert (
            auth_games_response.status_code == 200
        ), f"Authenticated games request failed: {auth_games_response.status_code} - {auth_games_response.text}"

        games_data = auth_games_response.json()
        assert "games" in games_data, "Games data missing"
        print(
            f"✅ Authenticated games endpoint passed: Found {games_data['count']} games"
        )

        print("Testing /sports endpoint with auth...")
        auth_sports_response = requests.get(
            f"{api_url}/sports", headers=headers, timeout=10
        )
        assert (
            auth_sports_response.status_code == 200
        ), f"Authenticated sports request failed: {auth_sports_response.status_code}"

        sports_data = auth_sports_response.json()
        assert "sports" in sports_data, "Sports data missing"
        print(
            f"✅ Authenticated sports endpoint passed: Found {sports_data['count']} sports"
        )

        print("Testing /bookmakers endpoint with auth...")
        auth_bookmakers_response = requests.get(
            f"{api_url}/bookmakers", headers=headers, timeout=10
        )
        assert (
            auth_bookmakers_response.status_code == 200
        ), f"Authenticated bookmakers request failed: {auth_bookmakers_response.status_code}"

        bookmakers_data = auth_bookmakers_response.json()
        assert "bookmakers" in bookmakers_data, "Bookmakers data missing"
        print(
            f"✅ Authenticated bookmakers endpoint passed: Found {bookmakers_data['count']} bookmakers"
        )

        # Test analyses endpoint
        print("Testing /analyses endpoint with auth...")
        auth_analyses_response = requests.get(
            f"{api_url}/analyses?sport=basketball_nba&bookmaker=fanduel&model=consensus&limit=5",
            headers=headers,
            timeout=10,
        )
        assert (
            auth_analyses_response.status_code == 200
        ), f"Authenticated analyses request failed: {auth_analyses_response.status_code} - {auth_analyses_response.text}"

        analyses_data = auth_analyses_response.json()
        assert "analyses" in analyses_data, "Analyses data missing"
        print(
            f"✅ Authenticated analyses endpoint passed: Found {analyses_data['count']} analyses"
        )

        if analyses_data["count"] > 0:
            sample = analyses_data["analyses"][0]
            print(f"   Sample: {sample['home_team']} vs {sample['away_team']}")
            print(f"   Prediction: {sample['prediction']}")
            print(f"   Confidence: {sample['confidence']}")

        # Test insights endpoint
        print("Testing /insights endpoint with auth...")
        insights_response = requests.get(
            f"{api_url}/insights?sport=basketball_nba&bookmaker=fanduel&model=consensus&limit=5",
            headers=headers,
            timeout=10,
        )
        assert (
            insights_response.status_code == 200
        ), f"Insights request failed: {insights_response.status_code} - {insights_response.text}"

        insights_data = insights_response.json()
        assert "insights" in insights_data, "Insights data missing"
        print(f"✅ Insights endpoint passed: Found {insights_data['count']} insights")

        # Test player props endpoint
        print("Testing /player-props endpoint with auth...")
        player_props_response = requests.get(
            f"{api_url}/player-props?sport=basketball_nba&limit=5",
            headers=headers,
            timeout=10,
        )
        assert (
            player_props_response.status_code == 200
        ), f"Player props request failed: {player_props_response.status_code} - {player_props_response.text}"

        player_props_data = player_props_response.json()
        assert "props" in player_props_data, "Player props data missing"
        print(
            f"✅ Player props endpoint passed: Found {player_props_data['count']} player props"
        )

        print("✅ All API integration tests passed!")

    except Exception as e:
        print(f"❌ API integration test failed: {e}")
        raise


if __name__ == "__main__":
    try:
        test_api_integration()
        print("\n✅ All API integration tests passed!")
        exit(0)
    except Exception as e:
        print(f"\n❌ API integration tests failed: {e}")
        exit(1)
