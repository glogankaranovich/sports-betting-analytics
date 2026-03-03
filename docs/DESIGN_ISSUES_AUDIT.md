# Design Issues & Technical Debt Audit

**Date:** March 3, 2026  
**Status:** Identified

## Overview

Comprehensive audit of design issues, technical debt, and architectural improvements needed across the codebase.

---

## Issue #1: Market Key Ambiguity ✅ DOCUMENTED

**Status:** Design document created (DESIGN_MARKET_KEY_FIX.md)

**Problem:** Game predictions return team name without specifying market type (h2h/spreads/totals)

**Solution:** Add `market_key` field to all game predictions

**Priority:** Medium  
**Effort:** ~3 hours  
**Document:** `docs/DESIGN_MARKET_KEY_FIX.md`

---

## Issue #2: Bare Exception Handlers

**Problem:** Many files use bare `except:` clauses that catch all exceptions, making debugging difficult

**Examples:**
```python
# backend/analysis_generator.py
try:
    # code
except:
    pass  # Don't fail on metric emission

# backend/benny_trader.py
try:
    # code
except:
    logger.error("Error")
```

**Impact:**
- Hides bugs and unexpected errors
- Makes debugging harder
- Can catch KeyboardInterrupt and SystemExit

**Solution:** Replace with specific exception types
```python
# Better
try:
    # code
except (ValueError, KeyError) as e:
    logger.error(f"Expected error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

**Files Affected:** 26 files with 46+ bare exception handlers

**Priority:** Low (works but not best practice)  
**Effort:** 2-3 hours to fix all

---

## Issue #3: AI Agent Conversation History

**Problem:** AI Agent has TODO for loading conversation history from DynamoDB

**Location:** `backend/ai_agent.py:697`

```python
# TODO: Load conversation history from DynamoDB if conversation_id provided
```

**Impact:** 
- Multi-turn conversations not persisted
- Users can't continue previous conversations
- Limits AI agent usefulness

**Solution:** Implement conversation storage/retrieval in DynamoDB

**Priority:** Medium (feature gap)  
**Effort:** 4-6 hours

---

## Issue #4: Inconsistent Error Return Values

**Problem:** Some functions return `None` on error, others raise exceptions, creating inconsistent error handling

**Examples:**
```python
# Some return None
def analyze_game_odds(...):
    try:
        # logic
    except:
        return None

# Others raise
def get_team_stats(...):
    if not team:
        raise ValueError("Team required")
```

**Impact:**
- Callers must handle both patterns
- Easy to miss None checks
- Inconsistent API

**Solution:** Standardize on one approach (prefer exceptions for errors, None for "no data")

**Priority:** Low (works but inconsistent)  
**Effort:** 4-6 hours

---

## Issue #5: Model Performance Tracking Overhead

**Problem:** Every model initializes performance tracker and inefficiency tracker, even when not used

**Location:** `ml/models/base.py`

```python
def __init__(self):
    self.performance_tracker = None
    self.inefficiency_tracker = None
    table_name = os.getenv("DYNAMODB_TABLE")
    if table_name:
        from model_performance import ModelPerformanceTracker
        from market_inefficiency_tracker import MarketInefficiencyTracker
        self.performance_tracker = ModelPerformanceTracker(table_name)
        self.inefficiency_tracker = MarketInefficiencyTracker(table_name)
```

**Impact:**
- Unnecessary imports and object creation
- Slower model initialization
- Not all models use these trackers

**Solution:** Lazy initialization - only create when first accessed

**Priority:** Low (performance optimization)  
**Effort:** 1-2 hours

---

## Issue #6: DynamoDB Table Name Duplication

**Problem:** Every model/collector duplicates DynamoDB table initialization logic

**Example:**
```python
# Repeated in ~20 files
if not self.table:
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
    self.table = dynamodb.Table(table_name)
```

**Impact:**
- Code duplication (~20 files)
- Harder to change table initialization logic
- Inconsistent default table names

**Solution:** Create shared `get_dynamodb_table()` utility function

**Priority:** Low (technical debt)  
**Effort:** 2-3 hours

---

## Issue #7: Hard-Coded Region

**Problem:** AWS region "us-east-1" is hard-coded throughout the codebase

**Examples:**
```python
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
```

**Impact:**
- Can't easily deploy to other regions
- Not following AWS best practices (use default region)

**Solution:** Remove region parameter (use AWS_REGION env var or default)

**Priority:** Low (works for current deployment)  
**Effort:** 1 hour

---

## Issue #8: Missing Type Hints

**Problem:** Many functions lack type hints, making code harder to understand and maintain

**Example:**
```python
# Current
def analyze_game_odds(self, game_id, odds_items, game_info):
    ...

# Better
def analyze_game_odds(
    self, 
    game_id: str, 
    odds_items: List[Dict], 
    game_info: Dict
) -> Optional[AnalysisResult]:
    ...
```

**Impact:**
- Harder to understand function contracts
- No IDE autocomplete support
- More runtime errors

**Solution:** Add type hints to all public functions

**Priority:** Low (quality of life)  
**Effort:** 8-10 hours (large codebase)

---

## Issue #9: Test Coverage Gaps

**Problem:** Many modules lack unit tests

**Known gaps:**
- Collectors (odds, team stats, player stats, schedule, injury, weather, ESPN, outcome)
- APIs (analytics, games, odds, user data, custom data, user models, AI agent)
- Data processing (DAO, backfill, season manager, PER calculator, ELO calculator)
- Model execution (user model executor, queue loader, weight adjuster, dynamic weighting)
- Benny Trader system

**Impact:**
- Bugs harder to catch
- Refactoring is risky
- No regression detection

**Solution:** Systematic test coverage plan (Task 5)

**Priority:** High (quality/reliability)  
**Effort:** 20-40 hours

---

## Issue #10: Prop Support Limited to NBA/NFL

**Problem:** Player prop predictions only work for NBA and NFL due to data availability

**Impact:**
- Can't provide prop predictions for MLB, NHL, soccer, college sports
- Limits platform value for those sports

**Solution:** 
- Option A: Expand data collection to other sports
- Option B: Document limitation clearly
- Option C: Add basic prop support using available data

**Priority:** Medium (feature gap)  
**Effort:** Varies by option (2-20 hours)

---

## Issue #11: Inverse Prediction Logic Complexity

**Problem:** Inverse predictions are calculated in `analysis_generator.py` with complex logic

**Impact:**
- Hard to understand and maintain
- Duplicates confidence/ROI calculation logic
- Tightly coupled to analysis generation

**Solution:** Move inverse logic to AnalysisResult class method

**Priority:** Low (technical debt)  
**Effort:** 2-3 hours

---

## Issue #12: Model Factory Uses Lazy Imports

**Problem:** ModelFactory uses if/elif chain with lazy imports instead of registry pattern

**Current:**
```python
def create_model(cls, model_name: str):
    if model_name == "fundamentals":
        from ml.models.fundamentals import FundamentalsModel
        return FundamentalsModel()
    if model_name == "matchup":
        from ml.models.matchup import MatchupModel
        return MatchupModel()
    # ... 10 more if statements
```

**Impact:**
- Verbose and repetitive
- Hard to add new models
- No clear model registry

**Solution:** Use registry pattern
```python
_MODEL_REGISTRY = {
    "fundamentals": "ml.models.fundamentals.FundamentalsModel",
    "matchup": "ml.models.matchup.MatchupModel",
    # ...
}

def create_model(cls, model_name: str):
    if model_name not in cls._MODEL_REGISTRY:
        raise ValueError(f"Unknown model: {model_name}")
    
    module_path, class_name = cls._MODEL_REGISTRY[model_name].rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()
```

**Priority:** Low (works fine, just not elegant)  
**Effort:** 1 hour

---

## Summary

### Priority Breakdown

**High Priority (1 issue):**
- Issue #9: Test coverage gaps

**Medium Priority (3 issues):**
- Issue #1: Market key ambiguity (documented)
- Issue #3: AI agent conversation history
- Issue #10: Prop support limited to NBA/NFL

**Low Priority (8 issues):**
- Issue #2: Bare exception handlers
- Issue #4: Inconsistent error returns
- Issue #5: Performance tracking overhead
- Issue #6: DynamoDB table duplication
- Issue #7: Hard-coded region
- Issue #8: Missing type hints
- Issue #11: Inverse prediction complexity
- Issue #12: Model factory pattern

### Recommended Action Plan

1. **Immediate:** Continue with Task 5 (test coverage plan) - addresses Issue #9
2. **Short-term:** Implement market_key fix (Issue #1) - design already complete
3. **Medium-term:** Add AI conversation history (Issue #3)
4. **Long-term:** Address low-priority technical debt as time permits

### Total Effort Estimate

- High priority: 20-40 hours
- Medium priority: 10-15 hours  
- Low priority: 20-30 hours
- **Total: 50-85 hours**

---

## Notes

- Most issues are technical debt, not critical bugs
- System is functional and stable
- Prioritize test coverage and feature gaps over code style improvements
- Many low-priority issues can be addressed incrementally
