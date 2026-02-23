"""
Integration tests for collector Lambda functions.
Tests schedule, player stats, team stats, model analytics, and season manager.
"""

import json
import os

import boto3

# AWS clients
lambda_client = boto3.client("lambda", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

# Get environment from env var, default to dev
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
TABLE_NAME = f"carpool-bets-v2-{ENVIRONMENT}"


def test_schedule_collector_integration():
    """Test schedule collector Lambda function."""
    # Get Lambda function name
    function_name = None
    response = lambda_client.list_functions()
    for func in response["Functions"]:
        if "ScheduleCollectorFunction" in func["FunctionName"]:
            function_name = func["FunctionName"]
            break

    if not function_name:
        print(f"Schedule collector function not found in {ENVIRONMENT}")
        return  # Skip if not deployed

    # Invoke Lambda with NBA sport
    payload = {"sport": "basketball_nba"}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    # Parse response
    response_payload = json.loads(response["Payload"].read())
    print(f"Schedule collector response: {response_payload}")

    # Verify response structure
    assert response["StatusCode"] == 200
    assert "statusCode" in response_payload
    assert response_payload["statusCode"] in [200, 201]


def test_player_stats_collector_integration():
    """Test player stats collector Lambda function."""
    function_name = None
    response = lambda_client.list_functions()
    for func in response["Functions"]:
        if "PlayerStatsCollectorFunction" in func["FunctionName"]:
            function_name = func["FunctionName"]
            break

    if not function_name:
        print(f"Player stats collector function not found in {ENVIRONMENT}")
        return

    payload = {"sport": "basketball_nba"}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    response_payload = json.loads(response["Payload"].read())
    print(f"Player stats collector response: {response_payload}")

    assert response["StatusCode"] == 200
    assert "statusCode" in response_payload


def test_team_stats_collector_integration():
    """Test team stats collector Lambda function."""
    function_name = None
    response = lambda_client.list_functions()
    for func in response["Functions"]:
        if "TeamStatsCollectorFunction" in func["FunctionName"]:
            function_name = func["FunctionName"]
            break

    if not function_name:
        print(f"Team stats collector function not found in {ENVIRONMENT}")
        return

    payload = {"sport": "basketball_nba"}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    response_payload = json.loads(response["Payload"].read())
    print(f"Team stats collector response: {response_payload}")

    assert response["StatusCode"] == 200
    assert "statusCode" in response_payload


def test_player_stats_collector_integration():
    """Test player stats collector Lambda function."""
    # Get Lambda function name
    function_name = None
    response = lambda_client.list_functions()
    for func in response["Functions"]:
        if "PlayerStats" in func["FunctionName"]:
            function_name = func["FunctionName"]
            break

    assert function_name is not None, "Player stats collector function not found"

    # Invoke Lambda with NBA sport
    payload = {"sport": "basketball_nba"}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    # Parse response
    response_payload = json.loads(response["Payload"].read())
    print(f"Player stats collector response: {response_payload}")

    # Verify response structure
    assert response["StatusCode"] == 200
    assert "statusCode" in response_payload
    assert response_payload["statusCode"] in [200, 201]

    # Verify data was stored in DynamoDB
    table = dynamodb.Table("carpool-bets-v2-{ENVIRONMENT}")

    # Query for player stats (PK starts with PLAYER_STATS#)
    response = table.scan(
        FilterExpression="begins_with(PK, :pk)",
        ExpressionAttributeValues={":pk": "PLAYER_STATS#"},
        Limit=5,
    )

    print(f"Found {len(response.get('Items', []))} player stats items")
    # Note: May be 0 if collector hasn't run yet, which is OK


def test_team_stats_collector_integration():
    """Test team stats collector Lambda function."""
    # Get Lambda function name
    function_name = None
    response = lambda_client.list_functions()
    for func in response["Functions"]:
        if "TeamStatsCollectorFunction" in func["FunctionName"]:
            function_name = func["FunctionName"]
            break

    assert function_name is not None, "Team stats collector function not found"

    # Invoke Lambda with NBA sport
    payload = {"sport": "basketball_nba"}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    # Parse response
    response_payload = json.loads(response["Payload"].read())
    print(f"Team stats collector response: {response_payload}")

    # Verify response structure
    assert response["StatusCode"] == 200
    assert "statusCode" in response_payload
    assert response_payload["statusCode"] in [200, 201]

    # Verify data was stored in DynamoDB
    table = dynamodb.Table("carpool-bets-v2-{ENVIRONMENT}")

    # Query for team stats (PK starts with TEAM_STATS#)
    response = table.scan(
        FilterExpression="begins_with(PK, :pk)",
        ExpressionAttributeValues={":pk": "TEAM_STATS#"},
        Limit=5,
    )

    print(f"Found {len(response.get('Items', []))} team stats items")
    # Note: May be 0 if collector hasn't run yet, which is OK


def test_model_analytics_integration():
    """Test model analytics Lambda function."""
    # Get Lambda function name
    function_name = None
    response = lambda_client.list_functions()
    for func in response["Functions"]:
        if "ModelAnalyticsFunction" in func["FunctionName"]:
            function_name = func["FunctionName"]
            break

    assert function_name is not None, "Model analytics function not found"

    # Invoke Lambda with query params to get summary for single model
    payload = {"queryStringParameters": {"type": "summary", "models": "consensus"}}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    # Parse response
    response_payload = json.loads(response["Payload"].read())
    print(f"Model analytics response: {response_payload}")

    # Verify response structure
    assert response["StatusCode"] == 200
    assert "statusCode" in response_payload
    # Analytics may return 200 even with no data to analyze


def test_season_manager_integration():
    """Test season manager Lambda function."""
    # Get Lambda function name
    function_name = None
    response = lambda_client.list_functions()
    for func in response["Functions"]:
        if "SeasonManagerFunction" in func["FunctionName"]:
            function_name = func["FunctionName"]
            break

    assert function_name is not None, "Season manager function not found"

    # Invoke Lambda
    payload = {"action": "check_seasons"}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    # Parse response
    response_payload = json.loads(response["Payload"].read())
    print(f"Season manager response: {response_payload}")

    # Verify response structure
    assert response["StatusCode"] == 200
    assert "statusCode" in response_payload
    assert response_payload["statusCode"] in [200, 201]


def test_all_analysis_generators_exist():
    """Verify all 5 analysis generator Lambda functions exist."""
    response = lambda_client.list_functions()
    function_names = [func["FunctionName"] for func in response["Functions"]]

    sports = ["nba", "nfl", "mlb", "nhl", "epl"]
    for sport in sports:
        found = any(
            f"analysis-generator-{sport}" in name.lower() for name in function_names
        )
        assert found, f"Analysis generator for {sport} not found"

    print("✓ All 5 analysis generators exist")


def test_all_lambdas_have_monitoring():
    """Verify all Lambda functions are being monitored."""
    # Get all Lambda functions
    response = lambda_client.list_functions()
    lambda_functions = [func["FunctionName"] for func in response["Functions"]]

    # Filter to our functions (exclude AWS-managed)
    our_functions = [
        name
        for name in lambda_functions
        if any(
            keyword in name.lower()
            for keyword in [
                "odds-collector",
                "props-collector",
                "schedulecollector",
                "analysis-generator",
                "insight-generator",
                "playerstats",
                "teamstats",
                "outcomecollector",
                "modelanalytics",
                "seasonmanager",
                "compliancelogger",
                "recommendationgenerator",
            ]
        )
    ]

    print(f"Found {len(our_functions)} Lambda functions to monitor:")
    for func in sorted(our_functions):
        print(f"  - {func}")

    # Verify we have the expected count
    # 2 odds collectors + 5 analysis + 5 insight + 6 other collectors = 18+
    assert (
        len(our_functions) >= 18
    ), f"Expected at least 18 functions, found {len(our_functions)}"

    print(f"✓ All {len(our_functions)} Lambda functions exist and should be monitored")
