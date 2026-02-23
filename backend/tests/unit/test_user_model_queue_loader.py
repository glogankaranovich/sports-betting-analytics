"""Unit tests for user_model_queue_loader"""
import json
from unittest.mock import Mock, patch, MagicMock
import pytest
from user_model_queue_loader import handler, get_all_active_models, load_models_to_queue


@patch('user_model_queue_loader.user_models_table')
def test_get_all_active_models(mock_table):
    """Test getting all active models"""
    mock_table.scan.return_value = {
        'Items': [
            {'model_id': 'model1', 'status': 'active'},
            {'model_id': 'model2', 'status': 'active'}
        ]
    }
    
    models = get_all_active_models()
    
    assert len(models) == 2
    assert models[0]['model_id'] == 'model1'


@patch('user_model_queue_loader.user_models_table')
def test_get_all_active_models_pagination(mock_table):
    """Test pagination when getting models"""
    mock_table.scan.side_effect = [
        {
            'Items': [{'model_id': 'model1'}],
            'LastEvaluatedKey': {'pk': 'key1'}
        },
        {
            'Items': [{'model_id': 'model2'}]
        }
    ]
    
    models = get_all_active_models()
    
    assert len(models) == 2
    assert mock_table.scan.call_count == 2


@patch('user_model_queue_loader.sqs')
def test_load_models_to_queue(mock_sqs):
    """Test loading models to queue"""
    models = [
        {'model_id': 'model1', 'user_id': 'user1'},
        {'model_id': 'model2', 'user_id': 'user2'}
    ]
    
    load_models_to_queue(models)
    
    assert mock_sqs.send_message_batch.called


@patch('user_model_queue_loader.get_all_active_models')
@patch('user_model_queue_loader.load_models_to_queue')
def test_lambda_handler_success(mock_load, mock_get):
    """Test successful queue loading"""
    mock_get.return_value = [
        {'model_id': 'model1'},
        {'model_id': 'model2'}
    ]
    mock_load.return_value = 2
    
    result = handler({}, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['models_queued'] == 2


@patch('user_model_queue_loader.get_all_active_models')
@patch('user_model_queue_loader.load_models_to_queue')
def test_lambda_handler_no_models(mock_load, mock_get):
    """Test when no active models"""
    mock_get.return_value = []
    mock_load.return_value = 0
    
    result = handler({}, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['models_queued'] == 0


@patch('user_model_queue_loader.get_all_active_models')
def test_lambda_handler_error(mock_get):
    """Test error handling"""
    mock_get.side_effect = Exception("DynamoDB error")
    
    with pytest.raises(Exception, match="DynamoDB error"):
        handler({}, None)
