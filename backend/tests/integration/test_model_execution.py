"""
Integration tests for Hot/Cold, Matchup, and Injury-Aware models
Tests that models can execute with real DynamoDB data

Run read-only tests: pytest test_model_execution.py -m readonly
Run full tests with writes: pytest test_model_execution.py -m writes
Run all tests: pytest test_model_execution.py
"""

import os
from datetime import datetime

import boto3
import pytest

# Set env var for model dependencies
environment = os.getenv("ENVIRONMENT", "dev")
os.environ["DYNAMODB_TABLE"] = f"carpool-bets-v2-{environment}"

from ml.models import HotColdModel, InjuryAwareModel, MatchupModel


@pytest.fixture
def dynamodb_table():
    """Get real DynamoDB table for integration testing"""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    return dynamodb.Table(os.environ["DYNAMODB_TABLE"])


@pytest.fixture
def sample_game_info():
    """Sample game info for testing"""
    return {
        "sport": "basketball_nba",
        "home_team": "Atlanta Hawks",
        "away_team": "Boston Celtics",
        "commence_time": "2026-01-26T00:00:00Z",
    }


@pytest.fixture
def sample_odds_items():
    """Sample odds items for testing"""
    return [
        {
            "sk": "ODDS#spreads#fanduel#LATEST",
            "outcomes": [
                {"name": "Atlanta Hawks", "point": -3.5, "price": -110},
                {"name": "Boston Celtics", "point": 3.5, "price": -110},
            ],
        }
    ]


@pytest.fixture
def sample_prop_item():
    """Sample prop item for testing"""
    return {
        "event_id": "integration_test_game",
        "sport": "basketball_nba",
        "home_team": "Atlanta Hawks",
        "away_team": "Boston Celtics",
        "commence_time": "2026-01-26T00:00:00Z",
        "player_name": "Trae Young",
        "market_key": "player_points",
        "point": 25.5,
        "outcomes": [
            {"name": "Over", "price": -110},
            {"name": "Under", "price": -110},
        ],
    }


@pytest.fixture
def test_data_cleanup(dynamodb_table):
    """Fixture to clean up test data after tests"""
    test_keys = []

    yield test_keys

    # Cleanup after test
    for key in test_keys:
        try:
            dynamodb_table.delete_item(Key=key)
            print(f"Cleaned up test data: {key}")
        except Exception as e:
            print(f"Error cleaning up {key}: {e}")


# ============================================================================
# READ-ONLY TESTS (Safe to run anytime)
# ============================================================================


@pytest.mark.readonly
class TestHotColdModelReadOnly:
    """Read-only integration tests for Hot/Cold model"""

    def test_model_can_instantiate_and_query(self, dynamodb_table):
        """Test that Hot/Cold model can instantiate and query DynamoDB without crashing"""
        model = HotColdModel(dynamodb_table=dynamodb_table)

        # Test internal query methods (read-only)
        recent_record = model._get_recent_record(
            "Atlanta Hawks", "basketball_nba", lookback=5
        )

        assert isinstance(recent_record, dict)
        assert "wins" in recent_record
        assert "losses" in recent_record
        assert "games" in recent_record
        print(f"✓ Hot/Cold model can query team records: {recent_record}")

    def test_analyze_game_does_not_crash(
        self, dynamodb_table, sample_game_info, sample_odds_items
    ):
        """Test that Hot/Cold model can analyze a game without crashing"""
        model = HotColdModel(dynamodb_table=dynamodb_table)

        result = model.analyze_game_odds(
            "integration_test_game", sample_odds_items, sample_game_info
        )

        assert result is not None
        assert result.model == "hot_cold"
        assert result.sport == "basketball_nba"
        assert result.confidence > 0
        print(
            f"✓ Hot/Cold game analysis: {result.prediction} (confidence: {result.confidence})"
        )

    def test_analyze_prop_does_not_crash(self, dynamodb_table, sample_prop_item):
        """Test that Hot/Cold model can analyze a prop without crashing"""
        model = HotColdModel(dynamodb_table=dynamodb_table)

        result = model.analyze_prop_odds(sample_prop_item)

        assert result is not None
        assert result.model == "hot_cold"
        assert result.player_name == "Trae Young"
        print(
            f"✓ Hot/Cold prop analysis: {result.prediction} (confidence: {result.confidence})"
        )


@pytest.mark.readonly
class TestMatchupModelReadOnly:
    """Read-only integration tests for Matchup model"""

    def test_analyze_game_does_not_crash(
        self, dynamodb_table, sample_game_info, sample_odds_items
    ):
        """Test that Matchup model can analyze a game without crashing"""
        model = MatchupModel(dynamodb_table=dynamodb_table)

        result = model.analyze_game_odds(
            "integration_test_game", sample_odds_items, sample_game_info
        )

        assert result is not None
        assert result.model == "matchup"
        print(
            f"✓ Matchup game analysis: {result.prediction} (confidence: {result.confidence})"
        )

    def test_analyze_prop_returns_none(self, dynamodb_table, sample_prop_item):
        """Test that Matchup model returns None for props (not implemented)"""
        model = MatchupModel(dynamodb_table=dynamodb_table)

        result = model.analyze_prop_odds(sample_prop_item)

        assert result is None
        print("✓ Matchup model correctly returns None for props")


@pytest.mark.readonly
class TestInjuryAwareModelReadOnly:
    """Read-only integration tests for Injury-Aware model"""

    def test_analyze_game_does_not_crash(
        self, dynamodb_table, sample_game_info, sample_odds_items
    ):
        """Test that Injury-Aware model can analyze a game without crashing"""
        model = InjuryAwareModel(dynamodb_table=dynamodb_table)

        result = model.analyze_game_odds(
            "integration_test_game", sample_odds_items, sample_game_info
        )

        assert result is not None
        assert result.model == "injury_aware"
        assert (
            "injur" in result.reasoning.lower() or "healthy" in result.reasoning.lower()
        )
        print(
            f"✓ Injury-Aware game analysis: {result.prediction} (confidence: {result.confidence})"
        )

    def test_can_query_team_injuries(self, dynamodb_table):
        """Test that we can query team injuries from real DynamoDB"""
        model = InjuryAwareModel(dynamodb_table=dynamodb_table)

        injuries = model._get_team_injuries("Atlanta Hawks", "basketball_nba")

        assert isinstance(injuries, list)
        print(f"✓ Found {len(injuries)} injuries for Atlanta Hawks")


# ============================================================================
# WRITE TESTS (Creates and cleans up test data)
# ============================================================================


@pytest.mark.writes
class TestHotColdModelWithWrites:
    """Full integration tests for Hot/Cold model with test data"""

    def test_analyze_with_test_game_data(self, dynamodb_table, test_data_cleanup):
        """Test Hot/Cold model with actual test game data"""
        # Create test game outcome data
        test_pk = "OUTCOME#basketball_nba#Atlanta Hawks"
        test_sk = f"GAME#{datetime.utcnow().isoformat()}"

        dynamodb_table.put_item(
            Item={
                "pk": test_pk,
                "sk": test_sk,
                "sport": "basketball_nba",
                "team": "Atlanta Hawks",
                "opponent": "Boston Celtics",
                "result": "W",
                "score": 110,
                "opponent_score": 105,
            }
        )

        test_data_cleanup.append({"pk": test_pk, "sk": test_sk})

        # Now test the model
        model = HotColdModel(dynamodb_table=dynamodb_table)
        recent_record = model._get_recent_record(
            "Atlanta Hawks", "basketball_nba", lookback=5
        )

        assert recent_record["games"] >= 1
        print(f"✓ Hot/Cold model found test game data: {recent_record}")


@pytest.mark.writes
class TestInjuryAwareModelWithWrites:
    """Full integration tests for Injury-Aware model with test data"""

    def test_analyze_with_test_injury_data(self, dynamodb_table, test_data_cleanup):
        """Test Injury-Aware model with actual test injury data"""
        from decimal import Decimal

        # Create test injury data
        test_pk = "PLAYER_INJURY#basketball_nba#test_player"
        test_sk = "LATEST"

        dynamodb_table.put_item(
            Item={
                "pk": test_pk,
                "sk": test_sk,
                "sport": "basketball_nba",
                "player_name": "Test Player",
                "status": "Out",
                "injury_type": "Knee",
                "avg_minutes": Decimal("30.0"),
            }
        )

        test_data_cleanup.append({"pk": test_pk, "sk": test_sk})

        # Now test the model
        model = InjuryAwareModel(dynamodb_table=dynamodb_table)
        status = model._get_player_injury_status("Test Player", "basketball_nba")

        assert status is not None
        assert status["status"] == "Out"
        print(f"✓ Injury-Aware model found test injury data: {status}")


@pytest.mark.readonly
def test_all_models_can_instantiate(dynamodb_table):
    """Test that all models can be instantiated with real DynamoDB"""
    models = [
        ("HotColdModel", HotColdModel(dynamodb_table=dynamodb_table)),
        ("MatchupModel", MatchupModel(dynamodb_table=dynamodb_table)),
        ("InjuryAwareModel", InjuryAwareModel(dynamodb_table=dynamodb_table)),
    ]

    for name, model in models:
        assert model is not None
        assert model.table is not None
        print(f"✓ {name} instantiated successfully")
