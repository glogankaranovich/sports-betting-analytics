"""
Integration test for API pagination
"""
import os

import boto3
import requests

# import json


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
        return response["AuthenticationResult"]["IdToken"]
    except Exception as e:
        print(f"Failed to get Cognito token: {e}")
        raise


def test_pagination():
    """Test API pagination functionality"""
    environment = os.getenv("ENVIRONMENT", "dev")
    environment_title = environment.title()

    cloudformation = boto3.client("cloudformation", region_name="us-east-1")

    # Get API URL
    api_stack_name = f"{environment_title}-BetCollectorApi"
    api_response = cloudformation.describe_stacks(StackName=api_stack_name)
    api_url = None
    for output in api_response["Stacks"][0]["Outputs"]:
        if output["OutputKey"] == "BetCollectorApiUrl":
            api_url = output["OutputValue"].rstrip("/")
            break

    # Get Cognito details
    auth_stack_name = f"{environment_title}-Auth"
    auth_response = cloudformation.describe_stacks(StackName=auth_stack_name)
    user_pool_id = None
    client_id = None
    for output in auth_response["Stacks"][0]["Outputs"]:
        if output["OutputKey"] == "UserPoolId":
            user_pool_id = output["OutputValue"]
        elif output["OutputKey"] == "UserPoolClientId":
            client_id = output["OutputValue"]

    # Get test credentials
    test_email = "testuser@example.com"
    test_password = "TestPass123!"

    # Get auth token
    print("Getting Cognito token...")
    token = get_cognito_token(user_pool_id, client_id, test_email, test_password)
    headers = {"Authorization": token}

    print(f"\n{'='*60}")
    print("Testing /analyses endpoint pagination")
    print(f"{'='*60}")

    # Test first page
    url = f"{api_url}/analyses?sport=basketball_nba&bookmaker=fanduel&model=consensus&type=game&limit=2"
    print("\n1. Fetching first page (limit=2)...")
    response = requests.get(url, headers=headers, timeout=10)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    print(f"   ✓ Status: {response.status_code}")
    print(f"   ✓ Analyses count: {data.get('count')}")
    print(f"   ✓ Has lastEvaluatedKey: {'lastEvaluatedKey' in data}")

    assert "analyses" in data, "Response should have 'analyses' key"
    assert "count" in data, "Response should have 'count' key"

    # Test second page if pagination token exists
    if "lastEvaluatedKey" in data:
        print("\n2. Fetching second page with pagination token...")
        pagination_token = data["lastEvaluatedKey"]
        url2 = f"{url}&lastEvaluatedKey={requests.utils.quote(pagination_token)}"

        response2 = requests.get(url2, headers=headers, timeout=10)
        assert (
            response2.status_code == 200
        ), f"Expected 200, got {response2.status_code}"
        data2 = response2.json()

        print(f"   ✓ Status: {response2.status_code}")
        print(f"   ✓ Analyses count: {data2.get('count')}")

        # Verify different results
        first_page_ids = [a.get("game_id") for a in data["analyses"]]
        second_page_ids = [a.get("game_id") for a in data2["analyses"]]

        print(f"\n   First page IDs: {first_page_ids}")
        print(f"   Second page IDs: {second_page_ids}")

        # Check for overlap
        overlap = set(first_page_ids) & set(second_page_ids)
        assert not overlap, f"Pages should not overlap, but found: {overlap}"
        print("   ✓ No overlap between pages")
    else:
        print("   ℹ️  No pagination token (fewer results than limit)")

    print(f"\n{'='*60}")
    print("Testing /analyses endpoint with prop type")
    print(f"{'='*60}")

    # Test prop analysis pagination
    url = f"{api_url}/analyses?sport=basketball_nba&bookmaker=fanduel&model=consensus&type=prop&limit=2"
    print("\n1. Fetching first page of prop analyses (limit=2)...")
    response = requests.get(url, headers=headers, timeout=10)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    print(f"   ✓ Status: {response.status_code}")
    print(f"   ✓ Prop analyses count: {data.get('count')}")
    print(f"   ✓ Has lastEvaluatedKey: {'lastEvaluatedKey' in data}")

    assert "analyses" in data, "Response should have 'analyses' key"

    print(f"\n{'='*60}")
    print("Testing invalid pagination token handling")
    print(f"{'='*60}")

    # Test invalid pagination token
    url = f"{api_url}/analyses?sport=basketball_nba&bookmaker=fanduel&model=consensus&type=game&limit=2&lastEvaluatedKey=invalid"
    print("\n1. Fetching with invalid pagination token...")
    response = requests.get(url, headers=headers, timeout=10)

    # Should either return 400 or treat as first page
    print(f"   ✓ Status: {response.status_code}")
    if response.status_code == 200:
        print("   ℹ️  Invalid token treated as first page")
    else:
        print("   ℹ️  Invalid token rejected with error")

    print(f"\n{'='*60}")
    print("Testing pagination exhaustion (last page)")
    print(f"{'='*60}")

    # Test with limit larger than total results
    url = f"{api_url}/analyses?sport=basketball_nba&bookmaker=fanduel&model=consensus&type=game&limit=1000"
    print("\n1. Fetching with large limit to exhaust results...")
    response = requests.get(url, headers=headers, timeout=10)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    print(f"   ✓ Status: {response.status_code}")
    print(f"   ✓ Analyses count: {data.get('count')}")
    has_token = "lastEvaluatedKey" in data
    print(f"   ✓ Has lastEvaluatedKey: {has_token}")

    if not has_token:
        print("   ✓ No pagination token on last page (as expected)")

    print(f"\n{'='*60}")
    print("✅ All pagination tests passed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    test_pagination()
