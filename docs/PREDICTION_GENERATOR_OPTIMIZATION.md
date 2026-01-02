# Prediction Generator Optimization Plan

## Current State
The prediction generator runs as a single Lambda function that processes ALL sports, bet types, and models together:
- Single `lambda_handler` in `prediction_generator.py`
- Processes all games via table scan with `FilterExpression=Attr('pk').begins_with('GAME#')`
- Processes all props across all sports in one execution
- Scheduled every 6 hours via single CloudWatch Events rule
- No granular control over what gets processed

## Proposed Optimization
Make prediction generation granular like the odds collector:
- **One sport** per invocation (e.g., `basketball_nba`, `americanfootball_nfl`)
- **One bet type** per invocation (`games` or `props`)
- **One model** per invocation (`consensus`, `value`, `momentum`, etc.)

## Schema Update Required
**Current Schema Issue**: SK doesn't include model type, preventing multiple models per game/prop

**Current:**
- Games: `sk`: `PREDICTION` (static)
- Props: `sk`: `PROP_PREDICTION` (static)

**Updated Schema:**
- Games: `sk`: `PREDICTION#{model}` (e.g., `PREDICTION#consensus`, `PREDICTION#value`)
- Props: `sk`: `PROP_PREDICTION#{model}` (e.g., `PROP_PREDICTION#consensus`)

**Additional Fields Needed:**
- `is_active`: Boolean flag indicating if prediction is for upcoming games (true) vs historical (false)
- `prediction_status`: `ACTIVE` | `HISTORICAL` | `RESOLVED` for lifecycle tracking
- `created_at`: Timestamp when prediction was generated
- `expires_at`: When prediction becomes historical (game commence time)

This allows:
- Multiple models per game/prop
- Querying by specific model
- Model-specific prediction tracking
- **Active vs Historical separation** - Current week bets vs performance analysis data
- **Lifecycle management** - Automatic transition from active → historical → resolved

## Implementation Plan

### 1. Update Lambda Handler
Modify `prediction_generator.py` to accept parameters:
```python
def lambda_handler(event, context):
    sport = event.get('sport', 'basketball_nba')
    bet_type = event.get('bet_type', 'games')  # 'games' or 'props'
    model = event.get('model', 'consensus')
```

### 2. Add Sport-Specific Methods
Add new methods to `PredictionTracker`:
```python
def generate_game_predictions_for_sport(self, sport: str, model: str) -> int
def generate_prop_predictions_for_sport(self, sport: str, model: str) -> int
```

### 3. Update CloudWatch Events
Replace single rule with granular scheduling:
- NBA games predictions (consensus): Every 6 hours
- NBA props predictions (consensus): Every 6 hours  
- NFL games predictions (consensus): Every 6 hours
- NFL props predictions (consensus): Every 6 hours
- Future: Add value/momentum models with different schedules

### 4. Benefits
- **Parallel Processing**: Different sports/models can run simultaneously
- **Targeted Execution**: Only process what's needed
- **Better Error Handling**: Failure in one sport doesn't affect others
- **Scalability**: Easy to add new sports/models without affecting existing ones
- **Resource Optimization**: Smaller Lambda executions, better timeout management
- **Debugging**: Easier to trace issues to specific sport/model combinations
- **Active vs Historical Separation**: Clear distinction between current bets and performance analysis data
- **Model Performance Tracking**: Historical predictions enable accuracy measurement over time

## Files to Modify
- `backend/prediction_generator.py` - Add parameter handling
- `backend/prediction_tracker.py` - Add sport-specific methods
- `infrastructure/lib/odds-collector-stack.ts` - Add granular CloudWatch Events rules
- Update integration tests to test specific sport/model combinations

## Current Status
- **Planning Phase**: Documented optimization approach
- **Next Steps**: Implement granular lambda handler and sport-specific methods
- **Timeline**: Resume after break

## Related Work
This follows the same pattern we used for optimizing the odds collector:
- Changed from collecting all sports every 4 hours
- To NBA/NFL twice daily with staggered timing
- Added parallel processing and smart updating
- Resulted in 75% reduction in collection frequency and improved performance
