# Notification System Design

## MVP: Benny Bet Notifications via SMS

### Architecture Principles

1. **Pluggable Delivery Channels** - Abstract notification delivery behind an interface
2. **Event-Driven** - Trigger notifications from events (Benny placing bets)
3. **Decoupled** - Use SQS queue to separate bet placement from notification delivery
4. **Extensible** - Easy to add new channels, triggers, and preferences later

### Components

#### 1. SQS Queue

**Purpose:** Decouple bet placement from notification delivery

```
Benny places bet → Send message to SQS → Continue
                         ↓
                    Notification Processor Lambda
                         ↓
                    Send via SNS/SES/etc
```

**Benefits:**
- Benny doesn't wait for notification delivery
- Automatic retries if notification fails
- Easy to add batching/rate limiting later
- Multiple consumers can process notifications

#### 2. Notification Processor Lambda

**File:** `backend/notification_processor.py`

```python
def lambda_handler(event, context):
    """Process notification events from SQS"""
    from notification_service import NotificationService
    
    service = NotificationService()
    
    for record in event['Records']:
        message = json.loads(record['body'])
        
        notification_type = message['type']  # 'bet_placed', 'high_confidence', etc.
        data = message['data']
        
        if notification_type == 'bet_placed':
            # For MVP: hardcoded phone from env
            phone = os.environ.get('BENNY_NOTIFICATION_PHONE')
            if phone:
                formatted_message = service.format_bet_notification(data)
                service.send_notification('sms', phone, formatted_message, data)
```

#### 3. Notification Service (Backend)

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

class NotificationService:
    """Central service for sending notifications"""
    def __init__(self):
        self.channels = {
            'sms': SMSChannel(),
        }
    
    def send_notification(self, channel: str, recipient: str, message: str, metadata: dict = None):
        """Send notification via specified channel"""
        if channel not in self.channels:
            raise ValueError(f"Unknown channel: {channel}")
        return self.channels[channel].send(recipient, message, metadata or {})
    
    def format_bet_notification(self, bet_details: dict) -> str:
        """Format bet details into notification message"""
        # Format message
        pass
```

#### 4. Benny Trader Integration

**Modify:** `backend/benny_trader.py`

After Benny places a bet, send event to SQS:

```python
def __init__(self, table_name=None):
    # ... existing code ...
    self.sqs = boto3.client('sqs')
    self.notification_queue_url = os.environ.get('NOTIFICATION_QUEUE_URL')

def _send_bet_notification(self, bet: dict, opportunity: dict):
    """Send bet notification event to SQS"""
    if not self.notification_queue_url:
        return
    
    message = {
        'type': 'bet_placed',
        'data': {
            'sport': opportunity['sport'],
            'game': f"{opportunity['away_team']} @ {opportunity['home_team']}",
            'pick': opportunity['prediction'],
            'confidence': float(opportunity['confidence']),
            'stake': float(bet['bet_amount']),
            'bankroll_percentage': float(bet['bet_amount'] / self.bankroll),
            'expected_roi': float(opportunity.get('expected_value', 0)),
            'reasoning': opportunity['reasoning']
        }
    }
    
    try:
        self.sqs.send_message(
            QueueUrl=self.notification_queue_url,
            MessageBody=json.dumps(message)
        )
    except Exception as e:
        # Log but don't fail bet placement
        print(f"Failed to send notification event: {e}")
```

#### 5. Infrastructure

**New Stack:** `infrastructure/lib/notification-stack.ts`

```typescript
// SQS Queue for notification events
const notificationQueue = new sqs.Queue(this, 'NotificationQueue', {
  queueName: `bet-notifications-${environment}`,
  visibilityTimeout: cdk.Duration.seconds(30),
  retentionPeriod: cdk.Duration.days(1),
});

// Dead letter queue for failed notifications
const dlq = new sqs.Queue(this, 'NotificationDLQ', {
  queueName: `bet-notifications-dlq-${environment}`,
  retentionPeriod: cdk.Duration.days(14),
});

notificationQueue.addDeadLetterQueue({
  queue: dlq,
  maxReceiveCount: 3,
});

// Notification processor Lambda
const notificationProcessor = new lambda.Function(this, 'NotificationProcessor', {
  functionName: `notification-processor-${environment}`,
  runtime: lambda.Runtime.PYTHON_3_11,
  handler: 'notification_processor.lambda_handler',
  code: lambda.Code.fromAsset('../backend', {
    bundling: {
      image: lambda.Runtime.PYTHON_3_11.bundlingImage,
      command: [
        'bash', '-c',
        'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
      ],
    },
  }),
  timeout: cdk.Duration.seconds(30),
  environment: {
    BENNY_NOTIFICATION_PHONE: '+1234567890',  // From SSM Parameter Store in production
  },
});

// Grant SNS publish permissions
notificationProcessor.addToRolePolicy(new iam.PolicyStatement({
  actions: ['sns:Publish'],
  resources: ['*'],
}));

// SQS trigger
notificationProcessor.addEventSource(new SqsEventSource(notificationQueue, {
  batchSize: 10,
}));

// Grant Benny Trader permission to send to queue
notificationQueue.grantSendMessages(bennyTraderFunction);

// Add queue URL to Benny environment
bennyTraderFunction.addEnvironment('NOTIFICATION_QUEUE_URL', notificationQueue.queueUrl);
```

### Message Format

**SQS Message:**
```json
{
  "type": "bet_placed",
  "data": {
    "sport": "basketball_nba",
    "game": "Lakers @ Warriors",
    "pick": "Lakers +5.5",
    "confidence": 0.72,
    "stake": 45.0,
    "bankroll_percentage": 0.045,
    "expected_roi": 0.082,
    "reasoning": "Strong value with recent momentum"
  }
}
```

**SMS Message:**
```
🎯 Benny placed a bet!

Sport: NBA
Game: Lakers @ Warriors
Pick: Lakers +5.5
Confidence: 72%
Stake: $45 (4.5% of bankroll)
Expected ROI: 8.2%

Reason: Strong value with recent momentum
```

### Future Extensions (No Architecture Changes Needed)

1. **Add Email Channel** - Implement `EmailChannel` class, add to channels dict
2. **Add Push Notifications** - Implement `PushChannel` class
3. **User Preferences** - Query DynamoDB in processor, send to multiple recipients
4. **Other Triggers** - Send different message types to same queue
5. **Batching** - Process multiple notifications together (digest emails)
6. **Rate Limiting** - Track sends per user in DynamoDB

### Cost Considerations

- **SQS**: First 1M requests/month free, then $0.40 per million
- **SNS SMS**: ~$0.00645 per message (US)
- **Lambda**: Essentially free at this scale

For MVP with 1 user and ~5 Benny bets/day: ~$1/month

### Implementation Order

1. ✅ Create `NotificationService` with SMS channel
2. ✅ Create `notification_processor.py` Lambda handler
3. ✅ Create notification infrastructure stack (SQS + Lambda)
4. ✅ Add SQS client to Benny Trader
5. ✅ Integrate queue send in Benny Trader
6. ✅ Deploy and test with real bet
7. 🔮 Add user preferences table (later)
8. 🔮 Add API endpoints for preferences (later)
9. 🔮 Add frontend UI (later)

### Testing

```bash
# Test SQS message
aws sqs send-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/.../bet-notifications-dev \
  --message-body '{"type":"bet_placed","data":{...}}'

# Test SMS delivery directly
aws sns publish \
  --phone-number "+1234567890" \
  --message "Test notification from Benny" \
  --region us-east-1
```

### Error Handling

- **SQS send fails**: Log error, continue with bet placement
- **Notification send fails**: Retry up to 3 times, then move to DLQ
- **Invalid phone number**: Log error, don't retry
- **SNS throttling**: Automatic backoff via SQS visibility timeout
