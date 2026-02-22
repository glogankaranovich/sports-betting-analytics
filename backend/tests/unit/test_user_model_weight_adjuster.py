"""User model weight adjuster tests"""

from unittest.mock import Mock, patch

import pytest

from user_model_weight_adjuster import get_data_source_accuracy


@patch("user_model_weight_adjuster.boto3")
def test_get_data_source_accuracy_insufficient_data(mock_boto):
    """Test insufficient data"""
    mock_table = Mock()
    mock_table.query.return_value = {"Items": []}
    mock_boto.resource.return_value.Table.return_value = mock_table
    
    result = get_data_source_accuracy("user1", "model1", "espn", 30)
    assert result is None


@patch("user_model_weight_adjuster.boto3")
def test_get_data_source_accuracy_no_source_predictions(mock_boto):
    """Test no predictions with source"""
    mock_table = Mock()
    mock_table.query.return_value = {
        "Items": [{"reasoning": "other source"} for _ in range(15)]
    }
    mock_boto.resource.return_value.Table.return_value = mock_table
    
    result = get_data_source_accuracy("user1", "model1", "espn", 30)
    assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
