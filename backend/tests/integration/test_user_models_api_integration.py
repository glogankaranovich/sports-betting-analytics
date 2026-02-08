"""
Integration tests for user models API endpoints
"""
import boto3
import requests


def get_test_user_token():
    """Get JWT token for test user"""
    try:
        client = boto3.client("cognito-idp", region_name="us-east-1")

        # Test user credentials
        response = client.admin_initiate_auth(
            UserPoolId="us-east-1_UT5jyAP5L",
            ClientId="4qs12vau007oineekjldjkn6v0",
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": "testuser@example.com",
                "PASSWORD": "CarpoolBets2026!Secure#",
            },
        )

        return response["AuthenticationResult"]["IdToken"]
    except Exception as e:
        print(f"Could not get auth token: {e}")
        return None


def test_user_models_api():
    """Test user models API endpoints against deployed infrastructure"""
    # Get API URL from CloudFormation outputs
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "Dev-BetCollectorApi"

    try:
        response = cf_client.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]
        api_url = next(
            o["OutputValue"] for o in outputs if o["OutputKey"] == "BetCollectorApiUrl"
        )
    except Exception as e:
        print(f"❌ Could not get API URL: {e}")
        return False

    print("\n" + "=" * 60)
    print("Testing User Models API")
    print("=" * 60 + "\n")
    print(f"API URL: {api_url}")

    # Get auth token
    print("\nGetting authentication token...")
    token = get_test_user_token()
    if not token:
        print("❌ Could not get authentication token")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Test user ID for integration tests
    test_user_id = "integration_test_user"

    # 1. Test listing models (should be empty initially)
    print("\n1. Testing GET /user-models...")
    response = requests.get(
        f"{api_url}user-models", params={"user_id": test_user_id}, headers=headers
    )

    if response.status_code == 200:
        models = response.json().get("models", [])
        print(f"✓ List models successful: {len(models)} models found")
    else:
        print(f"❌ List models failed: {response.status_code} - {response.text}")
        return False

    # 2. Test creating a model
    print("\n2. Testing POST /user-models...")
    model_data = {
        "user_id": test_user_id,
        "name": "Integration Test Model",
        "description": "Created by integration test",
        "sport": "basketball_nba",
        "bet_types": ["h2h"],
        "data_sources": {
            "team_stats": {"enabled": True, "weight": 0.4},
            "odds_movement": {"enabled": True, "weight": 0.3},
            "recent_form": {"enabled": True, "weight": 0.3},
        },
        "min_confidence": 0.65,
    }

    response = requests.post(f"{api_url}user-models", json=model_data, headers=headers)

    if response.status_code == 201:
        created_model = response.json().get("model", {})
        model_id = created_model.get("model_id")
        print(f"✓ Create model successful: {model_id}")
    else:
        print(f"❌ Create model failed: {response.status_code} - {response.text}")
        return False

    # 3. Test getting specific model
    print(f"\n3. Testing GET /user-models/{model_id}...")
    response = requests.get(
        f"{api_url}user-models/{model_id}",
        params={"user_id": test_user_id},
        headers=headers,
    )

    if response.status_code == 200:
        model = response.json().get("model", {})
        print(f"✓ Get model successful: {model.get('name')}")
    else:
        print(f"❌ Get model failed: {response.status_code} - {response.text}")
        return False

    # 4. Test updating model
    print(f"\n4. Testing PUT /user-models/{model_id}...")
    update_data = {
        "user_id": test_user_id,
        "name": "Updated Integration Test Model",
        "description": "Updated by integration test",
    }

    response = requests.put(
        f"{api_url}user-models/{model_id}", json=update_data, headers=headers
    )

    if response.status_code == 200:
        updated_model = response.json().get("model", {})
        print(f"✓ Update model successful: {updated_model.get('name')}")
    else:
        print(f"❌ Update model failed: {response.status_code} - {response.text}")
        return False

    # 5. Test deleting model
    print(f"\n5. Testing DELETE /user-models/{model_id}...")
    response = requests.delete(
        f"{api_url}user-models/{model_id}",
        params={"user_id": test_user_id},
        headers=headers,
    )

    if response.status_code == 200:
        print("✓ Delete model successful")
    else:
        print(f"❌ Delete model failed: {response.status_code} - {response.text}")
        return False

    # 6. Verify model is deleted
    print("\n6. Verifying model deletion...")
    response = requests.get(
        f"{api_url}user-models/{model_id}",
        params={"user_id": test_user_id},
        headers=headers,
    )

    if response.status_code == 404:
        print("✓ Model successfully deleted (404 as expected)")
    else:
        print("❌ Model still exists after deletion")
        return False

    print("\n" + "=" * 60)
    print("✅ All user models API tests passed!")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    import sys

    success = test_user_models_api()
    sys.exit(0 if success else 1)
