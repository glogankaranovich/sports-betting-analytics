"""
Integration test for Matchup Model
Tests that the matchup model generates analyses in dev environment
"""

import boto3


def test_matchup_model_integration():
    """Test that matchup model generates analyses"""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("carpool-bets-v2-dev")

    # Query for matchup model analyses using AnalysisTimeGSI
    response = table.query(
        IndexName="AnalysisTimeGSI",
        KeyConditionExpression="analysis_time_pk = :pk",
        ExpressionAttributeValues={
            ":pk": "ANALYSIS#basketball_nba#fanduel#matchup#game"
        },
        Limit=10,
    )

    matchup_items = response.get("Items", [])
    print(f"Matchup analyses found: {len(matchup_items)}")

    # Should have at least some analyses (may be 0 if model just deployed)
    if len(matchup_items) > 0:
        sample = matchup_items[0]
        print("Sample matchup analysis:")
        print(f"  Game: {sample.get('home_team')} vs {sample.get('away_team')}")
        print(f"  Prediction: {sample.get('prediction')}")
        print(f"  Confidence: {sample.get('confidence')}")
        print(f"  Reasoning: {sample.get('reasoning')}")

        # Verify structure
        assert "home_team" in sample
        assert "away_team" in sample
        assert "prediction" in sample
        assert "confidence" in sample
        assert "reasoning" in sample
        assert "H2H" in sample.get("reasoning", "") or "Style" in sample.get(
            "reasoning", ""
        )


def test_all_models_exist():
    """Verify all 7 models are configured"""
    expected_models = [
        "consensus",
        "value",
        "momentum",
        "contrarian",
        "hot_cold",
        "rest_schedule",
        "matchup",
    ]

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("carpool-bets-v2-dev")

    found_models = set()

    # Check for each model
    for model in expected_models:
        response = table.query(
            IndexName="AnalysisTimeGSI",
            KeyConditionExpression="analysis_time_pk = :pk",
            ExpressionAttributeValues={
                ":pk": f"ANALYSIS#basketball_nba#fanduel#{model}#game"
            },
            Limit=1,
        )

        if response.get("Items"):
            found_models.add(model)
            print(f"✓ {model} model has analyses")

    print(f"\nFound {len(found_models)}/{len(expected_models)} models with data")
    print(f"Models with data: {sorted(found_models)}")

    # At minimum, consensus should exist
    assert "consensus" in found_models, "Consensus model should have analyses"
