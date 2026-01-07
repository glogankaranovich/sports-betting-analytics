# Recommendation Tracking & Verification System

## Overview
System for storing, tracking, and improving bet recommendations through outcome verification and performance analysis.

## Requirements
- **Top 10 recommendations per sport** (scalable to more)
- **Recommendations as separate entities** associated with predictions
- **Avoid one-way doors** - design for future growth
- **Query pattern**: Active recommendations by sport
- **Keep it simple** - optimize later when needed

## Schema Design

### Recommendation Storage (Simple Approach)
```
Table: sports-betting-bets-{env}
PK: "RECOMMENDATIONS#{sport}#{model}#{risk_level}"
SK: "REC#{rank}#{created_timestamp}#{game_id}"

// Examples:
PK: "RECOMMENDATIONS#NBA#consensus#moderate"
PK: "RECOMMENDATIONS#NBA#value#aggressive"
SK: "REC#01#20260103T192000#game123"
```

**Trade-offs:**
- ✅ Personalized: Different top 10 for each model/risk combination
- ✅ Simple queries: Single partition key gets top 10
- ✅ Scalable: Easy to add new models or risk levels
- ⚠️ More partitions but still manageable volume
- 🔄 Can refactor later when volume increases

### Recommendation Data Structure
```json
{
  "PK": "RECOMMENDATIONS#NBA#consensus#moderate",
  "SK": "REC#01#20260103T192000#game123",
  
  // Association to prediction
  "prediction_pk": "GAME#game123",
  "prediction_sk": "PREDICTION#consensus",
  
  // Recommendation data
  "rank": 1,
  "sport": "NBA",
  "game_id": "game123",
  "model": "consensus",
  "risk_level": "moderate",
  "bet_type": "moneyline",
  "team_or_player": "Lakers",
  "expected_value": 0.15,
  "kelly_fraction": 0.05,
  "recommended_bet_amount": 25.00,
  "potential_payout": 47.73,
  "reasoning": "Strong consensus with 15% edge",
  
  // Lifecycle
  "created_at": "2026-01-03T19:20:00Z",
  "expires_at": "2026-01-04T01:00:00Z",
  "is_active": true,
  
  // Outcome (filled after game completion)
  "actual_outcome": null,
  "bet_won": null,
  "actual_roi": null,
  "outcome_verified_at": null
}
```

## Query Patterns

**Get Top 10 NBA Recommendations for Consensus Model, Moderate Risk:**
```
Query: PK = "RECOMMENDATIONS#NBA#consensus#moderate"
Limit: 10
SortOrder: Ascending (gets ranks 1-10)
```

**Get Top 10 NBA Recommendations for Value Model, Aggressive Risk:**
```
Query: PK = "RECOMMENDATIONS#NBA#value#aggressive"
Limit: 10
SortOrder: Ascending (gets ranks 1-10)
```

**Get Associated Prediction:**
```
Query: PK = prediction_pk, SK = prediction_sk
```

## Model Performance Tracking

**Question**: How do we track model performance without storing aggregated stats?

**Options:**
1. **Real-time calculation**: Query all completed recommendations and calculate on-demand
2. **Separate performance table**: Store aggregated metrics in different table
3. **CloudWatch metrics**: Push performance data to CloudWatch for dashboards
4. **Analytics database**: ETL recommendation outcomes to analytics store

**Recommendation**: Start with real-time calculation (simple), move to CloudWatch metrics as we scale.

## Implementation Benefits

- **No one-way doors**: Can easily increase recommendation count
- **Clean separation**: Recommendations don't pollute prediction data
- **Efficient queries**: Single partition key gets top N for sport
- **Future-proof**: Schema supports multiple models, risk levels
- **Performance tracking**: Clear association for outcome verification
- **Simple to start**: Avoid premature optimization

## Next Steps

1. Implement recommendation storage schema
2. Build recommendation generation and ranking logic
3. Add outcome verification when games complete
4. Decide on model performance tracking approach
