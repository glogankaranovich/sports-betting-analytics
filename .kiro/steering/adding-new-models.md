# Adding New Models to the System

This guide explains how to add a new betting analysis model to the platform.

## Overview

The platform has two types of models:
1. **System Models** - ML models that generate predictions (tracked in analytics, scheduled for analysis)
2. **User Model Data Sources** - Raw data inputs for user-created models (used in backtest engine)

This guide covers adding **System Models**.

## Required Changes

When adding a new system model, you must update **4 locations**:

### 1. Backend Constants (`backend/constants.py`)

Add your model to two places:

```python
SYSTEM_MODELS = os.environ.get(
    "SYSTEM_MODELS",
    "consensus,value,momentum,...,YOUR_MODEL_NAME",  # Add here
).split(",")

MODEL_NAMES = {
    "consensus": "Consensus Model",
    # ...
    "your_model_name": "Your Model Display Name",  # Add here
}
```

**Purpose:** Makes the model visible in analytics API and model comparison features.

### 2. Infrastructure Constants (`infrastructure/lib/utils/constants.ts`)

```typescript
export const PLATFORM_CONSTANTS = {
  SUPPORTED_SPORTS: 'basketball_nba,americanfootball_nfl,...',
  SYSTEM_MODELS: 'consensus,value,momentum,...,your_model_name',  // Add here
  SUPPORTED_BOOKMAKERS: 'draftkings,fanduel,betmgm,caesars',
  TIME_RANGES: '30,90,180,365',
};
```

**Purpose:** Schedules your model to run every 4 hours for each sport and bet type (games/props).

### 3. Model Factory (`backend/ml/models.py`)

```python
class ModelFactory:
    _models = {
        "consensus": ConsensusModel,
        "value": ValueModel,
        # ...
        "your_model_name": YourModelClass,  # Add here
    }
```

**Purpose:** Allows the analysis generator to instantiate your model.

### 4. Analytics API (`backend/api/analytics.py`)

The analytics API automatically uses `SYSTEM_MODELS` constant, so no changes needed here. Just verify it imports the constant:

```python
from constants import SYSTEM_MODELS
```

**Purpose:** Ensures your model appears in detailed analytics and model weights.

## Model Implementation Requirements

Your model class must:

1. **Inherit from `BaseAnalysisModel`**
   ```python
   class YourModel(BaseAnalysisModel):
       pass
   ```

2. **Implement required methods:**
   ```python
   def analyze_game_odds(self, game_id: str, odds_items: List[Dict], game_info: Dict) -> AnalysisResult:
       """Analyze game betting odds. Return None if model doesn't support games."""
       pass
   
   def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
       """Analyze prop betting odds. Return None if model doesn't support props."""
       pass
   ```

3. **Return `AnalysisResult` objects:**
   ```python
   return AnalysisResult(
       game_id=game_id,
       model="your_model_name",
       analysis_type="game",  # or "prop"
       sport=sport,
       home_team=home_team,
       away_team=away_team,
       commence_time=game_date,
       prediction=pick,  # Team name or player name
       confidence=0.75,  # 0.5-0.9 range
       reasoning="Why this pick was made",
       recommended_odds=-110
   )
   ```

## Deployment Process

After making the changes:

1. **Run tests:**
   ```bash
   cd backend
   python3 -m pytest tests/unit/test_your_model.py -v
   ```

2. **Deploy infrastructure:**
   ```bash
   cd infrastructure
   make deploy-stack STACK=Dev-AnalysisSchedule
   make deploy-stack STACK=Dev-BetCollectorApi  # For analytics API
   ```
   This updates the EventBridge schedules and analytics API to include your model.

3. **Verify in CloudWatch:**
   - Check EventBridge rules include your model
   - Monitor Lambda invocations after deployment

4. **Check frontend:**
   - Your model should appear in model comparison dropdowns
   - Your model should appear in detailed analytics
   - Analyses should appear in the bets table after first scheduled run

## Example: Adding the Fundamentals Model

Here's what was changed to add the `fundamentals` model:

**backend/constants.py:**
```python
SYSTEM_MODELS = "...,fundamentals"
MODEL_NAMES = {"fundamentals": "Fundamentals Model"}
```

**infrastructure/lib/utils/constants.ts:**
```typescript
SYSTEM_MODELS: '...,fundamentals'
```

**backend/ml/models.py:**
```python
class ModelFactory:
    _models = {
        # ...
        "fundamentals": FundamentalsModel,
    }
```

## Common Issues

### Model not appearing in frontend analytics
- Check that model name is in `SYSTEM_MODELS` constant (backend and infrastructure)
- Verify `BetCollectorApi` stack was deployed
- Check that `backend/api/analytics.py` imports `SYSTEM_MODELS`

### Model not appearing in bets table
- Check that model name is in all 3 constants
- Verify infrastructure was deployed
- Check CloudWatch logs for analysis generator errors

### Model not being scheduled
- Ensure infrastructure constants were updated
- Redeploy `AnalysisSchedule` stack
- Check EventBridge rules in AWS console

### Model errors during analysis
- Check CloudWatch logs for the analysis generator Lambda
- Verify model returns `None` for unsupported bet types
- Ensure `AnalysisResult` has all required fields

## Notes

- Model names must be lowercase with underscores (e.g., `player_stats`, not `PlayerStats`)
- Models run every 4 hours, staggered by 2 minutes to avoid throttling
- Each model runs separately for games and props
- Models that don't support props should return `None` from `analyze_prop_odds()`
- The `benny` model is excluded from scheduling (it's a special case)
