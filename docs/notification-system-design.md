# Notification System Design

## MVP: Benny Bet Notifications via SMS

### Architecture Principles

1. **Pluggable Delivery Channels** - Abstract notification delivery behind an interface
2. **Event-Driven** - Trigger notifications from events (Benny placing bets)
3. **Extensible** - Easy to add new channels, triggers, and preferences later

### Components

#### 1. Notification Service (Backend)

**File:** `backend/notification_service.py`

```python
class NotificationChannel(ABC):
    """Abstract base class for notification delivery"""
    @abstractmethod
    def send(self, recipient: str, message: str, metadata: dict) -> bool:
        pass

class SMSChannel(NotificationChannel):
    """SMS delivery via SNS"""
    def send(self, phone_number: str, message: str, metadata: dict) -> bool:
        # Use SNS to send SMS
        pass

class EmailChannel(NotificationChannel):
    """Email delivery via SES (future)"""
    pass

class PushChannel(NotificationChannel):
    """Push notifications (future)"""
    pass

class NotificationService:
    """Central service for sending notifications"""
    def __init__(self):
        self.channels = {
            'sms': SMSChannel(),
            # 'email': EmailChannel(),  # Add later
            # 'push': PushChannel(),     # Add later
        }
    
    def send_notification(self, channel: str, recipient: str, message: str, metadata: dict = None):
        """Send notification via specified channel"""
        if channel not in self.channels:
            raise ValueError(f"Unknown channel: {channel}")
        return self.channels[channel].send(recipient, message, metadata or {})
```

#### 2. Benny Trader Integration

**Modify:** `backend/benny_trader.py`

After Benny places a bet, publish an event:

```python
# After placing bet
self._send_bet_notification(bet_details)

def _send_bet_notification(self, bet_details: dict):
    """Send notification when bet is placed"""
    from notification_service import NotificationService
    
    service = NotificationService()
    message = self._format_bet_message(bet_details)
    
    # For MVP: hardcoded phone number from env var
    phone = os.environ.get('BENNY_NOTIFICATION_PHONE')
    if phone:
        service.send_notification('sms', phone, message, bet_details)
```

#### 3. Infrastructure

**New Stack:** `infrastructure/lib/notification-stack.ts`

```typescript
// SNS topic for notifications (optional, for future fan-out)
const notificationTopic = new sns.Topic(this, 'NotificationTopic', {
  topicName: `bet-notifications-${environment}`
});

// Grant Benny Trader permission to publish to SNS (for SMS)
bennyTraderFunction.addToRolePolicy(new iam.PolicyStatement({
  actions: ['sns:Publish'],
  resources: ['*']  // For SMS, SNS doesn't use topic ARNs
}));

// Environment variable for notification phone
bennyTraderFunction.addEnvironment('BENNY_NOTIFICATION_PHONE', '+1234567890');
```

### Message Format

```
🎯 Benny placed a bet!

Sport: NBA
Game: Lakers vs Warriors
Pick: Lakers +5.5
Confidence: 72%
Stake: $45 (4.5% of bankroll)
Expected ROI: 8.2%

Reason: Strong value with recent momentum
```

### Future Extensions (No Code Changes Needed)

1. **Add Email Channel** - Implement `EmailChannel` class, add to channels dict
2. **Add Push Notifications** - Implement `PushChannel` class
3. **User Preferences** - Store in DynamoDB, query before sending
4. **Multiple Recipients** - Loop through users with notifications enabled
5. **Other Triggers** - Call `NotificationService` from analysis generator for high-confidence bets

### Data Model (Future)

```python
# DynamoDB: Users table
{
  "user_id": "user123",
  "notification_preferences": {
    "enabled": true,
    "channels": ["sms", "email"],
    "phone_number": "+1234567890",
    "email": "user@example.com",
    "triggers": {
      "benny_bets": true,
      "high_confidence": false,  # Future
      "min_confidence": 0.70     # Future
    }
  }
}
```

### Cost Considerations

- **SNS SMS**: ~$0.00645 per message (US)
- **SES Email**: $0.10 per 1,000 emails
- **SNS Push**: Free (just data transfer)

For MVP with 1 user and ~5 Benny bets/day: ~$1/month

### Implementation Order

1. ✅ Create `NotificationService` with SMS channel
2. ✅ Add SNS permissions to Benny Trader
3. ✅ Integrate notification call in Benny Trader
4. ✅ Add phone number to environment variables
5. ✅ Test with real bet
6. 🔮 Add user preferences table (later)
7. 🔮 Add API endpoints for preferences (later)
8. 🔮 Add frontend UI (later)

### Security Notes

- Phone numbers stored as environment variables (MVP) or encrypted in DynamoDB (production)
- Use AWS Secrets Manager for sensitive notification credentials
- Rate limiting to prevent notification spam
- Opt-out mechanism required for SMS compliance

### Testing

```bash
# Test SMS delivery
aws sns publish \
  --phone-number "+1234567890" \
  --message "Test notification from Benny" \
  --region us-east-1
```
