# Sports Betting Analytics Platform - System Architecture

## Overview

A full-stack sports betting analytics platform that collects odds data, generates AI-powered predictions, tracks model performance, and provides an autonomous betting agent (Benny). The system learns from outcomes and automatically adjusts model confidence based on performance.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  - Game odds display                                             │
│  - Model predictions & analysis                                  │
│  - User model builder                                            │
│  - Model comparison dashboard                                    │
│  - Benny AI assistant                                            │
└────────────────┬────────────────────────────────────────────────┘
                 │ HTTPS/REST API
                 │ (Cognito Auth)
┌────────────────▼────────────────────────────────────────────────┐
│                    API Gateway (REST API)                        │
│  - /games, /analyses, /model-comparison                          │
│  - /user-models, /benny/dashboard                                │
│  - Cognito authorizer for protected endpoints                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬──────────────┬──────────────┐
    │            │            │              │              │
┌───▼───┐  ┌────▼────┐  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
│ Bet   │  │ User    │  │ Analysis │  │ Outcome  │  │ Benny    │
│ API   │  │ Models  │  │ Generator│  │ Collector│  │ Trader   │
│Lambda │  │ Lambda  │  │ Lambda   │  │ Lambda   │  │ Lambda   │
└───┬───┘  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
    │           │            │              │              │
    └───────────┴────────────┴──────────────┴──────────────┘
                             │
                    ┌────────▼────────┐
                    │   DynamoDB      │
                    │  (Single Table) │
                    │                 │
                    │  - Games/Odds   │
                    │  - Predictions  │
                    │  - Outcomes     │
                    │  - User Models  │
                    │  - Benny Bets   │
                    └─────────────────┘
```

## Core Components

### 1. Data Collection Layer

**Odds Collector** (`odds_collector.py`)
- Runs every 4 hours via EventBridge
- Fetches odds from The Odds API for 5 sports (NBA, NFL, MLB, NHL, EPL)
- Stores h2h (moneyline), spreads, and totals
- Marks latest odds with `latest=true` flag
- Deduplicates using game_id + bookmaker + market_key

**Player Stats Collector** (`player_stats_collector.py`)
- Collects player statistics for NBA/NFL
- Used for prop bet analysis
- Stores in `PLAYER_STATS#{sport}#{player}` format

**Team Stats Collector** (`team_stats_collector.py`)
- Collects team-level statistics
- Used for game analysis and recent form
- Stores in `TEAM_STATS#{sport}#{team}` format

**Injury Collector** (`injury_collector.py`)
- Tracks player injuries
- Impacts model predictions
- Stores in `INJURIES#{sport}#{team}` format

**Outcome Collector** (`outcome_collector.py`)
- Runs every 4 hours
- Fetches completed game results (last 3 days)
- Verifies model predictions (original + inverse)
- Settles Benny bets with actual odds payouts
- Stores team-specific outcomes for recent form queries

### 2. Analysis & Prediction Layer

**Analysis Generator** (`analysis_generator.py`)
- Runs every 4-6 hours via EventBridge
- Generates predictions for all 10 system models:
  - consensus, value, momentum, contrarian
  - hot_cold, rest_schedule, matchup, injury_aware
  - ensemble, benny
- Applies dynamic confidence adjustments
- Stores predictions with `#LATEST` and `#INVERSE` versions

**System Models** (`ml/models.py`)
- **ConsensusModel**: Averages bookmaker odds
- **ValueModel**: Finds odds discrepancies
- **MomentumModel**: Recent team performance
- **ContrariModel**: Bets against public
- **HotColdModel**: Streak-based predictions
- **RestScheduleModel**: Back-to-back game analysis
- **MatchupModel**: Head-to-head history
- **InjuryAwareModel**: Adjusts for injuries
- **EnsembleModel**: Combines multiple models

**Dynamic Weighting** (`ml/dynamic_weighting.py`)
- Calculates model performance (accuracy, Brier score)
- Adjusts confidence based on recent results:
  - Inverse better: 0.3x multiplier (70% penalty)
  - <50% accuracy: Direct scaling
  - 50-60%: 0.8x-1.0x (slight reduction)
  - >60%: 1.0x-1.2x (boost)
- Caches adjustments for 24 hours

**Model Adjustment Calculator** (`model_adjustment_calculator.py`)
- Runs daily to calculate performance adjustments
- Stores recommendations: ORIGINAL, INVERSE, or AVOID
- Includes confidence multipliers for each model

### 3. User Models System

**User Model Executor** (`user_model_executor.py`)
- Processes user-defined models from SQS queue
- Evaluates 5 data sources with custom weights:
  - Team stats, odds movement, injuries
  - Recent form, head-to-head history
- Generates predictions based on weighted scores

**User Models API** (`user_models.py`)
- CRUD operations for user models
- Stores model configuration (weights, thresholds)
- Tracks model status (active/paused)
- Max 5 models per user

**Backtest Engine** (`backtest_engine.py`)
- Tests user models on historical data
- Calculates accuracy, ROI, win rate
- Helps users optimize model weights

### 4. Benny - Autonomous Trading Agent

**Benny Trader** (`benny_trader.py`)
- AI-powered autonomous betting agent
- Analyzes games independently using Claude 3.5 Sonnet
- Manages $100/week virtual bankroll
- Places bets using Kelly Criterion (half-Kelly)
- Stores bets with actual American odds
- Tracks performance: ROI, win rate, profit/loss

**Bet Settlement**
- Outcome collector settles Benny bets automatically
- Calculates payouts using actual odds:
  - Positive odds: profit = (bet × odds) / 100
  - Negative odds: profit = bet / (|odds| / 100)
- Updates bankroll with winnings
- Tracks bet status: pending → won/lost

### 5. Performance Tracking & Learning

**Inverse Prediction System**
- Every prediction generates an inverse (opposite outcome)
- Inverse confidence = 1.0 - original confidence
- Both versions verified when outcomes collected
- Reveals models that should be bet against

**Model Comparison Dashboard**
- Compares original vs inverse accuracy
- Shows which models to use, invert, or avoid
- Includes user models alongside system models
- Filters by sport and timeframe (7/30/90 days)

**Verified Analysis GSI**
- Indexes: `VERIFIED#{model}#{sport}#{bet_type}[#inverse]`
- Enables efficient performance queries
- Tracks accuracy over time
- Powers dynamic confidence adjustments

### 6. API Layer

**Bet Collector API** (`api_handler.py`)
- Main REST API for frontend
- Endpoints:
  - `/games` - Get games with odds
  - `/analyses` - Get model predictions
  - `/model-comparison` - Compare model performance
  - `/user-models` - CRUD for user models
  - `/benny/dashboard` - Benny performance stats
- Cognito authorization for protected endpoints

### 7. Infrastructure

**DynamoDB Single Table Design**
```
PK                              SK                          GSI1PK              GSI1SK
─────────────────────────────────────────────────────────────────────────────────────
GAME#{game_id}                  {bookmaker}#h2h#{timestamp} GAME#{sport}        {commence_time}
GAME#{game_id}                  {bookmaker}#spreads#...     
ANALYSIS#{sport}#{game_id}#...  {model}#game#LATEST         ANALYSIS#{sport}... {commence_time}
ANALYSIS#{sport}#{game_id}#...  {model}#game#INVERSE        
OUTCOME#{sport}#{game_id}       RESULT                      
TEAM_OUTCOME#{sport}#{team}     {timestamp}#{game_id}       TEAM#{sport}#{team} {timestamp}
VERIFIED#{model}#{sport}#game   {timestamp}                 
USER_MODEL#{user_id}            {model_id}                  
BENNY                           BET#{timestamp}#{game_id}   BENNY#BETS          {commence_time}
BENNY                           BANKROLL                    
MODEL_ADJUSTMENT#{sport}#game   {model}                     
```

**Key GSIs:**
- **ActiveBetsIndexV2**: Query games by sport and time
- **AnalysisTimeGSI**: Query predictions by model/sport
- **VerifiedAnalysisGSI**: Query verified predictions for performance
- **TeamOutcomesIndex**: Query team's recent games
- **UserModelsIndex**: Query user's models

**EventBridge Schedules:**
- Odds collection: Every 4 hours
- Analysis generation: Every 4-6 hours
- Outcome collection: Every 4 hours
- Model adjustments: Daily

**Amplify Hosting:**
- Frontend deployed to Amplify
- Beta and Prod environments
- Automatic deployments from GitHub

## Data Flow

### Prediction Generation Flow
```
1. EventBridge triggers Analysis Generator
2. Query upcoming games from DynamoDB
3. For each model:
   a. Model analyzes game data
   b. Generates base prediction + confidence
   c. Dynamic weighting adjusts confidence
   d. Store original prediction
   e. Generate and store inverse prediction
4. Predictions available via API
```

### Outcome Verification Flow
```
1. EventBridge triggers Outcome Collector
2. Fetch completed games from Odds API (last 3 days)
3. For each completed game:
   a. Store game outcome
   b. Store team-specific outcomes (2 per game)
   c. Query all predictions for this game
   d. Verify original predictions
   e. Verify inverse predictions
   f. Settle Benny bets
   g. Update bankroll
4. Performance data available for model comparison
```

### User Model Execution Flow
```
1. User creates model via UI
2. Model stored in DynamoDB
3. User Model Queue Loader adds to SQS
4. User Model Executor processes from queue
5. Evaluates 5 data sources with custom weights
6. Generates prediction
7. Stores in DynamoDB with user_model_id
```

### Benny Trading Flow
```
1. EventBridge triggers Benny Trader daily
2. Query upcoming games (next 24 hours)
3. For each game:
   a. Gather data (odds, stats, injuries, H2H, form)
   b. AI analyzes using Claude 3.5 Sonnet
   c. If confidence >= 65%:
      - Calculate bet size (Kelly Criterion)
      - Store bet with odds
      - Store as analysis for verification
      - Deduct from bankroll
4. When game completes:
   a. Outcome collector verifies result
   b. Calculate payout using actual odds
   c. Update bet status (won/lost)
   d. Update bankroll
```

## Key Design Decisions

### Single Table Design
- All data in one DynamoDB table
- Reduces costs and latency
- Enables complex queries with GSIs
- Requires careful PK/SK design

### Inverse Predictions
- Reveals models that consistently predict wrong
- Doubles verification data for learning
- Enables "bet against" strategies
- Minimal storage overhead

### Dynamic Confidence Adjustment
- Applied per-model, not just ensemble
- Cached for 24 hours for efficiency
- Automatically penalizes bad models
- Boosts high-performing models

### Benny as Analysis Records
- Benny predictions stored as analysis records
- Enables outcome verification
- Tracks performance in leaderboard
- Consistent with system models

### User Model Limits
- Max 5 models per user
- Prevents abuse
- Encourages quality over quantity
- Reduces compute costs

## Monitoring & Observability

**CloudWatch Metrics:**
- Lambda invocations, errors, duration
- DynamoDB read/write capacity
- API Gateway requests, latency

**Logging:**
- All Lambdas log to CloudWatch
- Structured logging with context
- Error tracebacks for debugging

**Alarms:**
- Lambda error rates
- DynamoDB throttling
- API Gateway 5xx errors

## Security

**Authentication:**
- Cognito user pools
- JWT tokens for API access
- Protected endpoints require auth

**Authorization:**
- User-scoped data access
- User models isolated by user_id
- API validates user ownership

**Data Protection:**
- Secrets in Secrets Manager
- IAM roles with least privilege
- VPC endpoints for DynamoDB (optional)

## Scalability

**Current Limits:**
- ~25 games per day (NBA + NFL)
- 10 system models
- Unlimited users
- 5 models per user
- $100/week Benny bankroll

**Scaling Considerations:**
- DynamoDB auto-scales
- Lambda concurrent executions
- API Gateway throttling
- Amplify CDN for frontend

## Cost Optimization

**Strategies:**
- Single table design reduces costs
- Cached model adjustments reduce queries
- EventBridge schedules minimize runs
- Amplify free tier for hosting
- Lambda free tier for compute

**Estimated Monthly Costs:**
- DynamoDB: $10-20
- Lambda: $5-10
- API Gateway: $5-10
- Amplify: Free tier
- Bedrock (Benny): $10-30
- **Total: ~$30-70/month**

## Future Enhancements

1. **More Sports**: Add more leagues (NCAAB, NCAAF, etc.)
2. **Prop Bets**: Expand to player props
3. **Live Betting**: Real-time odds updates
4. **Model Marketplace**: Share/sell user models
5. **Advanced Analytics**: Sharpe ratio, max drawdown
6. **Mobile App**: Native iOS/Android apps
7. **Notifications**: Push alerts for high-value bets
8. **Social Features**: Follow other users, leaderboards

---

**Last Updated:** 2026-02-11
**Version:** 1.0
