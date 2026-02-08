# Feature Requests & Roadmap

## Phase 3: Advanced AI & Data Features

### 1. Benny Privacy & Model Access Control
**Priority:** High  
**Status:** Planned

**Requirements:**
- Benny should have read access to all models in the system for learning/analysis
- Users can only see/query their own models via Benny
- Implement model ownership checks in AI Agent tool execution
- Add privacy filters to RAG queries (filter by user_id)
- Benny can reference aggregate statistics without exposing individual model details

**Technical Approach:**
- Add `user_id` parameter to all AI Agent tool calls
- Filter DynamoDB queries by `user_id` in tool implementations
- Update RAG context to include only user's models + aggregate stats
- Add permission checks before returning model details

**Estimated Effort:** 2-3 days

---

### 2. Historical Backtesting System
**Priority:** High  
**Status:** Planned

**Requirements:**
- Fetch historical odds from The Odds API (one-time bulk import)
- Store historical odds in DynamoDB with date ranges
- Allow users to backtest their models against historical data
- Backtest existing system models (NBA, NFL, MLB, NHL, EPL)
- Generate performance reports (ROI, win rate, profit/loss over time)
- UI for selecting date ranges and viewing backtest results

**Technical Approach:**
- Create `historical_odds_collector.py` Lambda to fetch historical data
- Add `historical_odds` partition in DynamoDB (PK: `HISTORICAL_ODDS#{sport}#{date}`)
- Create `backtesting_engine.py` to replay historical games with model predictions
- Add `backtest_model` API endpoint
- Store backtest results in DynamoDB for comparison
- Add Benny tool: `backtest_model(model_id, start_date, end_date)`

**Data Storage:**
```
PK: HISTORICAL_ODDS#NBA#2024-01-15
SK: GAME#{game_id}
Data: {odds, teams, date, outcome}
```

**API Endpoints:**
- `POST /backtest/run` - Run backtest for a model
- `GET /backtest/results/{backtest_id}` - Get backtest results
- `GET /backtest/history` - List user's backtests

**Estimated Effort:** 1-2 weeks

---

### 3. Benny's Autonomous Trading Model
**Priority:** Medium  
**Status:** Planned

**Requirements:**
- Benny creates and manages its own betting model
- $100/week budget (virtual or real)
- Continuously learns from wins/losses
- Tracks performance metrics (ROI, win rate, bankroll)
- Uses earnings/losses to adjust future bet sizing
- Dashboard to monitor Benny's performance
- Benny can explain its betting decisions

**Technical Approach:**
- Create `benny_trader.py` autonomous agent
- Store Benny's model in DynamoDB: `PK: MODEL#benny-autonomous`
- Track bankroll: `PK: BENNY_BANKROLL`, `SK: WEEK#{date}`
- Scheduled Lambda (daily) to:
  1. Analyze upcoming games
  2. Generate predictions using Benny's model
  3. Place virtual bets (or real via API integration)
  4. Track outcomes and update model weights
- Use reinforcement learning approach (reward = profit/loss)
- Add Benny dashboard page showing:
  - Current bankroll
  - Bet history
  - Performance charts
  - Model evolution over time

**Data Storage:**
```
PK: BENNY_BET#{date}
SK: BET#{game_id}
Data: {amount, odds, prediction, outcome, profit_loss, reasoning}
```

**Estimated Effort:** 2-3 weeks

---

### 4. Custom Data Import & Social Media Integration
**Priority:** Medium  
**Status:** Planned

**Requirements:**
- Users can upload CSV/JSON data files
- Create models based on custom data sources
- Integrate Discord/Twitter feeds as data sources
- Parse social sentiment and incorporate into predictions
- Support for custom data schemas
- Data validation and sanitization

**Technical Approach:**

**Custom Data Import:**
- Add `POST /data/upload` endpoint (S3 upload)
- Parse CSV/JSON and store in DynamoDB
- User-defined schema mapping
- Data preview and validation UI

**Social Media Integration:**
- Create `social_feed_collector.py` Lambda
- Integrate Discord API (webhooks or bot)
- Integrate Twitter API (v2)
- Use sentiment analysis (AWS Comprehend or Bedrock)
- Store social signals: `PK: SOCIAL#{source}#{date}`, `SK: POST#{id}`
- Add social sentiment as model data source option

**Model Configuration:**
```json
{
  "data_sources": [
    {"type": "custom_csv", "file_id": "abc123"},
    {"type": "discord", "channel_id": "xyz789"},
    {"type": "twitter", "account": "@sportsguru"}
  ]
}
```

**Estimated Effort:** 3-4 weeks

---

### 5. Environment-Specific Email Addresses
**Priority:** Low  
**Status:** Planned

**Requirements:**
- Beta emails: `info@beta.carpoolbets.com`, `support@beta.carpoolbets.com`
- Prod emails: `info@carpoolbets.com`, `support@carpoolbets.com`
- Email subject/body includes environment tag
- Easy to identify which environment emails originate from

**Technical Approach:**

**Option A: Subdomain Emails (Recommended)**
- Configure Route 53 for `beta.carpoolbets.com` subdomain
- Update SES to verify subdomain
- Deploy separate email stacks per environment
- Beta: `info@beta.carpoolbets.com` → `glogankaranovich+beta@gmail.com`
- Prod: `info@carpoolbets.com` → `glogankaranovich@gmail.com`

**Option B: Subject Line Tagging**
- Keep current email addresses
- Modify Lambda forwarder to add `[BETA]` or `[PROD]` to subject
- Simpler but less professional

**Implementation:**
- Update `email-stack.ts` to accept environment parameter
- Configure subdomain in Route 53
- Update SES receipt rules per environment
- Update frontend to use environment-specific emails

**Estimated Effort:** 1-2 days

---

## Implementation Priority

1. **Phase 3.1** (Next Sprint):
   - Feature 1: Benny Privacy & Model Access Control
   - Feature 5: Environment-Specific Emails

2. **Phase 3.2** (Following Sprint):
   - Feature 2: Historical Backtesting System

3. **Phase 3.3** (Future):
   - Feature 3: Benny's Autonomous Trading Model
   - Feature 4: Custom Data Import & Social Media Integration

---

## Notes

- All features should integrate with existing Benny AI Agent
- Maintain responsible gambling compliance throughout
- Consider API rate limits for external integrations
- Ensure data privacy and security for user-uploaded data
- Monitor costs for historical data storage and API calls
