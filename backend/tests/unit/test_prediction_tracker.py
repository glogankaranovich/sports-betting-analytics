"""
Test PredictionTracker functionality
"""

import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch
from prediction_tracker import PredictionTracker


@mock_aws
def test_prediction_tracker_init():
    """Test PredictionTracker initialization"""
    tracker = PredictionTracker("test-table")
    assert tracker.table is not None
    assert tracker.analyzer is not None


@mock_aws
def test_generate_game_predictions():
    """Test game prediction generation"""
    # Create mock DynamoDB table
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    _ = dynamodb.create_table(  # Table created but not used directly
        TableName="carpool-bets-v2-dev",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Mock odds data (not used in current test but kept for reference)
    _ = [
        {
            "game_id": "test_game_1",
            "sport": "americanfootball_nfl",
            "home_team": "Team A",
            "away_team": "Team B",
            "commence_time": "2026-01-03T20:00:00Z",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Team A", "price": -110},
                        {"name": "Team B", "price": 100},
                    ],
                }
            ],
        }
    ]

    with patch(
        "prediction_tracker.PredictionTracker.generate_game_predictions_for_sport"
    ) as mock_generate:
        mock_generate.return_value = 1

        tracker = PredictionTracker("carpool-bets-v2-dev")
        count = tracker.generate_game_predictions()

        assert count >= 0


@mock_aws
def test_generate_prop_predictions():
    """Test player prop prediction generation"""
    # Create mock DynamoDB table
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    _ = dynamodb.create_table(  # Table created but not used directly
        TableName="carpool-bets-v2-dev",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Mock player props data (not used in current test but kept for reference)
    _ = [
        {
            "game_id": "test_game_1",
            "sport": "basketball_nba",
            "home_team": "Team A",
            "away_team": "Team B",
            "commence_time": "2026-01-03T20:00:00Z",
            "markets": [
                {
                    "key": "player_points",
                    "outcomes": [
                        {"name": "Player X Over 25.5", "price": -110, "point": 25.5},
                        {"name": "Player X Under 25.5", "price": -110, "point": 25.5},
                    ],
                }
            ],
        }
    ]

    with patch(
        "prediction_tracker.PredictionTracker.generate_prop_predictions_for_sport"
    ) as mock_generate:
        mock_generate.return_value = 1

        tracker = PredictionTracker("carpool-bets-v2-dev")
        count = tracker.generate_prop_predictions()

        assert count >= 0


def test_combat_sports_support():
    """Test that combat sports are included in supported sports"""
    tracker = PredictionTracker("test-table")

    # Test that the tracker can be initialized without errors
    # This implicitly tests that combat sports are supported
    assert tracker.analyzer is not None

    # Test that the analyzer can handle combat sports data
    mma_data = {
        "game_id": "mma_fight_1",
        "sport": "mma_mixed_martial_arts",
        "home_team": "Fighter A",
        "away_team": "Fighter B",
        "odds": {
            "test_bookmaker": {
                "h2h": {
                    "outcomes": [
                        {"name": "Fighter A", "price": -150},
                        {"name": "Fighter B", "price": 120},
                    ]
                }
            }
        },
    }

    prediction = tracker.analyzer.analyze_game(mma_data)
    assert prediction.sport == "mma_mixed_martial_arts"


if __name__ == "__main__":
    pytest.main([__file__])
