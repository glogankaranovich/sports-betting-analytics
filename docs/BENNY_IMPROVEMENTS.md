# Benny Trader - Future Improvements

## Performance Optimization

### ~~Accuracy & ROI Improvements (V1 + V3)~~ ✅ DONE (March 2026)
**Priority**: High
**Effort**: Medium
**Impact**: High

**Implemented across V1 and V3:**
- **Sport-specific edge floors**: NBA/NFL require 10% edge vs market, EPL/MLB/NHL 8%, NCAAB/MLS 6%. Prevents betting on thin margins in efficient markets.
- **Confidence calibration in bet decisions**: Maps raw AI confidence to actual win rate from settled bets. Rejects bets where calibrated confidence < market implied probability.
- **Calibration table in prompts**: Shows AI its own track record ("80% → 48% (overconfident)") so it self-corrects.
- **V1 `should_bet` upgraded**: Now enforces EV ≥ 5%, edge floor, and calibration gate (previously only checked confidence ≥ adaptive threshold).

**V3-only:**
- **ROI auto-gating**: Reads last 60 days of settled bets by sport|market. Blocks at -15% ROI (15+ bets), probation at -5% (requires extra 5% edge). Self-learning — no hardcoding.
- **Post-run ROI logging**: Prints gating status per sport|market combo.

**Coaching agent:**
- Replaced generic "KEY RULES" with "HARD RULES" requiring concrete factor-based thresholds (e.g., "RULE: Only bet favorites when ELO diff > +50").

**Code Locations**: `backend/benny/models/v1.py`, `backend/benny/models/v3.py`, `backend/benny/coaching_agent.py`

---

### ~~Separate Learning for Props vs Games~~ ✅ DONE (March 2026)
**Priority**: Medium  
**Effort**: Low  
**Impact**: Medium

~~Currently, props and games share the same confidence adjustment parameters.~~

**Implemented**: Market-type-aware confidence thresholds in `LearningEngine`:
- Game markets (h2h, spread, totals): 0.80 minimum confidence
- Prop markets (player_*): 0.65 minimum confidence
- Learned thresholds from DynamoDB override defaults when available
- Based on 30-day data showing props at 75-85% win rate / 63%+ ROI vs game bets at ~50% win rate / negative ROI

**Code Location**: `backend/benny/learning_engine.py` (`GAME_MARKET_CONFIDENCE`, `PROP_MARKET_CONFIDENCE`)

---

### ~~Sport-Specific Confidence Thresholds~~ ✅ INFRASTRUCTURE DONE (March 2026)
**Priority**: Low  
**Effort**: Medium  
**Impact**: Medium

~~Different sports may have different optimal confidence thresholds.~~

**Implemented**: `LearningEngine.get_adaptive_threshold()` checks DynamoDB for `by_sport` learned thresholds first, then falls back to market-type defaults. Infrastructure is in place — just needs enough settled bets per sport for the learning system to populate `BENNY#LEARNING` / `BENNY_V2#LEARNING` thresholds.

**Remaining**: Accumulate sufficient data (minimum 30 bets per sport) for learned thresholds to kick in.

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

### ~~A/B Testing for Strategy Changes~~ ✅ DONE (February 2026)
**Priority**: Low  
**Effort**: High  
**Impact**: Medium

**Implemented**: BENNY and BENNY_V2 run simultaneously with separate bankrolls ($147.01 each), separate learning parameters, and independent bet tracking. A/B reporter compares performance across versions. Both versions share infrastructure but maintain isolated state in DynamoDB.
