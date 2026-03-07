"""
Unit tests for notification_service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from notification_service import NotificationService, EmailChannel, SMSChannel


class TestEmailChannel:
    @patch('notification_service.boto3')
    def test_send_success(self, mock_boto3):
        """Test successful email send"""
        mock_ses = Mock()
        mock_ses.send_email.return_value = {"MessageId": "msg123"}
        mock_boto3.client.return_value = mock_ses
        
        channel = EmailChannel()
        result = channel.send("test@example.com", "Test message")
        
        assert result is True
        mock_ses.send_email.assert_called_once()
    
    @patch('notification_service.boto3')
    def test_send_failure(self, mock_boto3):
        """Test email send failure"""
        mock_ses = Mock()
        mock_ses.send_email.side_effect = Exception("SES error")
        mock_boto3.client.return_value = mock_ses
        
        channel = EmailChannel()
        result = channel.send("test@example.com", "Test message")
        
        assert result is False


class TestSMSChannel:
    @patch('notification_service.boto3')
    @patch.dict('os.environ', {'NOTIFICATION_TOPIC_ARN': 'arn:aws:sns:us-east-1:123:topic'})
    def test_send_success(self, mock_boto3):
        """Test successful SMS send"""
        mock_sns = Mock()
        mock_sns.publish.return_value = {"MessageId": "msg123"}
        mock_boto3.client.return_value = mock_sns
        
        channel = SMSChannel()
        result = channel.send("+1234567890", "Test message")
        
        assert result is True
        mock_sns.publish.assert_called_once()
    
    @patch('notification_service.boto3')
    @patch.dict('os.environ', {})
    def test_send_no_topic_arn(self, mock_boto3):
        """Test SMS send without topic ARN"""
        channel = SMSChannel()
        result = channel.send("+1234567890", "Test message")
        
        assert result is False


class TestNotificationService:
    @patch('notification_service.EmailChannel')
    def test_send_notification_email(self, mock_email_class):
        """Test sending email notification"""
        mock_channel = Mock()
        mock_channel.send.return_value = True
        mock_email_class.return_value = mock_channel
        
        service = NotificationService()
        result = service.send_notification('email', 'test@example.com', 'Test message')
        
        assert result is True
    
    def test_format_bet_notification(self):
        """Test bet notification formatting"""
        service = NotificationService()
        data = {
            'game': 'Team A vs Team B',
            'prediction': 'Team A',
            'confidence': 0.75,
            'bet_amount': 10.50
        }
        
        message = service.format_bet_notification(data)
        
        assert 'Team A vs Team B' in message
        assert 'Team A' in message
        assert '75' in message or '0.75' in message
