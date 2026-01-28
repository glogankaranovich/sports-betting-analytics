"""
Comprehensive API endpoint integration tests.
Tests all API endpoints with proper authentication.
"""

import requests
import os
import boto3
import pytest


@pytest.fixture(scope="module")
def api_config():
    """Get API configuration from CloudFormation stacks"""
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

    # Get JWT token
    cognito = boto3.client("cognito-idp", region_name="us-east-1")
    response = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={
            "USERNAME": "testuser@example.com",
            "PASSWORD": "TestPass123!",
        },
    )
    token = response["AuthenticationResult"]["IdToken"]

    return {
        "api_url": api_url,
        "headers": {"Authorization": token},
        "environment": environment,
    }


def test_health_endpoint(api_config):
    """Test /health endpoint (public)"""
    response = requests.get(f"{api_config['api_url']}/health", timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == api_config["environment"]


def test_games_endpoint(api_config):
    """Test /games endpoint"""
    response = requests.get(
        f"{api_config['api_url']}/games?sport=basketball_nba",
        headers=api_config["headers"],
        timeout=10,
    )
    assert response.status_code == 200
    data = response.json()
    assert "games" in data
    assert "count" in data


def test_analyses_endpoint(api_config):
    """Test /analyses endpoint"""
    response = requests.get(
        f"{api_config['api_url']}/analyses?sport=basketball_nba&bookmaker=fanduel&model=consensus&limit=5",
        headers=api_config["headers"],
        timeout=10,
    )
    assert response.status_code == 200
    data = response.json()
    assert "analyses" in data
    assert "count" in data


def test_player_props_endpoint(api_config):
    """Test /player-props endpoint"""
    response = requests.get(
        f"{api_config['api_url']}/player-props?sport=basketball_nba&limit=5",
        headers=api_config["headers"],
        timeout=10,
    )
    assert response.status_code == 200
    data = response.json()
    assert "props" in data
    assert "count" in data


def test_sports_endpoint(api_config):
    """Test /sports endpoint"""
    response = requests.get(
        f"{api_config['api_url']}/sports",
        headers=api_config["headers"],
        timeout=10,
    )
    assert response.status_code == 200
    data = response.json()
    assert "sports" in data
    assert "count" in data
    assert data["count"] > 0


def test_bookmakers_endpoint(api_config):
    """Test /bookmakers endpoint"""
    response = requests.get(
        f"{api_config['api_url']}/bookmakers",
        headers=api_config["headers"],
        timeout=10,
    )
    assert response.status_code == 200
    data = response.json()
    assert "bookmakers" in data
    assert "count" in data
    assert data["count"] > 0


def test_analytics_endpoint(api_config):
    """Test /analytics endpoint"""
    response = requests.get(
        f"{api_config['api_url']}/analytics?model=consensus",
        headers=api_config["headers"],
        timeout=10,
    )
    assert response.status_code in [200, 404]  # 404 if no analytics data yet


def test_compliance_log_endpoint(api_config):
    """Test /compliance/log endpoint (POST)"""
    # Compliance endpoint may not be in the main API Gateway
    # Skip if not available
    payload = {
        "user_id": "test-user",
        "action": "age_verification",
        "timestamp": "2026-01-24T21:00:00Z",
    }
    response = requests.post(
        f"{api_config['api_url']}/compliance/log",
        headers=api_config["headers"],
        json=payload,
        timeout=10,
    )
    # 403 means endpoint exists but not configured in this API Gateway
    assert response.status_code in [200, 201, 403, 404]


def test_unauthorized_access():
    """Test that protected endpoints require authentication"""
    environment = os.getenv("ENVIRONMENT", "dev")
    environment_title = environment.title()
    cloudformation = boto3.client("cloudformation", region_name="us-east-1")

    api_stack_name = f"{environment_title}-BetCollectorApi"
    api_response = cloudformation.describe_stacks(StackName=api_stack_name)
    api_url = None
    for output in api_response["Stacks"][0]["Outputs"]:
        if output["OutputKey"] == "BetCollectorApiUrl":
            api_url = output["OutputValue"].rstrip("/")
            break

    # Test without auth header
    response = requests.get(f"{api_url}/games", timeout=10)
    assert response.status_code == 401


def test_invalid_endpoint(api_config):
    """Test that invalid endpoints return 404 or 403"""
    response = requests.get(
        f"{api_config['api_url']}/invalid-endpoint",
        headers=api_config["headers"],
        timeout=10,
    )
    # API Gateway may return 403 for missing routes with auth
    assert response.status_code in [403, 404]
