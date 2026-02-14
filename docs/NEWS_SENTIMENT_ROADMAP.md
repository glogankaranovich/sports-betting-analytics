# News & Sentiment Data Integration Roadmap

## Overview
Add real-time news and social sentiment data to enhance betting predictions and provide Benny with breaking information.

## Phase 1: Twitter/X Integration (Week 1-2)

### 1.1 Twitter Data Collector
**File:** `backend/twitter_collector.py`

**Features:**
- Monitor team/player mentions
- Track beat reporters and verified accounts
- Detect injury/lineup keywords
- Collect sentiment scores
- Store in DynamoDB with TTL (24 hours)

**Data Structure:**
```python
{
    "pk": "SENTIMENT#basketball_nba#LAL",
    "sk": "2026-02-14T10:30:00Z",
    "sport": "basketball_nba",
    "team": "LAL",
    "sentiment_score": 0.65,  # -1 to 1
    "mention_count": 1250,
    "keywords": ["injury", "LeBron", "questionable"],
    "top_tweets": [...],
    "ttl": 1708012800
}
```

**Schedule:** Every 15 minutes via EventBridge

### 1.2 Sentiment Analysis Model
**File:** `backend/ml/sentiment_model.py`

**Inputs:**
- Recent Twitter sentiment (last 24h)
- Mention volume changes
- Keyword frequency (injury, trade, suspension)
- Beat reporter activity

**Output:**
- Sentiment shift indicator (-1 to 1)
- Confidence score
- Key factors driving sentiment

**Integration:**
- Add as data source to user models
- Feed into momentum model
- Alert Benny on major sentiment shifts

### 1.3 Infrastructure
- Lambda: `twitter-collector-{env}`
- EventBridge: Every 15 minutes
- DynamoDB: Use existing table with TTL
- Secrets Manager: Twitter API credentials

## Phase 2: Weather Data (Week 3)

### 2.1 Weather Collector
**File:** `backend/weather_collector.py`

**Features:**
- Collect weather for outdoor games (NFL, MLB, soccer)
- Wind speed, precipitation, temperature
- Store 48 hours before game time

**API Options:**
- OpenWeatherMap (free tier: 1000 calls/day)
- WeatherAPI (free tier: 1M calls/month)

**Data Structure:**
```python
{
    "pk": "WEATHER#{game_id}",
    "sk": "2026-02-14T10:30:00Z",
    "game_id": "abc123",
    "venue": "Lambeau Field",
    "temperature": 25,  # Fahrenheit
    "wind_speed": 15,   # mph
    "precipitation": 0.2,  # inches
    "conditions": "Snow"
}
```

**Schedule:** Every 6 hours for games in next 48h

### 2.2 Weather-Aware Model
**File:** `backend/ml/weather_model.py`

**Logic:**
- Cold weather: Lower scoring (NFL, MLB)
- Wind: Affects passing/kicking (NFL), fly balls (MLB)
- Rain: Lower scoring, more turnovers
- Dome games: No weather impact

**Integration:**
- Adjust over/under predictions
- Factor into game outcome confidence
- Alert Benny on extreme weather

## Phase 3: Line Movement Tracking (Week 4)

### 3.1 Line Movement Collector
**File:** `backend/line_movement_collector.py`

**Features:**
- Track odds changes over time
- Calculate line movement velocity
- Detect reverse line movement (RLM)
- Identify sharp vs public money

**Data Structure:**
```python
{
    "pk": "LINE_MOVEMENT#{game_id}",
    "sk": "fanduel#h2h#2026-02-14T10:30:00Z",
    "game_id": "abc123",
    "bookmaker": "fanduel",
    "market": "h2h",
    "home_odds_change": -15,  # moved from +110 to +95
    "away_odds_change": +10,
    "movement_velocity": "fast",  # slow/medium/fast
    "reverse_line_movement": true,
    "sharp_indicator": 0.8
}
```

**Schedule:** Every 30 minutes (use existing odds collector)

### 3.2 Sharp Money Model
**File:** `backend/ml/sharp_money_model.py`

**Logic:**
- Reverse line movement = sharp money
- Fast line movement = breaking news
- Slow steady movement = public money
- Compare across bookmakers

**Integration:**
- Contrarian model enhancement
- Benny follows sharp money
- Alert on RLM opportunities

## Phase 4: News Aggregation (Week 5-6)

### 4.1 News Collector
**File:** `backend/news_collector.py`

**Sources:**
- ESPN API (free)
- NewsAPI (free tier: 100 requests/day)
- Team RSS feeds
- Beat reporter blogs

**Features:**
- Keyword extraction (injury, trade, suspension)
- Categorize by impact (high/medium/low)
- Deduplicate similar stories
- Store with 7-day TTL

**Data Structure:**
```python
{
    "pk": "NEWS#{sport}#{team}",
    "sk": "2026-02-14T10:30:00Z",
    "sport": "basketball_nba",
    "team": "LAL",
    "headline": "LeBron James questionable for tonight",
    "source": "ESPN",
    "impact": "high",
    "keywords": ["injury", "LeBron James", "questionable"],
    "url": "https://...",
    "ttl": 1708617600
}
```

**Schedule:** Every 30 minutes

### 4.2 News Impact Model
**File:** `backend/ml/news_impact_model.py`

**Logic:**
- Weight news by source credibility
- Time decay (older news = less impact)
- Cross-reference with injury data
- Detect market overreaction

**Integration:**
- Feed all models with news context
- Benny prioritizes high-impact news
- User models can weight news importance

## Phase 5: Enhanced Benny Agent (Week 7)

### 5.1 Real-Time Alert System
**Features:**
- Monitor all data sources continuously
- Alert Benny on:
  - Major sentiment shifts (>0.3 change in 1 hour)
  - Breaking injury news
  - Reverse line movement
  - Extreme weather updates
  - Sharp money indicators

### 5.2 Benny Decision Engine Enhancement
**Updates to:** `backend/benny_trader.py`

**New Logic:**
- Wait for line movement after news breaks
- Fade public overreaction to news
- Follow sharp money on RLM
- Avoid betting in extreme weather (unless edge)
- Increase bet size on high-confidence news plays

## Implementation Priority

### Must Have (Weeks 1-2):
1. ✅ Twitter/X collector
2. ✅ Sentiment analysis model
3. ✅ Integration with user models

### Should Have (Weeks 3-4):
4. Weather collector (outdoor sports only)
5. Line movement tracking
6. Sharp money model

### Nice to Have (Weeks 5-7):
7. News aggregation
8. News impact model
9. Enhanced Benny alerts

## Technical Requirements

### New Dependencies:
```txt
tweepy>=4.14.0          # Twitter API
textblob>=0.17.1        # Sentiment analysis
requests>=2.31.0        # HTTP requests (already have)
feedparser>=6.0.10      # RSS feeds
```

### New AWS Resources:
- Lambda: `twitter-collector-{env}`
- Lambda: `weather-collector-{env}`
- Lambda: `news-collector-{env}`
- EventBridge: 3 new schedules
- Secrets Manager: Twitter API keys
- DynamoDB: Use existing table (add TTL)

### API Costs (Free Tiers):
- Twitter API: $100/month (Basic tier)
- OpenWeatherMap: Free (1000 calls/day)
- NewsAPI: Free (100 requests/day)
- **Total: ~$100/month**

## Success Metrics

### Data Quality:
- Sentiment accuracy: >70% correlation with outcomes
- News detection latency: <5 minutes from breaking
- Weather forecast accuracy: >80%

### Model Performance:
- Sentiment model: +2% accuracy improvement
- Weather model: +3% accuracy on outdoor games
- Sharp money model: +5% ROI on RLM plays

### Benny Performance:
- Faster bet placement (within 10 min of news)
- Higher win rate on news-driven bets (+5%)
- Better bankroll management (avoid bad weather games)

## Next Steps

1. **Apply for Twitter/X API access** ✅ (In progress)
2. Create `twitter_collector.py` skeleton
3. Set up EventBridge schedule
4. Build sentiment analysis model
5. Test with historical Twitter data
6. Deploy to dev environment
7. Monitor for 1 week before beta

## Questions to Resolve

- [ ] Twitter API tier (Basic $100/mo vs Free tier limits)?
- [ ] Store raw tweets or just aggregated sentiment?
- [ ] Real-time WebSocket vs polling for Twitter?
- [ ] Which weather API (OpenWeatherMap vs WeatherAPI)?
- [ ] News source priority (ESPN > Twitter > RSS)?
