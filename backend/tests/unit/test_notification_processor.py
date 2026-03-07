"""
Unit tests for notification_processor
"""
import json
import pytest
from unittest.mock import Mock, patch
from notification_processor import lambda_handler


@patch('notification_processor.NotificationService')
@patch.dict('os.environ', {'BENNY_NOTIFICATION_EMAIL': 'test@example.com'})
def test_lambda_handler_success(mock_service_class):
    """Test successful notification processing"""
    mock_service = Mock()
    mock_service.format_bet_notification.return_value = "Bet placed: Team A"
    mock_service.send_notification.return_value = True
    mock_service_class.return_value = mock_service
    
    event = {
        "Records": [{
            "body": json.dumps({
                "type": "bet_placed",
                "data": {"game": "Team A vs Team B", "amount": 10}
            })
        }]
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["successful"] == 1
    assert body["failed"] == 0


@patch('notification_processor.NotificationService')
@patch.dict('os.environ', {'BENNY_NOTIFICATION_EMAIL': 'test@example.com'})
def test_lambda_handler_send_failure(mock_service_class):
    """Test handling of send failure"""
    mock_service = Mock()
    mock_service.format_bet_notification.return_value = "Bet placed"
    mock_service.send_notification.return_value = False
    mock_service_class.return_value = mock_service
    
    event = {
        "Records": [{
            "body": json.dumps({
                "type": "bet_placed",
                "data": {"game": "Team A vs Team B"}
            })
        }]
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["successful"] == 0
    assert body["failed"] == 1


@patch('notification_processor.NotificationService')
@patch.dict('os.environ', {})
def test_lambda_handler_no_email_configured(mock_service_class):
    """Test skipping when email not configured"""
    event = {
        "Records": [{
            "body": json.dumps({
                "type": "bet_placed",
                "data": {"game": "Team A vs Team B"}
            })
        }]
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["successful"] == 0
    assert body["failed"] == 0


@patch('notification_processor.NotificationService')
@patch.dict('os.environ', {'BENNY_NOTIFICATION_EMAIL': 'test@example.com'})
def test_lambda_handler_unknown_type(mock_service_class):
    """Test handling of unknown notification type"""
    event = {
        "Records": [{
            "body": json.dumps({
                "type": "unknown_type",
                "data": {}
            })
        }]
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["successful"] == 0
