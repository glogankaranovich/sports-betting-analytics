# Benny Trader - Future Improvements

## Performance Optimization

### Separate Learning for Props vs Games
**Priority**: Medium  
**Effort**: Low  
**Impact**: Medium

Currently, props and games share the same confidence adjustment parameters. A bad run on props can make Benny too conservative on games, or vice versa.

**Implementation**:
- Split `min_confidence_adjustment` into `game_confidence_adjustment` and `prop_confidence_adjustment`
- Calculate separate win rates for props (player_* markets) vs games (h2h, spreads, totals)
- Apply adjustments independently based on performance
- Require minimum 10 bets of each type before adjusting

**Code Location**: `backend/benny_trader.py` line 1583 (`update_learning_parameters`)

---

### Sport-Specific Confidence Thresholds
**Priority**: Low  
**Effort**: Medium  
**Impact**: Medium

Different sports may have different optimal confidence thresholds. NBA might be more predictable than NHL.

**Implementation**:
- Track win rate by sport in learning parameters (already done)
- Add `confidence_adjustment_by_sport` dict
- Apply sport-specific adjustments when evaluating opportunities
- Require minimum 20 bets per sport before adjusting

---

### Dynamic Kelly Fraction
**Priority**: Low  
**Effort**: Low  
**Impact**: Low

Currently uses fixed Kelly fraction (0.25). Could adjust based on recent volatility.

**Implementation**:
- Track rolling standard deviation of bet outcomes
- Reduce Kelly fraction during high volatility periods
- Increase during stable periods
- Cap between 0.1 and 0.5

---

## Data Management

### Add TTL to Old Odds
**Priority**: Low  
**Effort**: Low  
**Impact**: Low

Old game odds and props accumulate in DynamoDB. Not urgent unless costs climb.

**Implementation**:
- Add `ttl` attribute to odds records (6 hours after game start)
- Enable TTL on DynamoDB table
- Monitor storage costs first to see if needed

**Code Location**: `backend/odds_collector.py` and `backend/props_collector.py`

---

## Feature Enhancements

### Multi-Leg Parlay Support
**Priority**: Low  
**Effort**: High  
**Impact**: High

Benny currently only places single bets. Parlays could increase ROI but add complexity.

**Considerations**:
- Correlation between legs (avoid correlated outcomes)
- Increased variance
- Lower win rate but higher payouts
- Need parlay-specific Kelly calculation

---

### Live Betting
**Priority**: Low  
**Effort**: Very High  
**Impact**: Very High

Place bets during games based on live odds and game state.

**Requirements**:
- Real-time odds feed
- Live game data (score, time, possession)
- Fast execution (sub-second)
- Different models for live vs pre-game

---

### Hedge Existing Positions
**Priority**: Medium  
**Effort**: Medium  
**Impact**: Medium

If a bet is winning but odds have shifted, hedge to lock in profit.

**Implementation**:
- Monitor odds for active bets
- Calculate hedge opportunity (guaranteed profit)
- Place opposite bet if EV positive
- Track as related positions

---

## Monitoring & Observability

### Slack/Discord Notifications
**Priority**: Low  
**Effort**: Low  
**Impact**: Low

Currently only email notifications. Add real-time alerts.

**Implementation**:
- Add webhook URLs to secrets
- Send notifications for:
  - Bets placed
  - Large wins/losses
  - Lock stuck >10 minutes
  - Errors during execution

---

### Performance Dashboard Enhancements
**Priority**: Low  
**Effort**: Medium  
**Impact**: Low

Add more detailed analytics to Benny dashboard.

**Features**:
- Win rate by time of day
- Performance by odds range
- Bet size distribution
- Confidence vs actual outcome correlation
- Model performance breakdown (which models contribute most to wins)

---

## Risk Management

### Bet Correlation Detection
**Priority**: Medium  
**Effort**: Medium  
**Impact**: Medium

Avoid placing multiple correlated bets (e.g., team total + game total).

**Implementation**:
- Define correlation rules (same game, related markets)
- Check existing positions before placing new bet
- Skip or reduce size if correlation detected

---

### Maximum Exposure Limits
**Priority**: Low  
**Effort**: Low  
**Impact**: Low

Currently no limit on total exposure across all active bets.

**Implementation**:
- Track total amount at risk across active bets
- Cap at 50% of bankroll
- Skip new bets if limit reached

---

## Testing & Validation

### Backtesting Framework
**Priority**: Medium  
**Effort**: High  
**Impact**: High

Test Benny's strategy on historical data before deploying changes.

**Requirements**:
- Historical odds data
- Historical analysis records
- Simulate bet placement and outcomes
- Calculate hypothetical performance

---

### A/B Testing for Strategy Changes
**Priority**: Low  
**Effort**: High  
**Impact**: Medium

Run two versions of Benny simultaneously with different parameters.

**Implementation**:
- Split bankroll between strategies
- Track performance separately
- Promote winning strategy after sufficient data
