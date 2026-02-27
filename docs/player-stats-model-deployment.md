# Player Stats Model - Production Deployment

**Date:** February 26, 2026  
**Status:** ✅ Deployed to Production  
**Model Type:** Prop Betting (Player Performance)

## Overview

The Player Stats Model is a specialized prop betting model that uses historical player performance data, opponent matchups, news sentiment, and injury status to predict player prop outcomes.

## Performance Metrics (90-Day Backtest)

### NBA Props
- **Accuracy:** 53.7% (vs 41.2% baseline)
- **ROI (Wagered):** -2.00% (vs -21.32% baseline)
- **Improvement:** +12.5% accuracy, +19.32% ROI
- **Predictions:** 54 bets analyzed
- **Status:** Nearly profitable (expected to be profitable with live odds vs assumed -110)

### Comparison to Other Prop Models
| Model | Accuracy | ROI | Status |
|-------|----------|-----|--------|
| **Player Stats** | 53.7% | -2.00% | ✅ Best performer |
| Value | 41.2% | -21.32% | ❌ Losing |
| Momentum | 29.4% | -52.94% | ❌ Losing |

## Model Features

### 1. Historical Player Stats
- Queries last 20 games per player
- Weighted average: 75% recent (last 5 games), 25% season average
- Filters out games with <20 minutes played
- Tracks: PTS, REB, AST, STL, BLK, 3PM, +/-

### 2. Opponent Matchups
- Uses player's historical performance vs specific opponent
- Requires 2+ games against opponent for adjustment
- Weighted 30% opponent history, 70% overall average

### 3. Streak Detection
- Only bets on significant form changes (15-25% deviation)
- Requires positive plus/minus for lower streaks
- Avoids betting on stable/average performance

### 4. News Sentiment Integration
- Checks last 48 hours of news for player mentions
- ±2% confidence boost based on sentiment and impact
- Uses AWS Comprehend for sentiment analysis

### 5. Injury Filtering
- Queries injury data before making predictions
- Skips players with "Out" or "Doubtful" status
- Prevents betting on unavailable players

### 6. Selective Betting
- 13.5% threshold: Only bets when line is significantly mispriced
- Line must be <86.5% or >113.5% of predicted value
- Reduces bet volume but increases accuracy

## Data Sources

### Player Stats Collection
- **Source:** ESPN API
- **Frequency:** Daily at 2 AM ET during season
- **Storage:** `PLAYER_STATS#{sport}#{normalized_name}` / `{date}#{opponent}`
- **Coverage:** 1,437+ NBA players with 20-game history

### News Collection
- **Source:** ESPN News API
- **Frequency:** Every 2 hours
- **Storage:** `NEWS#{sport}` / `{timestamp}`
- **Fields:** headline, description, sentiment_positive, sentiment_negative, impact

### Injury Collection
- **Source:** ESPN Injuries API
- **Frequency:** Every 2 hours
- **Storage:** `PLAYER_INJURY#{sport}#{normalized_name}` / `LATEST`
- **Coverage:** 103 NBA injuries tracked

## Technical Implementation

### Model Class
**File:** `backend/ml/player_stats_model.py`

**Key Methods:**
- `analyze_prop_odds()` - Main prediction logic
- `analyze_game_odds()` - Returns None (props only)
- `_get_player_stats()` - Queries historical performance
- `_get_news_boost()` - Calculates sentiment adjustment
- `_is_player_injured()` - Checks injury status

### Market Support
```python
market_map = {
    'player_points': 'PTS',
    'player_rebounds': 'REB',
    'player_assists': 'AST',
    'player_threes': '3PM',
    'player_steals': 'STL',
    'player_blocks': 'BLK',
}
```

### Prediction Logic
1. Check if player is injured (skip if Out/Doubtful)
2. Get player stats with opponent filter
3. Calculate weighted average (75% recent, 25% season)
4. Add opponent adjustment if available (30% weight)
5. Get news sentiment boost (±2%)
6. Check streak requirements (15-25% form change)
7. Apply 13.5% threshold filter
8. Return prediction with confidence

## Infrastructure Integration

### System Models Registration
**File:** `infrastructure/lib/utils/constants.ts`
```typescript
SYSTEM_MODELS: 'consensus,value,momentum,contrarian,hot_cold,rest_schedule,matchup,injury_aware,news,player_stats,ensemble'
```

### EventBridge Schedules
- **Frequency:** Every 4 hours
- **Sports:** NBA, NFL, MLB, NHL, EPL
- **Bet Type:** Props only (returns None for games)
- **Staggered:** 2-minute offsets to avoid throttling

### Lambda Configuration
- **Function:** `analysis-generator-{sport}-{env}`
- **Runtime:** Python 3.11
- **Memory:** 2048 MB
- **Timeout:** 15 minutes
- **Trigger:** EventBridge rule with `{sport: 'basketball_nba', model: 'player_stats', bet_type: 'props'}`

## Dynamic Weighting

The model is automatically included in the ensemble with ROI-based weighting:

**File:** `backend/ml/dynamic_weighting.py`

**Algorithm:**
1. Query last 90 days of verified predictions
2. Calculate ROI per model
3. Exclude models with ROI ≤ 0
4. Normalize weights to sum to 1.0

**Current Weight:** TBD (needs 90 days of production data)

## Deployment History

### February 26, 2026
1. ✅ Created player stats model with historical data
2. ✅ Added opponent matchup adjustments
3. ✅ Integrated news sentiment boost
4. ✅ Added injury filtering
5. ✅ Registered in ensemble
6. ✅ Added to SYSTEM_MODELS constant
7. ✅ Deployed to production

### Commits
- `c8a0ae2` - feat: add injury filtering to player stats model
- `4585d37` - feat: add player_stats model and remove benny from system models

## Next Steps

### Immediate (Post-Deployment)
1. Monitor first 24 hours of predictions
2. Verify EventBridge schedules are running
3. Check CloudWatch logs for errors
4. Validate predictions are stored correctly

### Short-Term (1-2 Weeks)
1. Collect 90 days of verified predictions for ROI calculation
2. Re-backtest with live odds (not assumed -110)
3. Adjust threshold if needed (currently 13.5%)
4. Monitor accuracy and ROI trends

### Long-Term (1-3 Months)
1. Expand to other sports (NHL, NFL, MLB)
2. Add defensive rating data (opponent strength vs position)
3. Test different weighting schemes (recent vs season)
4. Consider home/away splits
5. Add venue-specific adjustments

## Monitoring

### Key Metrics to Track
- **Accuracy:** Target >52.4% (break-even at -110 odds)
- **ROI:** Target >0% (currently -2%)
- **Bet Volume:** ~50-100 props per week per sport
- **Confidence Distribution:** Should be 55-65% range

### CloudWatch Alarms
- Alert if model returns 0 predictions for 24 hours
- Alert if accuracy drops below 45%
- Alert if injury collector fails
- Alert if news collector returns 0 articles

### DynamoDB Queries
```python
# Check recent predictions
pk = 'ANALYSIS#player_stats#basketball_nba#props'
sk >= '2026-02-26'

# Check verified outcomes
pk = 'VERIFIED#player_stats#basketball_nba#props'
sk >= '2026-02-26'
```

## Troubleshooting

### Model Returns No Predictions
1. Check if injury collector is running (should have 100+ injuries)
2. Verify player stats exist (query `PLAYER_STATS#basketball_nba#*`)
3. Check if threshold is too strict (13.5% may filter too many)
4. Verify news collector is running (should have recent articles)

### Low Accuracy
1. Review which markets are performing poorly (points vs rebounds)
2. Check if injury filtering is working (should skip Out/Doubtful)
3. Verify opponent matchup data is being used
4. Consider adjusting streak detection thresholds

### High Bet Volume
1. Increase threshold from 13.5% to 15% or 20%
2. Add minimum confidence requirement (e.g., >60%)
3. Reduce streak detection range (e.g., 20-25% instead of 15-25%)

## References

- [Backtesting Framework](./backtest-results-nba-90d.md)
- [Model Improvement Workflow](.kiro/steering/model-improvement-workflow.md)
- [Dynamic Weighting System](../backend/ml/dynamic_weighting.py)
- [Player Stats Model Code](../backend/ml/player_stats_model.py)
