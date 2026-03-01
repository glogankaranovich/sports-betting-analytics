"""
Notification service for sending alerts via multiple channels.
"""
import os
import boto3
from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract base class for notification delivery"""
    
    @abstractmethod
    def send(self, recipient: str, message: str, metadata: Optional[Dict] = None) -> bool:
        """Send notification to recipient"""
        pass


class SMSChannel(NotificationChannel):
    """SMS delivery via AWS SNS Topic"""
    
    def __init__(self):
        self.sns = boto3.client('sns')
        self.topic_arn = os.environ.get('NOTIFICATION_TOPIC_ARN')
    
    def send(self, recipient: str, message: str, metadata: Optional[Dict] = None) -> bool:
        """Send SMS via SNS Topic"""
        if not self.topic_arn:
            logger.error("NOTIFICATION_TOPIC_ARN not set")
            return False
        
        try:
            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            logger.info(f"SMS sent successfully via topic: {response['MessageId']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS via topic: {str(e)}")
            return False


class NotificationService:
    """Central service for sending notifications"""
    
    def __init__(self):
        self.channels = {
            'sms': SMSChannel(),
        }
    
    def send_notification(
        self, 
        channel: str, 
        recipient: str, 
        message: str, 
        metadata: Optional[Dict] = None
    ) -> bool:
        """Send notification via specified channel"""
        if channel not in self.channels:
            logger.error(f"Unknown notification channel: {channel}")
            return False
        
        return self.channels[channel].send(recipient, message, metadata)
    
    def format_bet_notification(self, bet_details: Dict) -> str:
        """Format bet details into notification message"""
        sport = bet_details.get('sport', 'Unknown').replace('_', ' ').title()
        game = bet_details.get('game', 'Unknown game')
        pick = bet_details.get('pick', 'Unknown')
        confidence = bet_details.get('confidence', 0) * 100
        stake = bet_details.get('stake', 0)
        bankroll_pct = bet_details.get('bankroll_percentage', 0) * 100
        expected_roi = bet_details.get('expected_roi', 0) * 100
        reasoning = bet_details.get('reasoning', 'No reason provided')
        
        message = f"""🎯 Benny placed a bet!

Sport: {sport}
Game: {game}
Pick: {pick}
Confidence: {confidence:.1f}%
Stake: ${stake:.2f} ({bankroll_pct:.1f}% of bankroll)
Expected ROI: {expected_roi:.1f}%

Reason: {reasoning}"""
        
        return message
