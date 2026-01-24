"""
Integration test for multi-model analysis generation
"""
import boto3
import json
import time
import os


def test_multi_model_analysis():
    """Test that all three models generate analyses correctly"""
    environment = os.getenv("ENVIRONMENT", "dev")
    lambda_function_name = f"analysis-generator-1-{environment}"
    lambda_client = boto3.client("lambda", region_name="us-east-1")

    models = ["consensus", "value", "momentum"]
    results = {}

    print(f"\n{'='*60}")
    print("Testing Multi-Model Analysis Generation")
    print(f"{'='*60}\n")

    for model in models:
        print(f"Testing {model} model...")

        # Test game analysis
        payload = {
            "sport": "basketball_nba",
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
        body = json.loads(result["body"])

        print(
            f"  ✓ {model} game analysis: {body.get('analyses_count', 0)} analyses generated"
        )

        assert result["statusCode"] == 200, f"{model} game analysis failed"
        assert body.get("analyses_count", 0) > 0, f"{model} generated no game analyses"

        results[f"{model}_games"] = body.get("analyses_count", 0)

        # Small delay between invocations
        time.sleep(1)

        # Test prop analysis (Lambda 2 handles props after split)
        payload["bet_type"] = "props"
        lambda_function_name_props = f"analysis-generator-2-{environment}"

        response = lambda_client.invoke(
            FunctionName=lambda_function_name_props,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        result = json.loads(response["Payload"].read())
        body = json.loads(result["body"])

        print(
            f"  ✓ {model} prop analysis: {body.get('analyses_count', 0)} analyses generated"
        )

        assert result["statusCode"] == 200, f"{model} prop analysis failed"
        assert body.get("analyses_count", 0) > 0, f"{model} generated no prop analyses"

        results[f"{model}_props"] = body.get("analyses_count", 0)

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
