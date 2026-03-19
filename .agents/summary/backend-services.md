# Backend Services & Handlers

> Supporting Lambda handlers, APIs, and utility modules.

## Lambda Handlers

### `coaching_memo_generator.py` — Daily Coaching Memo
- Runs daily at 8:30 AM ET via EventBridge
- Instantiates `CoachingAgent` for BENNY and BENNY_V3
- Generates and stores coaching memos in DynamoDB

### `benny_trader_handler.py` — Benny Trader Lambda Entry
- Thin wrapper that invokes `benny_trader.lambda_handler`

### `benny_weekly_reporter.py` — Weekly Performance Reports
- Generates weekly and daily performance reports
- Sends via SES email

### `benny_ab_reporter.py` — A/B Model Comparison
- Compares V1 vs V3 performance daily
- Sends comparison report via SES

### `analysis_generator.py` — Public Game Analysis
- Generates AI-powered game analyses for the frontend
- Multiple analysis strategies (consensus, contrarian, momentum, etc.)

### `notification_service.py` / `notification_processor.py` — Notifications
- SQS-based notification pipeline
- Sends bet placement and settlement notifications

## Utility Modules

### `model_performance.py` — Performance Metrics
- Calculates ROI, win rate, Sharpe ratio per model

### `model_analytics.py` — Deep Analytics
- Advanced model performance analysis

### `elo_calculator.py` / `elo_handler.py` — Elo Ratings
- Calculates and serves Elo ratings per team

### `feature_flags.py` — Feature Toggles
- Controls feature rollout (sports, markets, models)

### `dao.py` — Data Access Object
- Shared DynamoDB access patterns

### `constants.py` — Shared Constants
- Sport keys, market types, API endpoints

### `ai_agent.py` / `ai_agent_api.py` — AI Chat Agent
- User-facing AI agent for the frontend
- Answers questions about bets, performance, strategy
