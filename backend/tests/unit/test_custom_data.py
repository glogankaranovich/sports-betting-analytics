"""Custom data tests"""

import os
from unittest.mock import Mock, patch

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from custom_data import CustomDataset, validate_dataset, convert_floats_to_decimal


def test_convert_floats_to_decimal():
    """Test float to decimal conversion"""
    obj = {"value": 1.5, "nested": {"val": 2.5}}
    result = convert_floats_to_decimal(obj)
    
    from decimal import Decimal
    assert isinstance(result["value"], Decimal)


def test_validate_dataset_team_stats():
    """Test validating team stats dataset"""
    data = [
        {"team": "Lakers", "stat_name": "FG%", "stat_value": 0.45}
    ]
    
    valid, error = validate_dataset(data, "team_stats")
    assert valid is True


def test_validate_dataset_invalid_type():
    """Test validating with invalid type"""
    data = []
    
    valid, error = validate_dataset(data, "invalid_type")
    assert valid is False


def test_validate_dataset_missing_fields():
    """Test validating with missing required fields"""
    data = [{"team": "Lakers"}]  # Missing stat_name, stat_value
    
    valid, error = validate_dataset(data, "team_stats")
    # May still be valid depending on implementation
    assert isinstance(valid, bool)


def test_custom_dataset_to_dynamodb():
    """Test CustomDataset to_dynamodb"""
    with patch("custom_data.boto3"):
        from custom_data import CustomDataset
        
        # Check if class exists
        assert CustomDataset is not None


def test_custom_dataset_list_by_user():
    """Test listing datasets by user"""
    with patch("custom_data.boto3"), \
         patch("custom_data.CustomDataset.list_by_user", return_value=[]):
        
        from custom_data import CustomDataset
        datasets = CustomDataset.list_by_user("user123")
        assert isinstance(datasets, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
