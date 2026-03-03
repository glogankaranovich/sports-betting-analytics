# Model Audit and Refactoring Plan

Systematic audit of all 12 system models, refactor into individual classes, and ensure full test coverage.

## Phase 1: Audit Current Implementation

For each model, verify:
1. Logic correctness (no inverted logic, wrong operators)
2. Data access (correct field names, proper defaults)
3. Edge case handling (missing data, ties, extreme values)
4. Prediction format consistency

## Phase 2: Refactor to Individual Classes

Extract each model from `models.py` monolith into `backend/ml/models/{model_name}.py`:

**Target Structure**:
```
backend/ml/models/
├── __init__.py
├── base.py                    # BaseModel abstract class
├── fundamentals.py
├── matchup.py
├── momentum.py
├── value.py
├── player_stats.py           # Already exists
├── hot_cold.py
├── rest_schedule.py
├── injury_aware.py
├── contrarian.py
├── news.py
├── ensemble.py
└── consensus.py
```

**Each model class should**:
- Inherit from `BaseModel`
- Implement `predict()` method
- Have clear data dependencies
- Include docstrings explaining strategy
- Be independently testable

## Phase 3: Unit Tests

Create comprehensive tests for each model:
```
backend/tests/models/
├── test_fundamentals.py
├── test_matchup.py
├── test_momentum.py
├── test_value.py
├── test_player_stats.py
├── test_hot_cold.py
├── test_rest_schedule.py
├── test_injury_aware.py
├── test_contrarian.py
├── test_news.py
├── test_ensemble.py
└── test_consensus.py
```

## Models to Audit & Refactor

### 1. Fundamentals Model (Priority: HIGH)
**Strategy**: Core team statistics (offensive/defensive ratings)
**Current Issues**: Unknown
**Refactor**: Extract to `fundamentals.py`

### 2. Matchup Model (Priority: HIGH - RECENTLY FIXED)
**Strategy**: Head-to-head style matchups
**Current Issues**: Was using non-existent stat fields (FIXED)
**Refactor**: Extract to `matchup.py`, add regression tests

### 3. Player Stats Model (Priority: HIGH)
**Strategy**: Individual player performance analysis
**Current Issues**: Unknown
**Refactor**: Already in `player_stats.py` ✓

### 4. Momentum Model (Priority: HIGH)
**Strategy**: Recent performance trends (last N games)
**Current Issues**: Unknown
**Refactor**: Extract to `momentum.py`

### 5. Value Model (Priority: HIGH)
**Strategy**: Find value bets where odds are favorable
**Current Issues**: Unknown
**Refactor**: Extract to `value.py`

### 6. Hot/Cold Model (Priority: MEDIUM)
**Strategy**: Win/loss streaks
**Current Issues**: Unknown
**Refactor**: Extract to `hot_cold.py`

### 7. Rest/Schedule Model (Priority: MEDIUM)
**Strategy**: Days of rest, back-to-back games
**Current Issues**: Unknown
**Refactor**: Extract to `rest_schedule.py`

### 8. Injury-Aware Model (Priority: HIGH)
**Strategy**: Factor in player injuries
**Current Issues**: Unknown
**Refactor**: Extract to `injury_aware.py`

### 9. Contrarian Model (Priority: MEDIUM)
**Strategy**: Bet against public consensus
**Current Issues**: Unknown
**Refactor**: Extract to `contrarian.py`

### 10. News Model (Priority: LOW)
**Strategy**: Sentiment from news articles
**Current Issues**: Unknown
**Refactor**: Extract to `news.py`

### 11. Ensemble Model (Priority: HIGH)
**Strategy**: Weighted combination of models
**Current Issues**: Depends on all other models
**Refactor**: Extract to `ensemble.py`

### 12. Consensus Model (Priority: HIGH)
**Strategy**: Aggregate predictions from other models
**Current Issues**: Depends on all other models
**Refactor**: Extract to `consensus.py`

## Execution Order

### Week 1: Foundation & High Priority
1. Create `BaseModel` abstract class
2. Audit & refactor **Fundamentals**
3. Audit & refactor **Matchup** (add tests for recent fix)
4. Audit & refactor **Player Stats** (already separate, just audit)

### Week 2: Core Models
5. Audit & refactor **Momentum**
6. Audit & refactor **Value**
7. Audit & refactor **Hot/Cold**
8. Audit & refactor **Rest/Schedule**

### Week 3: Complex Models
9. Audit & refactor **Injury-Aware**
10. Audit & refactor **Contrarian**
11. Audit & refactor **News**

### Week 4: Meta Models
12. Audit & refactor **Ensemble**
13. Audit & refactor **Consensus**

## Success Criteria

For each model:
- [ ] Extracted to individual file
- [ ] Inherits from BaseModel
- [ ] Has comprehensive unit tests (>80% coverage)
- [ ] Passes all tests
- [ ] Documented with strategy explanation
- [ ] No bugs found in logic
- [ ] Uses correct data fields
- [ ] Handles edge cases properly

## Benefits

1. **Maintainability**: Easier to find and fix bugs
2. **Testability**: Each model can be tested in isolation
3. **Clarity**: Clear separation of concerns
4. **Extensibility**: Easy to add new models
5. **Debugging**: Easier to trace issues to specific models
6. **Performance**: Can optimize individual models
