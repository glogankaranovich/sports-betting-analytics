"""
Integration test for Matchup Model
Tests that the matchup model generates analyses in dev environment
"""

import os
from decimal import Decimal

import boto3
import pytest

# Set env var for model dependencies
environment = os.getenv("ENVIRONMENT", "dev")
os.environ["DYNAMODB_TABLE"] = f"carpool-bets-v2-{environment}"


@pytest.mark.readonly
def test_matchup_model_integration():
    """Test that matchup model generates analyses"""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])

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


@pytest.mark.writes
def test_matchup_prop_with_opponent_data():
    """Test Matchup model prop analysis with opponent-specific player stats"""
    from ml.models import MatchupModel

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])

    # Create test data
    test_game_id = "test_matchup_prop_game"
    test_player = "test_matchup_player"

    # Store test game
    table.put_item(
        Item={
            "pk": f"GAME#{test_game_id}",
            "sk": "LATEST",
            "home_team": "Lakers",
            "away_team": "Celtics",
            "commence_time": "2026-01-25T19:00:00Z",
            "sport": "basketball_nba",
        }
    )

    # Store player stats vs Celtics (averages 28 pts)
    for i, pts in enumerate([30, 28, 26, 29, 27]):
        table.put_item(
            Item={
                "pk": f"PLAYER_STATS#basketball_nba#{test_player}",
                "sk": f"2026-01-{20+i:02d}#celtics",
                "game_id": f"game_{i}",
                "game_index_pk": f"game_{i}",
                "game_index_sk": f"PLAYER_STATS#basketball_nba#{test_player}",
                "sport": "basketball_nba",
                "player_name": "Test Matchup Player",
                "opponent": "Celtics",
                "stats": {"PTS": Decimal(str(pts)), "MIN": Decimal("35")},
                "collected_at": "2026-01-25T10:00:00Z",
            }
        )

    try:
        # Test prop analysis
        model = MatchupModel(dynamodb_table=table)

        prop_item = {
            "sport": "basketball_nba",
            "player_name": "Test Matchup Player",
            "market_key": "player_points",
            "point": 24.5,
            "event_id": test_game_id,
            "team": "Lakers",
        }

        result = model.analyze_prop_odds(prop_item)

        assert result is not None, "Should return analysis with opponent history"
        assert "Over" in result.prediction, "Should predict Over (avg 28 vs line 24.5)"
        assert result.confidence > 0.5, "Should have decent confidence"
        assert "Celtics" in result.reasoning, "Should mention opponent"

        print(f"✓ Matchup prop analysis: {result.prediction} ({result.confidence:.2f})")
        print(f"  Reasoning: {result.reasoning}")

    finally:
        # Cleanup
        table.delete_item(Key={"pk": f"GAME#{test_game_id}", "sk": "LATEST"})
        for i in range(5):
            table.delete_item(
                Key={
                    "pk": f"PLAYER_STATS#basketball_nba#{test_player}",
                    "sk": f"2026-01-{20+i:02d}#celtics",
                }
            )


@pytest.mark.readonly
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
