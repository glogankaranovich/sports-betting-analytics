# Benny Trader - Improvements & Current Plan

## Current Architecture (March 2026)

### Self-Correction System (replaces coaching memo)
The AI now sees raw performance data directly in every prompt instead of an LLM-generated coaching memo. This eliminates the "telephone game" of one LLM interpreting data and another LLM interpreting the interpretation.

**What the AI sees before every bet:**
1. **Calibration table** — "you said 70% confident, you actually won 44%". Forceful wording: "We WILL remap your confidence. Adjust your outputs."
2. **Recent losses per sport** — last 5 losses with prediction, confidence, and reasoning
3. **Recent wins per sport** — last 5 wins to reinforce good patterns
4. **Factor track record** — which `key_factors` correlate with wins vs losses (e.g., "✓ Elo advantage: 12/18 (67%) — trust this" / "✗ Recent form: 3/11 (27%) — misleads you")
5. **Sport/market win rates** — raw record by market (e.g., "h2h: 8/15 (53%), spread: 3/12 (25%)")

**Calibration in bet decisions:** Both V1 and V3 reject bets where calibrated confidence < market implied probability. V1 also uses calibrated confidence for Kelly sizing.

**Code:** `base.py` (shared helpers), `v1.py`, `v3.py` (prompts), `benny_trader.py` (bet flow)

### Shadow Bet Tracking
Every AI pick is stored as a "shadow bet" before any filtering (confidence threshold, calibration, edge floor, ROI gating). This tracks pick accuracy independent of the betting gates.

**How it works:**
- `benny_trader.py` `_store_shadow_bet()` writes to DynamoDB with `sk=SHADOW#...`, `status=shadow`
- `outcome_collector.py` `_settle_shadow_bets()` settles them alongside real bets → `shadow_won` / `shadow_lost`
- No bankroll impact — purely for data collection

**Key question it answers:** "Is the AI good at picking sides but bad at calibrating confidence, or is it bad at both?"

**Plan:** Collect 1-2 weeks of data, then analyze shadow bet accuracy vs real bet accuracy. If shadow accuracy is significantly higher, the gates are too aggressive. If it's the same, the AI's picks need work.

### Deprecated: Coaching Memo
The coaching agent (`coaching_agent.py`) and its Lambda (`coaching-memo-stack.ts`) are deprecated. The Lambda instantiation was removed from `infrastructure.ts`. The coaching agent code still exists but nothing imports it. The coaching memo is still generated for email reports via `coaching_memo_generator.py` but is no longer injected into AI prompts.

### Deprecated: Confidence Scorer
`confidence_scorer.py` exists but is no longer imported. It was an experiment to replace AI confidence with programmatic signals (Elo, form, injuries, market alignment). Removed because it second-guessed the AI's picks with a simpler model — the AI might see nuances the scorer can't.

---

## Performance Optimization

### ~~Accuracy & ROI Improvements (V1 + V3)~~ ✅ DONE (March 2026)
**Priority**: High
**Effort**: Medium
**Impact**: High

**Implemented across V1 and V3:**
- **Sport-specific edge floors**: NBA/NFL require 10% edge vs market, EPL/MLB/NHL 8%, NCAAB/MLS 6%. Prevents betting on thin margins in efficient markets.
- **Confidence calibration in bet decisions**: Maps raw AI confidence to actual win rate from settled bets. Rejects bets where calibrated confidence < market implied probability.
- **Calibration table in prompts**: Shows AI its own track record ("80% → 48% (overconfident)") so it self-corrects.
- **Raw self-correction signals**: Recent wins/losses per sport, factor track record, sport/market win rates — all injected directly into prompts (replaced coaching memo).
- **Shadow bet tracking**: Every AI pick stored before filtering for pick accuracy analysis.
- **Lowered confidence threshold**: 0.70 → 0.55 since AI now outputs honest (lower) confidence after seeing calibration data.

**V3-only:**
- **ROI auto-gating**: Reads last 60 days of settled bets by sport|market. Blocks at -15% ROI (15+ bets), probation at -5% (requires extra 5% edge). Self-learning — no hardcoding.

**Code Locations**: `backend/benny/models/base.py`, `backend/benny/models/v1.py`, `backend/benny/models/v3.py`, `backend/benny_trader.py`, `backend/outcome_collector.py`

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
