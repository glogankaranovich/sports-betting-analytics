# Code Audit - February 11, 2026

## Overview
24 commits shipped today with ~6,688 lines of code added. This document audits each feature.

## Test Status
- **303 passing** (92%)
- **15 failing** (pre-existing issues)
- **10 errors** (pre-existing issues)

---

## Features Shipped Today

### 1. Model Learning System (Core Feature)

#### 1.1 Inverse Prediction Tracking
**Commit:** 3f124e2
**Purpose:** Track both original and inverse predictions to identify models that should be bet against
**Files Changed:**
- `backend/outcome_collector.py` - Stores inverse predictions
- `backend/api_handler.py` - Queries inverse predictions

**What it does:**
- For every prediction, stores the opposite prediction with inverted confidence
- When outcomes verified, marks both original and inverse as correct/incorrect
- Reveals which models consistently predict wrong

**Testing Status:**
- [ ] Unit tests exist?
- [ ] Manual test in dev
- [ ] Verified in DynamoDB

**Concerns:**
- Doubles the number of prediction records stored
- Impact on query performance?

---

#### 1.2 Model Performance Comparison Dashboard
**Commit:** 41c58b5, 0f7ceca
**Purpose:** Frontend view comparing original vs inverse accuracy
**Files Changed:**
- `frontend/src/components/ModelComparison.tsx` (273 lines added)
- `backend/api_handler.py` - `/model-comparison` endpoint
- `infrastructure/lib/bet-collector-api-stack.ts` - API Gateway resource

**What it does:**
- Shows accuracy for both original and inverse predictions side-by-side
- Recommends: ORIGINAL (use as-is), INVERSE (bet against), or AVOID
- Filters by sport, timeframe (7/30/90 days)
- Includes user models

**Testing Status:**
- [ ] Frontend loads without errors
- [ ] API returns valid data
- [ ] Recommendations make sense

**Concerns:**
- New frontend component - tested on all screen sizes?
- API performance with large datasets?

---

#### 1.3 Dynamic Confidence Adjustment
**Commit:** b8e19c4, 6fc794c
**Purpose:** Automatically reduce confidence for underperforming models
**Files Changed:**
- `backend/ml/dynamic_weighting.py` (167 lines changed)
- `backend/model_adjustment_calculator.py` (67 lines added)
- `backend/analysis_generator.py` - Applies adjustments

**What it does:**
- Calculates accuracy for each model (last 30 days)
- Applies confidence multiplier:
  - <50% accuracy: 0.4x-0.5x (penalty)
  - 50-60%: 0.8x-1.0x (slight reduction)
  - >60%: 1.0x-1.2x (boost)
- Caches adjustments for 24 hours

**Testing Status:**
- [ ] Adjustments calculated correctly
- [ ] Cache working
- [ ] Predictions show adjusted confidence

**Concerns:**
- 1 failing test: `test_calculate_adjusted_confidence_reduce`
- Cache miss fallback tested?

---

#### 1.4 Automatic Weight Adjustment for User Models
**Commit:** 89c229a, 8494e33
**Purpose:** User models auto-optimize based on data source performance
**Files Changed:**
- `backend/user_model_weight_adjuster.py` (185 lines added)
- `backend/user_models.py` - Added `auto_adjust_weights` flag

**What it does:**
- Weekly Lambda scans models with `auto_adjust_weights=true`
- Calculates accuracy per data source (last 30 days)
- Redistributes weights proportionally to accuracy
- Requires 10+ predictions, 5+ per source

**Testing Status:**
- [ ] Lambda deployed?
- [ ] EventBridge schedule configured?
- [ ] Weight adjustments stored correctly

**Concerns:**
- Is the Lambda actually scheduled to run?
- What if all sources perform poorly?

---

#### 1.5 Model ROI Rankings
**Commit:** 288c38f, 4575cd7, 9dbd9c9
**Purpose:** Rank models by profitability, not just accuracy
**Files Changed:**
- `backend/api_handler.py` - `/model-rankings` endpoint
- `frontend/src/App.tsx` - Ticker display

**What it does:**
- Calculates ROI by simulating $100 bets using actual odds
- Tracks: total bets, wins, losses, profit, Sharpe ratio
- Displays top 5 in ticker

**Testing Status:**
- [x] API returns data (tested with curl)
- [ ] ROI calculations correct
- [ ] Ticker displays properly

**Concerns:**
- **CRITICAL:** All ROI values are 0% because odds aren't stored in verified predictions
- Changed ticker from "Top Profitable" to "Top Accurate" as workaround
- Need to populate `recommended_odds` field (partially done today)

---

#### 1.6 Benny Bet Settlement System
**Commit:** 72dca1f, 836ecab
**Purpose:** Automatically settle Benny's virtual bets when outcomes verified
**Files Changed:**
- `backend/outcome_collector.py` - Settlement logic
- `backend/benny_trader.py` - Stores odds with bets

**What it does:**
- When outcomes collected, finds pending Benny bets
- Calculates payout using actual American odds
- Updates bet status (won/lost) and bankroll
- Robust team name matching (3-tier)

**Testing Status:**
- [ ] Bets settle correctly
- [ ] Payout calculations accurate
- [ ] Bankroll updates properly

**Concerns:**
- 5 failing Benny tests
- Team name matching edge cases?

---

#### 1.7 Historical Odds Preservation
**Commit:** 292aff6
**Purpose:** Keep historical odds instead of deleting via TTL
**Files Changed:**
- `backend/backfill_historical_odds.py` (159 lines changed)
- `backend/odds_cleanup.py` (57 lines added)
- `backend/odds_collector.py` - Removed TTL

**What it does:**
- Removes TTL from odds records
- Archives old odds to separate partition
- Enables backtesting with historical odds

**Testing Status:**
- [ ] TTL actually removed?
- [ ] Archiving working?
- [ ] Storage costs acceptable?

**Concerns:**
- DynamoDB storage will grow indefinitely
- Need monitoring for table size

---

### 2. Infrastructure Changes

#### 2.1 TeamOutcomesIndex GSI
**Commit:** 5c7d49f
**Purpose:** Efficient queries for recent team performance
**Files Changed:**
- `infrastructure/lib/dynamodb-stack.ts`

**Testing Status:**
- [ ] GSI deployed?
- [ ] Queries using new index?

---

#### 2.2 Removed Features
**Commit:** 6d804e8, 2d9a806
**Removed:**
- `allow_benny_access` flag (deemed unnecessary)
- Infrastructure tests (not maintained)

**Concerns:**
- Why remove infrastructure tests?

---

## Critical Issues to Address

### Priority 1: Broken Tests
1. **Benny Trader Tests (5 failing)**
   - `test_weekly_reset`
   - `test_analyze_games_filters_confidence`
   - `test_place_bet_success`
   - `test_handler_success`
   - `test_handler_no_bets`
   - `test_handler_time_window`

2. **Backtest Engine (2 failing)**
   - `test_evaluate_game_home_win`
   - `test_evaluate_game_away_win`

3. **Custom Data (4 failing)**
   - `test_init_with_defaults`
   - `test_from_dynamodb`
   - `test_list_benny_accessible_all_sports`
   - `test_list_benny_accessible_filtered_by_sport`

4. **Dynamic Weighting (1 failing)**
   - `test_calculate_adjusted_confidence_reduce`

5. **Outcome Collector (1 failing)**
   - `test_store_outcome`

6. **User Models API (1 failing)**
   - `test_list_user_models`

### Priority 2: Missing Data
- **ROI calculations return 0%** - Need to populate `recommended_odds` in all predictions
- Partially fixed today (added field to models.py) but not deployed yet

### Priority 3: Deployment Status
- [ ] Are new Lambdas deployed? (model_adjustment_calculator, user_model_weight_adjuster)
- [ ] Are EventBridge schedules configured?
- [ ] Are new API endpoints live?
- [ ] Is frontend deployed with ticker changes?

---

## Action Items

### Immediate (Before Any Deployment)
1. [ ] Fix all 15 failing tests
2. [ ] Manual test each feature in dev environment
3. [ ] Verify DynamoDB schema changes deployed
4. [ ] Check Lambda deployment status
5. [ ] Test frontend changes on localhost

### Before Production Deploy
1. [ ] Deploy `recommended_odds` changes to start collecting odds data
2. [ ] Verify model leaderboard shows accurate data
3. [ ] Test Benny bet settlement with real outcomes
4. [ ] Verify inverse predictions stored correctly
5. [ ] Check DynamoDB storage costs

### Documentation
1. [ ] Update user-facing docs about new features
2. [ ] Document breaking changes (ticker display changed)
3. [ ] Add monitoring for new features

---

## Rollback Plan
If critical issues found:
1. Revert commits: `git revert e4772e4~24..e4772e4`
2. Or cherry-pick only working commits
3. Keep audit branch for reference

---

## Sign-off Checklist
- [ ] All tests passing
- [ ] Manual testing complete
- [ ] No breaking changes to existing features
- [ ] Performance acceptable
- [ ] Ready for production

**Status:** 🔴 NOT READY - Multiple failing tests and missing data
