"""
Unit tests for email_forwarder
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from email_forwarder import lambda_handler


@patch('email_forwarder.s3')
@patch('email_forwarder.ses')
def test_lambda_handler_success(mock_ses, mock_s3):
    """Test successful email forwarding"""
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: b"Raw email content")
    }
    
    event = {
        "Records": [{
            "ses": {
                "mail": {"messageId": "msg123"},
                "receipt": {"recipients": ["support@carpoolbets.com"]}
            }
        }]
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    mock_s3.get_object.assert_called_once()
    mock_ses.send_raw_email.assert_called_once()


@patch('email_forwarder.s3')
@patch('email_forwarder.ses')
@patch('email_forwarder.boto3')
def test_lambda_handler_ses_error(mock_boto3, mock_ses, mock_s3):
    """Test handling of SES error"""
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: b"Raw email content")
    }
    mock_ses.send_raw_email.side_effect = ClientError(
        {"Error": {"Code": "MessageRejected", "Message": "Email rejected"}},
        "send_raw_email"
    )
    mock_cloudwatch = Mock()
    mock_boto3.client.return_value = mock_cloudwatch
    
    event = {
        "Records": [{
            "ses": {
                "mail": {"messageId": "msg123"},
                "receipt": {"recipients": ["support@carpoolbets.com"]}
            }
        }]
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 500
    mock_cloudwatch.put_metric_data.assert_called_once()


@patch('email_forwarder.s3')
@patch('email_forwarder.ses')
def test_lambda_handler_s3_error(mock_ses, mock_s3):
    """Test handling of S3 error"""
    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
        "get_object"
    )
    
    event = {
        "Records": [{
            "ses": {
                "mail": {"messageId": "msg123"},
                "receipt": {"recipients": ["support@carpoolbets.com"]}
            }
        }]
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 500
