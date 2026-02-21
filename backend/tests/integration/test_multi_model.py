"""
Integration test for multi-model analysis generation
"""
import json
import os
import time

import boto3


def test_multi_model_analysis():
    """Test that all three models generate analyses correctly"""
    environment = os.getenv("ENVIRONMENT", "dev")
    lambda_client = boto3.client("lambda", region_name="us-east-1")

    models = ["consensus", "value", "momentum"]
    # Try multiple sports to find one with active games
    sports_to_try = [
        ("basketball_nba", "nba"),
        ("icehockey_nhl", "nhl"),
        ("americanfootball_nfl", "nfl"),
    ]

    sport_used = None
    sport_key = None

    # Find a sport with active games
    for sport, key in sports_to_try:
        lambda_function_name = f"analysis-generator-{key}-{environment}"
        test_payload = {
            "sport": sport,
            "model": "consensus",
            "bet_type": "games",
            "limit": 1,
        }

        response = lambda_client.invoke(
            FunctionName=lambda_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(test_payload),
        )

        result = json.loads(response["Payload"].read())
        body = json.loads(result["body"])

        if body.get("analyses_count", 0) > 0:
            sport_used = sport
            sport_key = key
            print(f"Using {sport} for multi-model testing (has active games)")
            break

    assert (
        sport_used is not None
    ), f"No active games found in any sport (tried: {[s[0] for s in sports_to_try]})"

    lambda_function_name = f"analysis-generator-{sport_key}-{environment}"
    results = {}

    print(f"\n{'='*60}")
    print(f"Testing Multi-Model Analysis Generation ({sport_used})")
    print(f"{'='*60}\n")

    for model in models:
        print(f"Testing {model} model...")

        # Test game analysis
        payload = {
            "sport": sport_used,
            "model": model,
            "bet_type": "games",
            "limit": 5,
        }

        response = lambda_client.invoke(
            FunctionName=lambda_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        result = json.loads(response["Payload"].read())
        
        # Check if Lambda errored
        if "errorMessage" in result:
            pytest.fail(f"{model} Lambda error: {result.get('errorMessage')}")
        
        assert "body" in result, f"{model} Lambda response missing 'body': {result}"
        body = json.loads(result["body"])

        print(
            f"  ✓ {model} game analysis: {body.get('analyses_count', 0)} analyses generated"
        )

        assert result["statusCode"] == 200, f"{model} game analysis failed"
        assert body.get("analyses_count", 0) > 0, f"{model} generated no game analyses"

        results[f"{model}_games"] = body.get("analyses_count", 0)

        # Small delay between invocations
        time.sleep(1)

        # Test prop analysis (same Lambda handles both games and props)
        # Props might not be available for all sports, so make this optional
        payload["bet_type"] = "props"

        response = lambda_client.invoke(
            FunctionName=lambda_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        result = json.loads(response["Payload"].read())
        body = json.loads(result["body"])

        prop_count = body.get("analyses_count", 0)
        print(f"  ✓ {model} prop analysis: {prop_count} analyses generated")

        assert result["statusCode"] == 200, f"{model} prop analysis failed"
        # Props are optional - just log if none available
        if prop_count == 0:
            print(f"    (No props available for {sport_used})")

        results[f"{model}_props"] = prop_count

        time.sleep(1)

    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")
    for key, count in results.items():
        print(f"  {key}: {count} analyses")

    print(f"\n{'='*60}")
    print("✅ All models generated analyses successfully!")
    print(f"{'='*60}\n")


def test_model_data_differences():
    """Verify that different models produce different analyses"""
    environment = os.getenv("ENVIRONMENT", "dev")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(f"carpool-bets-v2-{environment}")

    print(f"\n{'='*60}")
    print("Testing Model Data Differences")
    print(f"{'='*60}\n")

    # Query analyses for the same game from different models using AnalysisTimeGSI
    response = table.query(
        IndexName="AnalysisTimeGSI",
        KeyConditionExpression="analysis_time_pk = :pk",
        ExpressionAttributeValues={
            ":pk": "ANALYSIS#basketball_nba#fanduel#consensus#game"
        },
        Limit=1,
    )

    consensus_items = response.get("Items", [])

    response = table.query(
        IndexName="AnalysisTimeGSI",
        KeyConditionExpression="analysis_time_pk = :pk",
        ExpressionAttributeValues={":pk": "ANALYSIS#basketball_nba#fanduel#value#game"},
        Limit=1,
    )

    value_items = response.get("Items", [])

    response = table.query(
        IndexName="AnalysisTimeGSI",
        KeyConditionExpression="analysis_time_pk = :pk",
        ExpressionAttributeValues={
            ":pk": "ANALYSIS#basketball_nba#fanduel#momentum#game"
        },
        Limit=1,
    )

    momentum_items = response.get("Items", [])

    print(f"Consensus analyses found: {len(consensus_items)}")
    print(f"Value analyses found: {len(value_items)}")
    print(f"Momentum analyses found: {len(momentum_items)}")

    assert len(consensus_items) > 0, "No consensus analyses found"
    assert len(value_items) > 0, "No value analyses found"
    assert len(momentum_items) > 0, "No momentum analyses found"

    # Compare reasoning to ensure they're different
    if consensus_items and value_items and momentum_items:
        consensus_reasoning = consensus_items[0].get("reasoning", "")
        value_reasoning = value_items[0].get("reasoning", "")
        momentum_reasoning = momentum_items[0].get("reasoning", "")

        print(f"\nConsensus: {consensus_reasoning}")
        print(f"Value: {value_reasoning}")
        print(f"Momentum: {momentum_reasoning}")

        # Verify they have different reasoning
        assert (
            consensus_reasoning != value_reasoning
        ), "Consensus and Value have identical reasoning"
        assert (
            consensus_reasoning != momentum_reasoning
        ), "Consensus and Momentum have identical reasoning"

        print("\n✅ Models produce different analyses")

    print("\n" + "=" * 60)
    print("✅ Model data differences verified!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_multi_model_analysis()
    test_model_data_differences()
