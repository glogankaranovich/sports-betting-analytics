# Backtesting System - Implementation Plan

**Created:** February 8, 2026  
**Status:** In Progress - Historical Data Backfill Running

---

## Current State

### ✅ Completed
1. **Historical odds backfill script** (`backend/backfill_historical_odds.py`)
   - Fetches historical odds from The Odds API
   - Stores in DynamoDB with correct schema (pk/sk, game_index_pk/sk)
   - Converts floats to Decimal for DynamoDB compatibility
   - Supports dev, staging, and prod environments

2. **Parallel execution script** (`ops/run_backfill.sh`)
   - Runs backfill across all 3 environments in tmux
   - Configurable date range (default: 3 months)
   - Usage: `./ops/run_backfill.sh YOUR_API_KEY [YEARS]`

3. **Backfill currently running**
   - Dev, staging, and prod environments loading historical odds
   - Date range: ~3 months back (API limitation on historical data)
   - Sports: NBA, NFL, NHL, MLB, EPL

### 🚧 In Progress
- Historical odds backfill completing (check tmux session: `tmux attach -t backfill-historical`)

---

## What's Needed for Full Backtesting

### 1. Historical Outcomes Collection

**Problem:** We have historical odds but not historical game outcomes (who won, final scores)

**Solution Options:**

**Option A: Backfill from ESPN API**
```python
# Create: backend/backfill_historical_outcomes.py
# For each historical game in DynamoDB:
#   - Query ESPN API for final score
#   - Store outcome in DynamoDB
#   - Link to existing odds data
```

**Option B: Use The Odds API scores endpoint**
```python
# The Odds API has historical scores
# Endpoint: /v4/historical/sports/{sport}/scores
# Can fetch alongside odds data
```

**Recommendation:** Option B - same API, consistent data source

### 2. Update Backfill Script to Include Outcomes

**File:** `backend/backfill_historical_odds.py`

**Changes needed:**
```python
# After fetching odds, also fetch scores for completed games
def _fetch_historical_scores(self, sport: str, timestamp: str):
    url = f"{self.base_url}/sports/{sport}/scores"
    # Fetch and store outcomes

# Store outcome alongside odds
def _store_outcome(self, game: Dict, sport: str):
    item = {
        "pk": f"GAME#{sport}#{game_id}",
        "sk": "OUTCOME",
        "game_id": game_id,
        "sport": sport,
        "home_score": game["scores"]["home"],
        "away_score": game["scores"]["away"],
        "completed": True,
        "completed_at": game["completed_at"],
        "historical_backfill": True
    }
    self.table.put_item(Item=item)
```

### 3. Fix Backtest Engine

**File:** `backend/backtest_engine.py`

**Current issues:**
- Uses non-existent GSI1 index
- Doesn't match current data schema
- Missing outcome lookup logic

**Changes needed:**
```python
def _fetch_historical_games(self, sport: str, start_date: str, end_date: str):
    """Fetch historical games with outcomes"""
    games = []
    
    # Query by game_index to find all games
    # Filter for games with outcomes
    # Use commence_time for date filtering
    
    # For each game:
    #   - Fetch all odds snapshots
    #   - Fetch outcome
    #   - Combine into game object
    
    return games

def _evaluate_game(self, game: Dict, model_config: Dict):
    """Run user model on historical game"""
    # Use historical odds at game time (not current)
    # Run model evaluators with historical data
    # Compare prediction to actual outcome
    # Calculate profit/loss based on odds
    
    return prediction_result
```

### 4. Historical Stats Collection (Optional - Phase 2)

**For more accurate backtesting:**

- Historical team stats at game time
- Historical player stats at game time
- Historical injury reports
- Historical line movement (multiple snapshots per game)

**Current limitation:** Models that use team/player stats will use current stats, not historical

**Workaround:** Start with odds-movement and recent-form models only

---

## Implementation Steps

### Phase 1: Basic Backtesting (2-3 days)

1. **Add outcomes to backfill script**
   - Modify `backfill_historical_odds.py` to fetch scores
   - Store outcomes in DynamoDB
   - Re-run backfill for all environments

2. **Fix backtest engine**
   - Update `_fetch_historical_games()` to use correct GSI
   - Add outcome lookup logic
   - Fix data schema references

3. **Test end-to-end**
   - Create test user model
   - Run backtest on 1 month of data
   - Verify metrics calculation
   - Check UI display

### Phase 2: Enhanced Backtesting (1-2 weeks)

4. **Add historical stats**
   - Backfill team stats at game time
   - Backfill player stats at game time
   - Update model evaluators to use historical data

5. **Add more metrics**
   - ROI by bet type
   - Sharpe ratio
   - Max drawdown
   - Win rate by confidence level

6. **UI improvements**
   - Backtest results visualization
   - Performance charts
   - Comparison to baseline models

---

## Data Schema

### Historical Odds
```
pk: GAME#{sport}#{game_id}
sk: ODDS#{bookmaker}#{market}
game_index_pk: {game_id}
game_index_sk: ODDS#{bookmaker}#{market}
commence_time: ISO timestamp
outcomes: [{"name": "Home", "price": Decimal(110)}]
historical_backfill: true
```

### Historical Outcomes (to add)
```
pk: GAME#{sport}#{game_id}
sk: OUTCOME
game_index_pk: {game_id}
game_index_sk: OUTCOME
home_score: Decimal
away_score: Decimal
completed: true
completed_at: ISO timestamp
historical_backfill: true
```

### Backtest Results
```
pk: USER#{user_id}
sk: BACKTEST#{backtest_id}
model_id: string
start_date: ISO timestamp
end_date: ISO timestamp
total_predictions: number
metrics: {
  accuracy: Decimal,
  roi: Decimal,
  total_profit: Decimal,
  win_rate: Decimal
}
predictions: [...]  # First 100
created_at: ISO timestamp
```

---

## API Endpoints (Already Exist)

```
POST /user-models/{model_id}/backtests
  - Create new backtest
  - Body: {start_date, end_date}
  - Returns: backtest_id

GET /user-models/{model_id}/backtests
  - List all backtests for model
  
GET /user-models/{model_id}/backtests/{backtest_id}
  - Get backtest details and results
```

---

## Cost Estimates

### The Odds API
- Historical odds: $0.01 per request
- Historical scores: $0.01 per request
- 3 months × 5 sports × ~90 days = ~450 requests per environment
- Total: ~$13.50 for all 3 environments

### DynamoDB
- Storage: ~1-2 GB historical data = ~$0.25/month
- Reads during backtest: Pay-per-request, minimal cost
- Writes during backfill: One-time, ~$1-2

**Total one-time cost:** ~$15-20

---

## Testing Checklist

### Before Backfill
- [x] Script handles Decimal conversion
- [x] Script uses correct DynamoDB keys
- [x] Script handles API errors gracefully
- [x] Timestamp format is correct (no microseconds)

### After Backfill
- [ ] Verify data in DynamoDB (spot check games)
- [ ] Check data completeness (all sports, all dates)
- [ ] Verify odds format is correct
- [ ] Check API usage and cost

### Backtest Engine
- [ ] Can fetch historical games by date range
- [ ] Can run model on historical data
- [ ] Calculates metrics correctly
- [ ] Stores results properly
- [ ] UI displays results

---

## Next Session TODO

1. **Check backfill completion**
   ```bash
   tmux attach -t backfill-historical
   # Review completion status in each window
   ```

2. **Verify data loaded**
   ```bash
   # Check item count increased
   AWS_PROFILE=sports-betting-dev aws dynamodb describe-table \
     --table-name carpool-bets-v2-dev \
     --query 'Table.ItemCount'
   
   # Spot check a game
   AWS_PROFILE=sports-betting-dev aws dynamodb query \
     --table-name carpool-bets-v2-dev \
     --index-name GameIndex \
     --key-condition-expression "game_index_pk = :gid" \
     --expression-attribute-values '{":gid":{"S":"SOME_GAME_ID"}}'
   ```

3. **Add outcomes to backfill script**
   - Modify `backend/backfill_historical_odds.py`
   - Add `_fetch_historical_scores()` method
   - Add `_store_outcome()` method
   - Re-run for completed games

4. **Fix backtest engine**
   - Update `backend/backtest_engine.py`
   - Fix GSI query
   - Add outcome lookup
   - Test with sample model

5. **Test end-to-end**
   - Create test user model via API
   - Run backtest
   - Verify results

---

## Questions to Resolve

1. **How far back should we backfill?**
   - Current: 3 months (API limitation)
   - Ideal: 1-2 years for robust backtesting
   - May need paid API tier for older data

2. **Should we store multiple odds snapshots per game?**
   - Current: One snapshot per day
   - Better: Opening line, -24h, -12h, -1h, closing
   - Enables line movement analysis

3. **How to handle missing data?**
   - Some games may not have complete odds
   - Some outcomes may be missing
   - Skip or estimate?

4. **Performance optimization?**
   - Backtest on 1000+ games could be slow
   - Cache intermediate results?
   - Batch processing?

---

## Files Modified Tonight

- `backend/backfill_historical_odds.py` - Fixed timestamp format, Decimal conversion, schema keys
- `ops/run_backfill.sh` - Created tmux parallel execution script

## Files to Modify Next

- `backend/backfill_historical_odds.py` - Add outcomes collection
- `backend/backtest_engine.py` - Fix GSI query and outcome lookup
- `backend/user_model_executor.py` - Ensure works with historical data

---

**Status:** Ready to resume. Historical odds backfill running overnight. Next step: add outcomes and fix backtest engine.
