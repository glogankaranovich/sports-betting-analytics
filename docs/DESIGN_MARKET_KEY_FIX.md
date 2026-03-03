# Design Fix: Market Key Support for Game Predictions

**Issue ID:** Design Issue #1  
**Created:** March 3, 2026  
**Status:** Proposed

## Problem Statement

Game predictions currently return only a team name (e.g., "Boston Celtics") without specifying which betting market the prediction applies to. This creates ambiguity:

```python
# Current prediction format
result = AnalysisResult(
    prediction="Boston Celtics",  # Which market? Moneyline? Spread? Total?
    market_key=None  # Only used for props
)
```

**Issues:**
1. **Ambiguous predictions**: Users don't know if the model is predicting moneyline, spread, or total
2. **Inconsistent with props**: Props use `market_key` (e.g., "player_points"), but games don't
3. **Limited model flexibility**: Models can't specify which market they're analyzing
4. **ROI calculation issues**: Different markets have different odds and risk profiles

## Current State

### AnalysisResult Structure
```python
@dataclass
class AnalysisResult:
    game_id: str
    model: str
    analysis_type: str  # "game" or "prop"
    sport: str
    prediction: str  # Team name for games, "Over X" or "Under X" for props
    confidence: float
    reasoning: str
    market_key: str = None  # Currently only used for props
```

### How Models Currently Work

**Game Predictions:**
- Fundamentals: Predicts team name (assumes moneyline/spread)
- Matchup: Predicts team name based on H2H
- Momentum: Predicts team name based on recent form
- Value: Analyzes spreads but predicts team name
- Contrarian: Analyzes spreads but predicts team name
- HotCold: Predicts team name based on streaks
- RestSchedule: Predicts team name based on fatigue
- InjuryAware: Predicts team name based on injuries
- News: Predicts team name based on sentiment
- Consensus: Averages spreads but predicts team name
- Ensemble: Combines predictions (team names)

**Prop Predictions:**
- PlayerStats: Returns "Over X" or "Under X" with `market_key="player_points"`
- HotCold: Returns "Over X" or "Under X" with `market_key` set
- InjuryAware: Returns "Over X" or "Under X" with `market_key` set
- Contrarian: Returns "Over X" or "Under X" with `market_key` set

## Proposed Solutions

### Option A: Keep Team Name Only (Status Quo)
**Approach:** Document that game predictions assume spread/moneyline equivalence

**Pros:**
- No code changes required
- Simple prediction format
- Works for most use cases

**Cons:**
- Ambiguity remains
- Can't distinguish between markets
- Limits future enhancements

**Recommendation:** ❌ Not recommended - doesn't solve the problem

---

### Option B: Add Market Key to All Game Predictions ⭐ RECOMMENDED
**Approach:** Extend `market_key` to game predictions, specify which market each model analyzes

**Changes Required:**

1. **Update AnalysisResult usage in models:**
```python
# Before
return AnalysisResult(
    prediction="Boston Celtics",
    market_key=None
)

# After
return AnalysisResult(
    prediction="Boston Celtics",
    market_key="spreads"  # or "h2h" or "totals"
)
```

2. **Model-specific market keys:**
- **Fundamentals**: `market_key="spreads"` (analyzes team strength)
- **Matchup**: `market_key="spreads"` (H2H history)
- **Momentum**: `market_key="spreads"` (recent form)
- **Value**: `market_key="spreads"` (already analyzes spreads)
- **Contrarian**: `market_key="spreads"` (already analyzes spreads)
- **HotCold**: `market_key="spreads"` (streak-based)
- **RestSchedule**: `market_key="spreads"` (fatigue impact)
- **InjuryAware**: `market_key="spreads"` (injury impact)
- **News**: `market_key="h2h"` (sentiment-based, no spread analysis)
- **Consensus**: `market_key="spreads"` (averages spreads)
- **Ensemble**: `market_key="spreads"` (combines spread predictions)

3. **Update DynamoDB schema:**
```python
# Already has market_key field, just needs to be populated for games
item = {
    "pk": f"ANALYSIS#{sport}#{game_id}#{bookmaker}",
    "sk": f"{model}#game#LATEST",
    "market_key": "spreads",  # Now populated for games
    "prediction": "Boston Celtics",
    ...
}
```

4. **Update frontend display:**
```typescript
// Show market type with prediction
{analysis.analysis_type === 'game' && (
  <span className="market-badge">{analysis.market_key}</span>
)}
<span className="prediction">{analysis.prediction}</span>
```

**Pros:**
- ✅ Clear which market each prediction applies to
- ✅ Consistent with prop predictions
- ✅ Enables future enhancements (multiple markets per model)
- ✅ Minimal code changes (just add market_key parameter)
- ✅ Backward compatible (market_key already exists)

**Cons:**
- Requires updating all 11 game models
- Need to update frontend to display market type
- Need to update API documentation

**Recommendation:** ✅ **RECOMMENDED** - Best balance of clarity and simplicity

---

### Option C: Return Multiple Predictions Per Market
**Approach:** Each model returns separate predictions for h2h, spreads, and totals

**Changes Required:**

1. **Models return list of predictions:**
```python
def analyze_game_odds(self, game_id, odds_items, game_info):
    # Analyze all markets
    return [
        AnalysisResult(prediction="Boston Celtics", market_key="h2h", ...),
        AnalysisResult(prediction="Boston Celtics", market_key="spreads", ...),
        AnalysisResult(prediction="Over 215.5", market_key="totals", ...)
    ]
```

2. **Update storage to handle multiple predictions per model:**
```python
# Store 3 predictions per model per game
pk = f"ANALYSIS#{sport}#{game_id}#{bookmaker}"
sk = f"{model}#game#{market_key}#LATEST"
```

3. **Update frontend to show all markets:**
```typescript
// Group predictions by market
const byMarket = groupBy(analyses, 'market_key')
```

**Pros:**
- Most comprehensive solution
- Covers all betting markets
- Maximum flexibility

**Cons:**
- ❌ Significant code changes required
- ❌ 3x storage and compute costs
- ❌ Complex frontend changes
- ❌ Most models don't analyze totals
- ❌ Overkill for current needs

**Recommendation:** ❌ Not recommended - too complex for the benefit

---

## Recommended Implementation: Option B

### Phase 1: Update Models (1-2 hours)

Update all 11 game models to specify `market_key`:

```python
# Example: fundamentals.py
return AnalysisResult(
    game_id=game_id,
    model="fundamentals",
    analysis_type="game",
    sport=sport,
    prediction=pick,
    market_key="spreads",  # ADD THIS
    confidence=confidence,
    reasoning=reasoning,
    recommended_odds=-110
)
```

**Files to update:**
- `ml/models/fundamentals.py`
- `ml/models/matchup.py`
- `ml/models/momentum.py`
- `ml/models/value.py`
- `ml/models/hot_cold.py`
- `ml/models/rest_schedule.py`
- `ml/models/injury_aware.py`
- `ml/models/contrarian.py`
- `ml/models/news.py`
- `ml/models/consensus.py`
- `ml/models/ensemble.py`

### Phase 2: Update Tests (30 min)

Update test assertions to include market_key:

```python
# Before
assert result.prediction == "Boston Celtics"

# After
assert result.prediction == "Boston Celtics"
assert result.market_key == "spreads"
```

### Phase 3: Update Frontend (30 min)

Add market badge to game predictions:

```typescript
<div className="prediction-card">
  {analysis.market_key && (
    <span className="market-badge">{analysis.market_key}</span>
  )}
  <span className="prediction">{analysis.prediction}</span>
</div>
```

### Phase 4: Update Documentation (15 min)

Document market_key usage in:
- API documentation
- Model architecture docs
- Frontend component docs

## Testing Plan

1. **Unit tests**: Verify all models return market_key
2. **Integration tests**: Verify DynamoDB storage includes market_key
3. **Frontend tests**: Verify market badge displays correctly
4. **Manual testing**: Review predictions in UI

## Rollout Plan

1. Deploy backend changes (models + tests)
2. Verify DynamoDB items have market_key populated
3. Deploy frontend changes
4. Monitor for issues
5. Update documentation

## Timeline

- **Phase 1 (Models)**: 1-2 hours
- **Phase 2 (Tests)**: 30 minutes
- **Phase 3 (Frontend)**: 30 minutes
- **Phase 4 (Docs)**: 15 minutes
- **Total**: ~3 hours

## Success Criteria

- ✅ All game predictions include market_key
- ✅ All 99 model tests pass
- ✅ Frontend displays market type
- ✅ No regressions in prediction accuracy
- ✅ Documentation updated

## Future Enhancements

After implementing Option B, we could:
1. Add totals predictions for models that analyze scoring
2. Add h2h-specific models for moneyline bets
3. Allow users to filter predictions by market type
4. Track model performance by market type

## Decision

**Recommended:** Option B - Add market_key to all game predictions

**Rationale:**
- Solves the ambiguity problem
- Minimal code changes
- Consistent with existing prop predictions
- Enables future enhancements
- Clear implementation path

**Next Steps:**
1. Get approval for Option B
2. Create implementation branch
3. Update models (Phase 1)
4. Update tests (Phase 2)
5. Deploy and verify
