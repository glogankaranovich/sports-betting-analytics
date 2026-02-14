# Data Inconsistency Investigation - Model Analytics

## Priority: HIGH

## Issue
ModelAnalytics and ModelComparison show different numbers for the same models.

## Root Cause

### `/analytics` Endpoint (ModelAnalytics Component)
**Data Source:** `model_analytics.py` → `_get_verified_analyses()`
**Query:**
```python
pk = f"VERIFIED#{model}#{sport}#{bet_type}"
# No time filter - gets ALL verified predictions
```
**Characteristics:**
- Returns ALL-TIME accuracy
- Cached in DynamoDB as `ANALYTICS#summary`
- Updated periodically (when? by what Lambda?)
- Example: 89 total predictions for consensus

### `/model-comparison` Endpoint (ModelComparison Component)
**Data Source:** `api_handler.py` → `_get_model_comparison_data()`
**Query:**
```python
pk = f"VERIFIED#{model}#{sport}#game"
# WITH time filter: verified_analysis_sk >= cutoff_time
```
**Characteristics:**
- Returns RECENT accuracy (last 7/30/90 days)
- Calculated live on each request
- Example: 50 predictions in last 30 days

## The Mismatch Explained

User sees:
- **ModelAnalytics:** "Consensus: 50.6% accuracy (45/89 predictions)"
  - This is ALL-TIME performance
- **ModelComparison:** "Consensus: 48.0% accuracy (24/50 predictions)"  
  - This is LAST 30 DAYS performance

Both are technically correct, but they're measuring different things!

## Impact

**User Confusion:**
- Users think one of the dashboards is broken
- Can't trust the numbers
- Don't know which to believe

**Business Logic:**
- Dynamic weighting uses recent performance (30 days)
- But ModelAnalytics shows all-time
- Inconsistent decision-making

## Solutions

### Option 1: Make ModelAnalytics Time-Filtered (RECOMMENDED)
**Change:** Update `_get_verified_analyses()` to accept a `days` parameter
**Pros:**
- Both dashboards show same timeframe
- More relevant (recent performance matters more)
- Consistent with dynamic weighting logic
**Cons:**
- Need to update cached analytics
- Might break existing code that depends on all-time stats

### Option 2: Add Time Filter to ModelAnalytics UI
**Change:** Add dropdown to ModelAnalytics for 7/30/90/All-time
**Pros:**
- User can choose timeframe
- Backwards compatible
**Cons:**
- More complex UI
- Still confusing if defaults differ

### Option 3: Remove ModelAnalytics, Keep Only ModelComparison
**Change:** Delete ModelAnalytics component entirely
**Pros:**
- One source of truth
- Simpler codebase
**Cons:**
- Lose cached analytics (performance benefit)
- Lose all-time historical view

### Option 4: Clearly Label Each Dashboard
**Change:** Add "All-Time Performance" vs "Recent Performance (30 days)"
**Pros:**
- Quick fix
- Both dashboards remain useful
**Cons:**
- Still confusing
- Doesn't solve underlying inconsistency

## Recommendation

**Option 1: Make ModelAnalytics Time-Filtered**

1. Update `_get_verified_analyses()` to filter by time
2. Update cached analytics to store multiple timeframes (7/30/90/all)
3. Make both dashboards use same data source
4. Add clear labels: "Last 30 Days Performance"

## Code Changes Required

### 1. Update `model_analytics.py`
```python
def _get_verified_analyses(self, models: List[str] = None, days: int = None):
    """Get verified analyses, optionally filtered by time"""
    from datetime import datetime, timedelta
    
    cutoff_time = None
    if days:
        cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    # ... existing code ...
    
    if cutoff_time:
        response = self.table.query(
            IndexName="VerifiedAnalysisGSI",
            KeyConditionExpression="verified_analysis_pk = :pk AND verified_analysis_sk >= :cutoff",
            ExpressionAttributeValues={":pk": pk, ":cutoff": cutoff_time},
        )
    else:
        # All-time query (existing code)
```

### 2. Update `/analytics` endpoint
```python
def handle_get_analytics(query_params: Dict[str, str]):
    days = int(query_params.get("days", 30))  # Default to 30 days
    # Pass days parameter to analytics methods
```

### 3. Update ModelAnalytics component
```tsx
// Add days filter dropdown
const [days, setDays] = useState(30);
// Pass to API call
```

## Testing Required

- [ ] Verify both dashboards show same numbers with same timeframe
- [ ] Test with different timeframes (7/30/90 days)
- [ ] Verify cached analytics update correctly
- [ ] Check performance impact of live queries

## Timeline

- Investigation: ✅ Complete
- Code changes: 2-3 hours
- Testing: 1 hour
- Deployment: 30 min

**Total: ~4 hours**

## Status

🔴 **BLOCKED** - Waiting for decision on which option to implement
