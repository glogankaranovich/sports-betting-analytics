"""
Unit tests for custom_data module
"""
import json
import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from custom_data import (
    CustomDataset,
    convert_floats_to_decimal,
    validate_dataset,
)


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB table"""
    with patch("custom_data.custom_data_table") as mock_table:
        yield mock_table


@pytest.fixture
def mock_s3():
    """Mock S3 client"""
    with patch("custom_data.s3") as mock_s3_client:
        yield mock_s3_client


@pytest.fixture
def sample_dataset():
    """Sample dataset for testing"""
    return CustomDataset(
        user_id="user123",
        name="Test Dataset",
        description="Test description",
        sport="nba",
        data_type="team",
        columns=["team", "stat1", "stat2"],
        s3_key="datasets/test.json",
        row_count=100,
        dataset_id="dataset_abc123",
        created_at="2026-02-08T12:00:00",
    )


class TestConvertFloatsToDecimal:
    """Test float to Decimal conversion"""

    def test_convert_float(self):
        assert convert_floats_to_decimal(1.5) == Decimal("1.5")

    def test_convert_dict(self):
        result = convert_floats_to_decimal({"a": 1.5, "b": 2.0})
        assert result["a"] == Decimal("1.5")
        assert result["b"] == Decimal("2.0")

    def test_convert_list(self):
        result = convert_floats_to_decimal([1.5, 2.0, 3.5])
        assert result == [Decimal("1.5"), Decimal("2.0"), Decimal("3.5")]

    def test_convert_nested(self):
        result = convert_floats_to_decimal({"a": [1.5, {"b": 2.0}]})
        assert result["a"][0] == Decimal("1.5")
        assert result["a"][1]["b"] == Decimal("2.0")

    def test_non_float_unchanged(self):
        assert convert_floats_to_decimal("test") == "test"
        assert convert_floats_to_decimal(42) == 42


class TestCustomDataset:
    """Test CustomDataset class"""

    def test_init_with_defaults(self):
        dataset = CustomDataset(
            user_id="user123",
            name="Test",
            description="Desc",
            sport="nba",
            data_type="team",
            columns=["team", "stat"],
            s3_key="key",
            row_count=10,
        )
        assert dataset.user_id == "user123"
        assert dataset.name == "Test"
        assert dataset.dataset_id.startswith("dataset_")
        assert dataset.created_at is not None

    def test_init_with_all_params(self, sample_dataset):
        assert sample_dataset.dataset_id == "dataset_abc123"
        assert sample_dataset.user_id == "user123"
        assert sample_dataset.created_at == "2026-02-08T12:00:00"

    def test_to_dynamodb(self, sample_dataset):
        item = sample_dataset.to_dynamodb()
        assert item["PK"] == "USER#user123"
        assert item["SK"] == "DATASET#dataset_abc123"
        assert item["GSI1PK"] == "SPORT#nba"
        assert item["GSI1SK"] == "CREATED#2026-02-08T12:00:00"
        assert item["dataset_id"] == "dataset_abc123"
        assert item["name"] == "Test Dataset"
        assert item["sport"] == "nba"
        assert item["data_type"] == "team"
        assert item["columns"] == ["team", "stat1", "stat2"]
        assert item["row_count"] == 100

    def test_from_dynamodb(self):
        item = {
            "dataset_id": "dataset_xyz",
            "user_id": "user456",
            "name": "My Dataset",
            "description": "Description",
            "sport": "nfl",
            "data_type": "player",
            "columns": ["player", "yards"],
            "s3_key": "datasets/xyz.json",
            "row_count": 50,
            "created_at": "2026-02-01T10:00:00",
        }
        dataset = CustomDataset.from_dynamodb(item)
        assert dataset.dataset_id == "dataset_xyz"
        assert dataset.user_id == "user456"
        assert dataset.name == "My Dataset"
        assert dataset.sport == "nfl"
        assert dataset.data_type == "player"

    def test_save(self, sample_dataset, mock_dynamodb):
        sample_dataset.save()
        mock_dynamodb.put_item.assert_called_once()
        call_args = mock_dynamodb.put_item.call_args
        assert call_args[1]["Item"]["PK"] == "USER#user123"
        assert call_args[1]["Item"]["SK"] == "DATASET#dataset_abc123"

    def test_get_found(self, mock_dynamodb):
        mock_dynamodb.get_item.return_value = {
            "Item": {
                "dataset_id": "dataset_123",
                "user_id": "user123",
                "name": "Test",
                "description": "Desc",
                "sport": "nba",
                "data_type": "team",
                "columns": ["team"],
                "s3_key": "key",
                "row_count": 10,
                "allow_benny_access": True,
                "created_at": "2026-02-08T12:00:00",
            }
        }
        dataset = CustomDataset.get("user123", "dataset_123")
        assert dataset is not None
        assert dataset.dataset_id == "dataset_123"
        assert dataset.name == "Test"

    def test_get_not_found(self, mock_dynamodb):
        mock_dynamodb.get_item.return_value = {}
        dataset = CustomDataset.get("user123", "nonexistent")
        assert dataset is None

    def test_list_by_user(self, mock_dynamodb):
        mock_dynamodb.query.return_value = {
            "Items": [
                {
                    "dataset_id": "dataset_1",
                    "user_id": "user123",
                    "name": "Dataset 1",
                    "description": "Desc",
                    "sport": "nba",
                    "data_type": "team",
                    "columns": ["team"],
                    "s3_key": "key1",
                    "row_count": 10,
                    "created_at": "2026-02-08T12:00:00",
                },
                {
                    "dataset_id": "dataset_2",
                    "user_id": "user123",
                    "name": "Dataset 2",
                    "description": "Desc",
                    "sport": "nfl",
                    "data_type": "player",
                    "columns": ["player"],
                    "s3_key": "key2",
                    "row_count": 20,
                    "created_at": "2026-02-07T12:00:00",
                },
            ]
        }
        datasets = CustomDataset.list_by_user("user123")
        assert len(datasets) == 2
        assert datasets[0].dataset_id == "dataset_1"
        assert datasets[1].dataset_id == "dataset_2"

    def test_delete(self, sample_dataset, mock_dynamodb, mock_s3):
        sample_dataset.delete()
        mock_dynamodb.delete_item.assert_called_once_with(
            Key={"PK": "USER#user123", "SK": "DATASET#dataset_abc123"}
        )
        mock_s3.delete_object.assert_called_once_with(
            Bucket=os.environ.get("CUSTOM_DATA_BUCKET", "dev-custom-data-bucket"),
            Key="datasets/test.json",
        )

    def test_delete_s3_error(self, sample_dataset, mock_dynamodb, mock_s3):
        mock_s3.delete_object.side_effect = Exception("S3 error")
        # Should not raise exception
        sample_dataset.delete()
        mock_dynamodb.delete_item.assert_called_once()

    def test_get_data(self, sample_dataset, mock_s3):
        mock_response = {
            "Body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps([{"team": "Lakers", "stat": 100}]).encode()
                )
            )
        }
        mock_s3.get_object.return_value = mock_response
        data = sample_dataset.get_data()
        assert len(data) == 1
        assert data[0]["team"] == "Lakers"

    def test_get_data_error(self, sample_dataset, mock_s3):
        mock_s3.get_object.side_effect = Exception("S3 error")
        data = sample_dataset.get_data()
        assert data == []


class TestValidateDataset:
    """Test dataset validation"""

    def test_empty_dataset(self):
        valid, error = validate_dataset([], "team")
        assert not valid
        assert error == "Dataset is empty"

    def test_too_large(self):
        data = [{"team": f"Team{i}"} for i in range(10001)]
        valid, error = validate_dataset(data, "team")
        assert not valid
        assert error == "Dataset too large (max 10,000 rows)"

    def test_inconsistent_columns(self):
        data = [{"team": "Lakers", "stat": 100}, {"team": "Celtics"}]
        valid, error = validate_dataset(data, "team")
        assert not valid
        assert error == "Inconsistent columns across rows"

    def test_team_missing_team_column(self):
        data = [{"name": "Lakers", "stat": 100}]
        valid, error = validate_dataset(data, "team")
        assert not valid
        assert error == "Team datasets must have 'team' column"

    def test_player_missing_player_column(self):
        data = [{"name": "LeBron", "stat": 100}]
        valid, error = validate_dataset(data, "player")
        assert not valid
        assert error == "Player datasets must have 'player' column"

    def test_valid_team_dataset(self):
        data = [
            {"team": "Lakers", "stat1": 100, "stat2": 200},
            {"team": "Celtics", "stat1": 110, "stat2": 210},
        ]
        valid, error = validate_dataset(data, "team")
        assert valid
        assert error is None

    def test_valid_player_dataset(self):
        data = [
            {"player": "LeBron", "points": 25.5},
            {"player": "Curry", "points": 28.3},
        ]
        valid, error = validate_dataset(data, "player")
        assert valid
        assert error is None
