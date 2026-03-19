# Benny Engines & Support Modules

> Internal modules powering the betting system's learning, bankroll, and execution.

## Files (all in `backend/benny/`)

### `coaching_agent.py` — LLM Coaching Memo Generator
- `CoachingAgent(table, pk)` — gathers 30d settled bets, feature insights, calibration, variance data
- `generate_memo()` — builds structured summary, sends to Claude, stores memo in DynamoDB
- `get_memo()` — single `get_item` to read stored memo
- Explore/Avoid with cooldowns: markets with 20+ bets and <35% win rate get 30-day cooldown, then auto-move to EXPLORE
- Cooldown dates persisted in `cooldowns` map on the COACHING_MEMO item
- DynamoDB: `pk={PK}#LEARNING`, `sk=COACHING_MEMO`

### `learning_engine.py` — Adaptive Parameter Learning
- `LearningEngine(table, pk)` — reads/writes learning parameters
- Tracks win rates, sport performance, confidence calibration
- `update_from_result()` — updates params after each bet settles
- `get_perf_warnings()` — generates warnings for underperforming areas
- DynamoDB: `pk={PK}#LEARNING`, `sk=PARAMS`

### `bankroll_manager.py` — Bankroll Tracking
- `BankrollManager(table, pk)` — reads/updates bankroll
- `update_bankroll(amount)` — atomic bankroll update
- DynamoDB: `pk={PK}`, `sk=BANKROLL`

### `bet_executor.py` — Bet Placement
- `BetExecutor(table, pk, bankroll_manager)` — writes bets to DynamoDB
- `place_bet()` — creates bet record with prediction, confidence, odds, reasoning
- Handles duplicate detection, bankroll deduction

### `parlay_engine.py` — Parlay Construction
- `ParlayEngine(table, pk)` — builds multi-leg parlays from individual picks
- `build_parlays()` — combines qualifying bets into 2-4 leg parlays
- Calculates combined odds and confidence

### `position_manager.py` — Live Position Management
- `PositionManager(table, pk)` — manages open positions
- Cash-out logic, double-down opportunities
- Tracks position P&L

### `feature_extractor.py` — Feature Engineering
- Extracts structured features from game data for analysis
- Elo differentials, rest days, home/away, travel fatigue

### `opportunity_analyzer.py` — Opportunity Scoring
- Scores betting opportunities based on multiple factors
- Filters low-quality opportunities

### `outcome_analyzer.py` — Feature Performance Analysis
- `OutcomeAnalyzer(table, pk)` — analyzes which features predict wins
- `analyze_features()` — win rate by feature range
- `analyze_confidence_calibration()` — stated vs actual confidence
- DynamoDB: `pk={PK}#LEARNING`, `sk=FEATURES|CALIBRATION`

### `threshold_optimizer.py` — Adaptive Thresholds
- `ThresholdOptimizer(table, pk)` — optimizes confidence thresholds per sport/market
- `optimize_thresholds()` — finds optimal threshold based on historical performance
- DynamoDB: `pk={PK}#LEARNING`, `sk=THRESHOLDS`

### `variance_tracker.py` — Statistical Variance Analysis
- `VarianceTracker(table, pk)` — tracks if results are within expected variance
- ROI percentile, bets needed for significance
- DynamoDB: `pk={PK}#LEARNING`, `sk=VARIANCE`
