# Old Tests Audit - tests/unit/ vs tests/models/

## Summary

During model extraction, we created new comprehensive tests in `tests/models/` for each extracted model. However, older tests exist in `tests/unit/` that may have additional coverage or different test scenarios.

## Duplicate Test Files Found

| Model | Old Tests (tests/unit/) | New Tests (tests/models/) | Status |
|-------|------------------------|---------------------------|--------|
| **Fundamentals** | test_fundamentals_model.py (243 lines, 8 tests) | test_fundamentals.py (335 lines, 16 tests) | ✅ New tests more comprehensive |
| **Matchup** | test_matchup_model.py (239 lines, 8 tests) | test_matchup.py (257 lines, 13 tests) | ✅ New tests more comprehensive |
| **Contrarian** | test_contrarian_model.py (252 lines, 11 tests) | test_contrarian.py (114 lines, 5 tests) | ⚠️ Old tests have more coverage |
| **RestSchedule** | test_rest_schedule_model.py (6 tests) | test_rest_schedule.py (6 tests) | ✅ Equal coverage, new tests sufficient |
| **HotCold** | test_hot_cold_model.py (13 tests) | test_hot_cold.py (5 tests) | ⚠️ Old tests have more coverage |
| **InjuryAware** | test_injury_aware_model.py (10 tests) | test_injury_aware.py (7 tests) | ⚠️ Old tests have more coverage |

## Old Test Issues

All old tests in `tests/unit/` are currently **FAILING** because:
1. They import from `ml.models` directly (e.g., `from ml.models import FundamentalsModel`)
2. Models were moved to `ml.models.fundamentals`, `ml.models.matchup`, etc.
3. Import paths need updating: `from ml.models.fundamentals import FundamentalsModel`

## Contrarian Model - Detailed Comparison

### Old Tests (11 tests):
- test_strong_line_movement_up
- test_strong_line_movement_down
- test_odds_imbalance_home_sharp
- test_odds_imbalance_away_sharp
- test_fade_favorite_home
- test_fade_favorite_away
- test_prop_odds_imbalance_over
- test_prop_odds_imbalance_under
- test_prop_fade_public
- test_no_spreads_returns_none
- test_invalid_prop_returns_none

### New Tests (5 tests):
- test_analyze_game_strong_line_movement
- test_analyze_game_odds_imbalance
- test_analyze_game_fade_favorite
- test_analyze_prop_odds_imbalance_over
- test_analyze_prop_default_under

### Missing Coverage in New Tests:
- ❌ Separate tests for home vs away scenarios
- ❌ test_no_spreads_returns_none
- ❌ test_invalid_prop_returns_none
- ❌ test_prop_fade_public

## HotCold Model - Detailed Comparison

### Old Tests (13 tests):
- test_strong_home_form
- test_strong_away_form
- test_similar_form
- test_prop_hot_player
- test_prop_cold_player
- test_prop_no_data
- test_calculate_form_score_hot
- test_calculate_form_score_cold
- test_calculate_form_score_neutral
- test_get_current_spread
- test_get_current_spread_no_spreads
- test_map_market_to_stat
- test_invalid_prop_returns_none

### New Tests (5 tests):
- test_analyze_game_odds_hot_home_team
- test_analyze_game_odds_hot_away_team
- test_analyze_prop_odds_hot_player
- test_analyze_prop_odds_cold_player
- test_analyze_prop_odds_no_data

### Missing Coverage in New Tests:
- ❌ test_similar_form (neutral case)
- ❌ test_calculate_form_score_* (unit tests for helper method)
- ❌ test_get_current_spread (helper method)
- ❌ test_get_current_spread_no_spreads (edge case)
- ❌ test_map_market_to_stat (helper method)
- ❌ test_invalid_prop_returns_none (edge case)

## InjuryAware Model - Detailed Comparison

### Old Tests (10 tests):
- test_analyze_game_with_home_injuries
- test_analyze_game_with_away_injuries
- test_analyze_game_both_healthy
- test_analyze_prop_player_out
- test_analyze_prop_player_healthy
- test_calculate_injury_impact_no_injuries
- test_calculate_injury_impact_multiple_injuries
- test_calculate_injury_impact_max_cap
- test_get_team_injuries_no_data
- test_get_team_injuries_with_data

### New Tests (7 tests):
- test_analyze_game_away_team_injured
- test_analyze_game_both_healthy
- test_analyze_prop_player_out
- test_analyze_prop_player_questionable
- test_analyze_prop_player_healthy
- test_calculate_injury_impact
- test_calculate_injury_impact_empty

### Missing Coverage in New Tests:
- ❌ test_analyze_game_with_home_injuries (only have away)
- ❌ test_calculate_injury_impact_multiple_injuries (edge case)
- ❌ test_calculate_injury_impact_max_cap (edge case)
- ❌ test_get_team_injuries_* (helper method tests)

## RestSchedule Model - Detailed Comparison

### Old Tests (6 tests):
- test_well_rested_home_team
- test_back_to_back_penalty
- test_home_advantage
- test_no_schedule_data
- test_prop_analysis_well_rested
- test_prop_analysis_fatigued

### New Tests (6 tests):
- test_analyze_game_with_fatigue_calculator
- test_analyze_game_fallback_to_rest_score
- test_analyze_prop_well_rested
- test_analyze_prop_fatigued
- test_get_rest_score_well_rested
- test_get_rest_score_back_to_back

### Coverage Assessment:
✅ Both cover well-rested scenarios
✅ Both cover fatigued/back-to-back scenarios
✅ Both cover prop analysis
✅ New tests cover fatigue calculator integration
✅ New tests cover fallback logic
**Verdict: New tests are equivalent or better**

## Missing Coverage in New Tests:

### Option A: Delete Old Tests (FAST)
**Pros:**
- Clean up duplicate code immediately
- New tests are passing and cover core functionality
- Reduces maintenance burden

**Cons:**
- May lose some edge case coverage (especially Contrarian)
- Old tests may have caught bugs we haven't seen yet

### Option B: Merge Best of Both (THOROUGH)
**Pros:**
- Maximum test coverage
- Preserve valuable edge case tests
- More confidence in model behavior

**Cons:**
- Time-consuming to review and merge
- Need to update all old test imports
- More tests to maintain

### Option C: Fix Imports, Keep Both (SAFE)
**Pros:**
- No test coverage lost
- Can gradually consolidate later
- Safe approach

**Cons:**
- Duplicate test maintenance
- Confusing to have two test locations
- More CI time

## Recommended Action Plan

**UPDATED RECOMMENDATION: Selective Merge**

### Priority 1: DELETE IMMEDIATELY (Safe)
- ✅ **Fundamentals** - New tests more comprehensive (16 vs 8)
- ✅ **Matchup** - New tests more comprehensive (13 vs 8)
- ✅ **RestSchedule** - New tests equivalent/better (6 vs 6)

### Priority 2: MERGE MISSING TESTS (Important)
- ⚠️ **Contrarian** - Port 6 missing test scenarios
- ⚠️ **HotCold** - Port 8 missing test scenarios (helper methods + edge cases)
- ⚠️ **InjuryAware** - Port 4 missing test scenarios (home injuries + edge cases)

### Summary of Missing Tests to Port

**Contrarian (6 missing):**
1. Separate home vs away line movement tests
2. test_no_spreads_returns_none
3. test_invalid_prop_returns_none
4. test_prop_fade_public

**HotCold (8 missing):**
1. test_similar_form (neutral case)
2. test_calculate_form_score_hot
3. test_calculate_form_score_cold
4. test_calculate_form_score_neutral
5. test_get_current_spread
6. test_get_current_spread_no_spreads
7. test_map_market_to_stat
8. test_invalid_prop_returns_none

**InjuryAware (4 missing):**
1. test_analyze_game_with_home_injuries
2. test_calculate_injury_impact_multiple_injuries
3. test_calculate_injury_impact_max_cap
4. test_get_team_injuries_with_data / test_get_team_injuries_no_data

## Recommended Action Plan

1. **Delete Safe Files** (IMMEDIATE)
   ```bash
   rm tests/unit/test_fundamentals_model.py
   rm tests/unit/test_matchup_model.py
   rm tests/unit/test_rest_schedule_model.py
   ```

2. **Port Contrarian Tests** (30 min)
   - Add 6 missing test scenarios to `tests/models/test_contrarian.py`
   - Delete `tests/unit/test_contrarian_model.py`

3. **Port HotCold Tests** (45 min)
   - Add 8 missing test scenarios to `tests/models/test_hot_cold.py`
   - Delete `tests/unit/test_hot_cold_model.py`

4. **Port InjuryAware Tests** (30 min)
   - Add 4 missing test scenarios to `tests/models/test_injury_aware.py`
   - Delete `tests/unit/test_injury_aware_model.py`

5. **Final Verification**
   ```bash
   pytest tests/models/ -v
   ```

## Implementation Steps

```bash
# 1. Compare test coverage for remaining models
pytest tests/unit/test_rest_schedule_model.py --collect-only
pytest tests/models/test_rest_schedule.py --collect-only

pytest tests/unit/test_hot_cold_model.py --collect-only
pytest tests/models/test_hot_cold.py --collect-only

pytest tests/unit/test_injury_aware_model.py --collect-only
pytest tests/models/test_injury_aware.py --collect-only

# 2. Port missing Contrarian tests
# (Manual code review and porting)

# 3. Delete old test files
rm tests/unit/test_fundamentals_model.py
rm tests/unit/test_matchup_model.py
rm tests/unit/test_contrarian_model.py
rm tests/unit/test_rest_schedule_model.py
rm tests/unit/test_hot_cold_model.py
rm tests/unit/test_injury_aware_model.py

# 4. Verify all new tests pass
pytest tests/models/ -v
```

## Timeline Estimate

- **Delete safe files**: 1 minute
- **Port Contrarian tests**: 30 minutes
- **Port HotCold tests**: 45 minutes
- **Port InjuryAware tests**: 30 minutes
- **Total**: ~2 hours

## Next Steps

1. Delete safe files (Fundamentals, Matchup, RestSchedule)
2. Port missing tests for Contrarian, HotCold, InjuryAware
3. Verify all tests pass
4. Update TODO list

---

**AUDIT COMPLETE** ✅

**Summary:**
- 3 models safe to delete immediately
- 3 models need 18 tests ported
- Total effort: ~2 hours
- Result: Comprehensive test coverage with no duplication
