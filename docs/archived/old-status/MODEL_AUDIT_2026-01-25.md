# Model Audit Report - January 25, 2026

## Executive Summary
- **Total Models**: 8 (Consensus, Value, Momentum, Contrarian, Hot/Cold, Rest/Schedule, Matchup, Injury-Aware)
- **Critical Issues**: 4
- **Medium Issues**: 3
- **Minor Issues**: 2

---

## Critical Issues (Must Fix Before Public Launch)

### 1. Injury-Aware Model - Incomplete Team Mapping
**Location**: `backend/ml/models.py:1450-1456`
**Issue**: Only 3 NBA teams mapped (Atlanta, Boston, Brooklyn). Missing 27 NBA teams + all NFL/MLB/NHL teams.
**Impact**: Model returns no injury data for 90% of teams, making it ineffective.
**Fix Required**: Complete team ID mapping for all leagues.

### 2. Injury-Aware Model - Player Injury Lookup Not Implemented
**Location**: `backend/ml/models.py:1424-1427`
**Issue**: `_get_player_injury_status()` always returns `None`.
**Impact**: Prop analysis never detects injured players. "AVOID" warnings never trigger.
**Fix Required**: Implement player name lookup in injury data.

### 3. Matchup Model - Props Not Supported
**Location**: `backend/ml/models.py:1189-1191`
**Issue**: `analyze_prop_odds()` returns `None` with TODO comment.
**Impact**: Matchup model only works for games, not props.
**Fix Required**: Either implement prop analysis or remove from prop schedules.

### 4. Analysis vs Insight Duplication
**Location**: `backend/analysis_generator.py` and `backend/insight_generator.py`
**Issue**: 
- Analysis Generator: Runs models, stores raw analysis
- Insight Generator: Queries analyses, filters by confidence, stores insights
- Both run on same schedule for same models
- Insights are just filtered copies of analyses
**Impact**: 
- 2x Lambda invocations (2x cost)
- 2x DynamoDB writes (2x cost)
- Duplicate data storage
- Confusing architecture
**Recommendation**: **Merge into single generator** that stores analysis and creates insight if confidence > threshold.

---

## Medium Issues (Should Fix Soon)

### 5. Momentum Model - Simplified Prop Analysis
**Location**: `backend/ml/models.py:389`
**Issue**: Comment says "simplified version" - analyzes single prop_item without historical line movement.
**Impact**: Momentum model for props is less effective than intended.
**Fix**: Collect historical prop odds to track line movement over time.

### 6. Injury-Aware Model - Simplified Impact Calculation
**Location**: `backend/ml/models.py:1429-1436`
**Issue**: Just counts injuries (0.15 per injury), doesn't weight by player importance.
**Impact**: Bench player injury weighted same as star player injury.
**Fix**: Add player importance weighting (starter vs bench, usage rate, etc.).

### 7. No Integration Tests for New Models
**Issue**: Hot/Cold, Matchup, Injury-Aware models only have unit tests.
**Impact**: Haven't verified they work with real DynamoDB data.
**Fix**: Add integration tests before production.

---

## Minor Issues (Nice to Have)

### 8. Error Handling Inconsistency
**Issue**: Some models return `None` on error, others return low-confidence predictions.
**Impact**: Inconsistent behavior across models.
**Fix**: Standardize error handling approach.

### 9. No Model Performance Tracking
**Issue**: No tracking of which models perform best over time.
**Impact**: Can't optimize model selection or weighting.
**Fix**: Add model performance metrics to monitoring.

---

## Analysis vs Insight - Detailed Breakdown

### Current Architecture:
```
EventBridge (7:00 PM) → Analysis Generator → Stores ANALYSIS records
EventBridge (7:00 PM) → Insight Generator → Queries ANALYSIS → Stores INSIGHT records
```

### What They Do:
- **Analysis Generator**: Runs model, stores prediction with confidence
- **Insight Generator**: Filters analyses by confidence ≥ 0.6, copies to INSIGHT table

### Problems:
1. **Redundant**: Insights are just filtered analyses
2. **Wasteful**: 2x Lambda invocations, 2x DynamoDB operations
3. **Confusing**: Two similar concepts (analysis vs insight)
4. **Delayed**: Insights created after analyses (timing gap)

### Recommended Solution:
**Merge into single "Analysis Generator":**
```python
def lambda_handler(event, context):
    # Run model
    analysis = model.analyze_game_odds(...)
    
    # Store analysis
    store_analysis(analysis)
    
    # If high confidence, also store as insight
    if analysis.confidence >= 0.6:
        store_insight(analysis)
    
    return result
```

**Benefits:**
- 50% fewer Lambda invocations
- 50% fewer DynamoDB writes
- Simpler architecture
- Atomic operation (analysis + insight together)

---

## Recommendations

### Before Public Launch (Priority Order):

1. **Fix Critical Issues 1-3** (1-2 days)
   - Complete team ID mappings
   - Implement player injury lookup
   - Fix or remove matchup prop analysis

2. **Merge Analysis/Insight Generators** (1 day)
   - Simplify architecture
   - Reduce costs
   - Easier to maintain

3. **Add Integration Tests** (1 day)
   - Test with real DynamoDB data
   - Verify all models work end-to-end

4. **Monitor in Dev for 1 Week**
   - Verify models run successfully
   - Check prediction quality
   - Monitor for errors

5. **Fix Medium Issues** (2-3 days)
   - Player importance weighting
   - Historical prop odds collection

**Total Timeline: 1-2 weeks minimum**

---

## Public Launch Readiness Checklist

- [ ] All critical issues fixed
- [ ] Integration tests passing
- [ ] 1 week of successful dev monitoring
- [ ] Error alerting configured
- [ ] User documentation written
- [ ] Model limitations documented
- [ ] Beta testing with small user group
- [ ] Performance metrics baseline established

**Current Status: Not Ready for Public Launch**
