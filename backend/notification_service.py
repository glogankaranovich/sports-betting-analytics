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


class EmailChannel(NotificationChannel):
    """Email delivery via AWS SES"""
    
    def __init__(self):
        self.ses = boto3.client('ses')
        self.from_email = os.environ.get('NOTIFICATION_FROM_EMAIL', 'noreply@carpoolbets.com')
    
    def send(self, recipient: str, message: str, metadata: Optional[Dict] = None) -> bool:
        """Send email via SES"""
        try:
            response = self.ses.send_email(
                Source=f'Benny Notifications <{self.from_email}>',
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': '🎯 Benny Placed a Bet!'},
                    'Body': {
                        'Text': {'Data': message}
                    }
                }
            )
            logger.info(f"Email sent successfully to {recipient}: {response['MessageId']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False


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


class DiscordChannel(NotificationChannel):
    """Discord delivery via webhook"""

    def __init__(self):
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

    def send(self, recipient: str, message: str, metadata: Optional[Dict] = None) -> bool:
        """Send message to Discord via webhook."""
        if not self.webhook_url:
            logger.error("DISCORD_WEBHOOK_URL not set")
            return False
        try:
            import json as _json
            from urllib import request as urllib_request
            # Discord max message length is 2000 chars
            truncated = message[:1990]
            data = _json.dumps({"content": truncated}).encode()
            req = urllib_request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "Benny/1.0"},
            )
            urllib_request.urlopen(req, timeout=5)
            logger.info("Discord notification sent")
            return True
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False


class NotificationService:
    """Central service for sending notifications"""
    
    def __init__(self):
        self.channels = {
            'email': EmailChannel(),
            'sms': SMSChannel(),
            'discord': DiscordChannel(),
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
        version = bet_details.get('version', 'v1')
        sport = bet_details.get('sport', 'Unknown').replace('_', ' ').title()
        game = bet_details.get('game', 'Unknown game')
        pick = bet_details.get('pick', 'Unknown')
        market = bet_details.get('market_key', 'h2h').upper()
        confidence = bet_details.get('confidence', 0) * 100
        stake = bet_details.get('stake', 0)
        odds = bet_details.get('odds', 0)
        bankroll_pct = bet_details.get('bankroll_percentage', 0) * 100
        expected_roi = bet_details.get('expected_roi', 0) * 100
        reasoning = bet_details.get('reasoning', 'No reason provided')
        
        # Format odds
        odds_str = f"{odds:+.0f}" if odds else "N/A"
        
        # Version indicator
        version_emoji = "🟢" if version == "v1" else "🔵"
        version_label = "Control" if version == "v1" else "Learning"
        
        message = f"""🎯 Benny {version_emoji} {version.upper()} ({version_label}) placed a bet!

Sport: {sport}
Game: {game}
Market: {market}
Pick: {pick} ({odds_str})
Confidence: {confidence:.1f}%
Stake: ${stake:.2f} ({bankroll_pct:.1f}% of bankroll)
Expected ROI: {expected_roi:.1f}%

Reason: {reasoning}"""
        
        return message

    def format_consensus_report(self, data: Dict) -> str:
        """Format consensus report comparing V1 and V3 bets."""
        date = data.get('date', 'Unknown')
        agree = data.get('agree', [])
        v1_only = data.get('v1_only', [])
        v3_only = data.get('v3_only', [])

        lines = [f"Benny Consensus Report — {date}", ""]

        if agree:
            same = [a for a in agree if a.get('same_pick')]
            diff = [a for a in agree if not a.get('same_pick')]
            if same:
                lines.append("🤝 Both Models Agree:")
                for a in same:
                    lines.append(
                        f"  {a['pick']} ({a['sport']}) — "
                        f"V1: {a['v1_conf']:.0%}, V3: {a['v3_conf']:.0%}, odds: {a['odds']:+.0f}"
                    )
                lines.append("")
            if diff:
                lines.append("⚔️ Same Game, Different Pick:")
                for a in diff:
                    lines.append(
                        f"  {a['sport']}: V1={a['pick']} ({a['v1_conf']:.0%}), "
                        f"V3={a.get('v3_pick', '?')} ({a['v3_conf']:.0%})"
                    )
                lines.append("")

        if v1_only:
            lines.append("V1 Only:")
            for b in v1_only:
                lines.append(
                    f"  {b['prediction']} ({b['sport']}) — "
                    f"conf: {b['confidence']:.0%}, ${b['bet_amount']:.2f}"
                )
            lines.append("")

        if v3_only:
            lines.append("V3 Only:")
            for b in v3_only:
                lines.append(
                    f"  {b['prediction']} ({b['sport']}) — "
                    f"conf: {b['confidence']:.0%}, ${b['bet_amount']:.2f}"
                )

        return "\n".join(lines)
