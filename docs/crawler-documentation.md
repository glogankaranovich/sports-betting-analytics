# Data Crawlers Documentation

## Overview

The sports betting analytics system uses two main crawlers to collect data:

1. **Sports Data Crawler** - Collects odds and game data from The Odds API
2. **Reddit Insights Crawler** - Extracts betting discussions and sentiment from Reddit

## Sports Data Crawler

### Data Source
- **API**: The Odds API (https://the-odds-api.com)
- **Authentication**: API key stored in AWS Secrets Manager
- **Rate Limit**: 10 requests per minute (free tier: 500 requests/month)

### Sports Covered
- NFL (American Football)
- NBA (Basketball) 
- MLB (Baseball)
- NHL (Ice Hockey)
- EPL (Soccer)
- UEFA Champions League

### Data Collected
```json
{
  "id": "event_unique_id",
  "sport": "americanfootball_nfl",
  "home_team": "Kansas City Chiefs",
  "away_team": "Buffalo Bills", 
  "commence_time": "2024-01-15T18:00:00Z",
  "bookmaker_odds": [
    {
      "bookmaker": "DraftKings",
      "markets": {
        "h2h": {"home": 1.85, "away": 2.10},
        "spreads": {"home": -3.5, "away": 3.5},
        "totals": {"over": 47.5, "under": 47.5}
      }
    }
  ]
}
```

### Collection Process
1. **API Request**: GET `/v4/sports/{sport}/odds`
2. **Rate Limiting**: 6-second delay between requests
3. **Data Validation**: Pydantic models ensure data integrity
4. **Storage**: DynamoDB (processed) + S3 (raw JSON backup)
5. **TTL**: Data expires after 30 days

### Error Handling
- **API Failures**: Logged and skipped, continues with other sports
- **Rate Limits**: Automatic backoff and retry
- **Timeout**: 12-minute Lambda limit with 3-minute buffer

## Reddit Insights Crawler

### Data Sources
**Target Subreddits:**
- `r/sportsbook` - Main betting discussions
- `r/sportsbetting` - General betting community
- `r/DraftKings` - DraftKings users
- `r/fanduel` - FanDuel users
- `r/nfl`, `r/nba`, `r/mlb`, `r/nhl` - Sport-specific discussions

### Web Crawling Method
- **API**: Reddit JSON API (`reddit.com/r/subreddit/hot.json`)
- **No Authentication**: Uses public endpoints
- **Rate Limiting**: 1 second between subreddit requests
- **User Agent**: "SportsAnalytics/1.0"

### Content Filtering

**Betting Keywords:**
```
"bet", "wager", "pick", "lock", "play", "odds", "line",
"spread", "moneyline", "over", "under", "prop", "parlay"
```

**Team Detection:**
```python
team_patterns = {
    "nfl": ["chiefs", "bills", "cowboys", "patriots", "packers"],
    "nba": ["lakers", "warriors", "celtics", "heat", "nets"],
    "mlb": ["yankees", "dodgers", "astros", "braves", "red sox"],
    "nhl": ["rangers", "bruins", "lightning", "avalanche", "kings"]
}
```

### Data Extracted
```json
{
  "post_id": "reddit_abc123",
  "sport": "american_football",
  "teams": ["Chiefs", "Bills"],
  "bet_type": "spread",
  "confidence": 0.75,
  "reasoning": "Chiefs -3.5 is a lock this week",
  "source_url": "https://reddit.com/r/sportsbook/abc123",
  "created_at": "2024-01-15T14:30:00Z"
}
```

### Confidence Scoring Algorithm
```python
confidence = 0.5  # Base confidence

# Post engagement
if post.score > 10: confidence += 0.2
if post.num_comments > 20: confidence += 0.1

# Language analysis
confident_words = ["lock", "sure", "confident", "guarantee"]
if any(word in text for word in confident_words): confidence += 0.1

uncertain_words = ["maybe", "might", "possibly", "unsure"]  
if any(word in text for word in uncertain_words): confidence -= 0.1

# Clamp between 0.1-0.9
return min(max(confidence, 0.1), 0.9)
```

## Automation & Scheduling

### CloudWatch Events
- **Sports Collection**: Every 4 hours
- **Reddit Collection**: Every 2 hours
- **Environment**: Disabled in dev (returns mock data)

### Lambda Configuration
- **Runtime**: Python 3.11
- **Timeout**: 15 minutes
- **Memory**: 512 MB
- **Environment Variables**:
  - `STAGE`: dev/staging/prod
  - `ODDS_API_SECRET_ARN`: Secret Manager ARN
  - `*_TABLE_NAME`: DynamoDB table names
  - `RAW_DATA_BUCKET_NAME`: S3 bucket for backups

### Manual Triggers
**API Gateway Endpoints:**
- `POST /collect/sports` - Trigger sports data collection
- `POST /collect/reddit` - Trigger Reddit insights collection

## Data Storage

### DynamoDB Schema
**Sports Data Table:**
```
Partition Key: sport (string)
Sort Key: collected_at (string)
Attributes: event_data (map), ttl (number)
```

**Reddit Insights:**
```
Partition Key: sport (string) 
Sort Key: collected_at (string)
Attributes: insight_data (map), ttl (number)
```

### S3 Backup
- **Raw JSON**: Complete API responses
- **Organized by**: `year/month/day/hour/`
- **Retention**: Lifecycle policy (30 days)

## Error Handling & Monitoring

### Logging
- **CloudWatch Logs**: All execution details
- **Structured Logging**: JSON format for easy parsing
- **Error Tracking**: Failed requests, timeouts, validation errors

### Metrics
- **Execution Time**: Lambda duration tracking
- **Success Rate**: Collection success/failure ratio
- **Data Volume**: Events collected per run
- **API Usage**: Rate limit monitoring

### Alerts (Future)
- Lambda failures
- API rate limit exceeded
- Data collection gaps

## Development & Testing

### Local Development
```bash
# Set environment variables
export THE_ODDS_API_KEY="your_key_here"
export STAGE="dev"

# Run crawler
cd backend/crawler
python -c "
import asyncio
from scheduler import DataCollectionExecutor
executor = DataCollectionExecutor()
result = asyncio.run(executor.collect_all_sports())
print(result)
"
```

### Testing
- **Unit Tests**: 15 tests covering core logic
- **Mock Data**: Reddit API responses, odds data
- **Integration Tests**: End-to-end pipeline validation

### Environment Behavior
- **Dev**: Mock responses, no actual data collection
- **Staging**: Real data collection for testing
- **Prod**: Full data collection and storage

## Security

### API Keys
- **Storage**: AWS Secrets Manager
- **Access**: Lambda IAM role with read permissions
- **Rotation**: Manual (can be automated)

### Rate Limiting
- **The Odds API**: 10 requests/minute
- **Reddit**: 1 request/second per subreddit
- **Backoff**: Exponential retry on failures

### Data Privacy
- **Public Data Only**: No private Reddit content
- **No PII**: Only betting discussions and odds
- **Compliance**: Respects robots.txt and rate limits
