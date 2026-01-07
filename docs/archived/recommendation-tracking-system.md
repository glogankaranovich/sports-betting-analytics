# Recommendation Tracking & Verification System

## Overview
System for storing, tracking, and improving bet recommendations through outcome verification and performance analysis.

## Storage Strategy

### Why Store Recommendations?
- **Performance**: Pre-computed recommendations faster than real-time generation
- **Tracking**: Historical data needed for performance measurement
- **Consistency**: Same recommendations across user sessions
- **Analytics**: Track user adoption and recommendation effectiveness

### DynamoDB Schema Options

**Option 1: Separate Recommendation Table**
```
Table: sports-betting-recommendations-{env}
PK: "REC#{date}#{sport}"
SK: "{model}#{risk_level}#{game_id}#{bet_type}"
```

**Option 2: Extend Existing Table**
```
Table: sports-betting-bets-{env}
PK: "GAME#{game_id}" or "PROP#{game_id}#{player}"
SK: "RECOMMENDATION#{model}#{risk_level}"
```

**Option 3: Time-based Partitioning**
```
PK: "RECOMMENDATIONS#{date}"
SK: "{sport}#{model}#{risk_level}#{game_id}#{bet_type}"
```

## Recommendation Data Structure

```json
{
  "recommendation_id": "string",
  "game_id": "string",
  "sport": "string",
  "model": "consensus|value|momentum",
  "risk_level": "conservative|moderate|aggressive",
  "bet_type": "moneyline|spread|total|prop",
  "team_or_player": "string",
  "market": "string",
  
  // Prediction Data
  "predicted_probability": 0.75,
  "confidence_score": 0.68,
  "bookmaker_odds": -110,
  "implied_probability": 0.52,
  
  // Recommendation Data
  "expected_value": 0.15,
  "kelly_fraction": 0.05,
  "recommended_bet_amount": 25.00,
  "potential_payout": 47.73,
  "reasoning": "string",
  
  // Tracking Data
  "created_at": "2026-01-03T19:20:00Z",
  "expires_at": "2026-01-04T01:00:00Z",
  "is_active": true,
  
  // Outcome Data (filled post-game)
  "actual_outcome": null,
  "bet_won": null,
  "actual_roi": null,
  "outcome_verified_at": null
}
```

## Improvement Strategy

### Two-Layer Approach

**Layer 1: Prediction Accuracy (Primary)**
- Improve underlying ML predictions
- Better predictions automatically improve recommendations
- Focus: Model training, feature engineering, data quality

**Layer 2: Recommendation Engine (Secondary)**
- Optimize Kelly Criterion parameters
- Adjust risk level thresholds
- Fine-tune bet sizing algorithms
- Focus: Recommendation logic, risk management

### Performance Metrics

**Prediction Metrics**
- Accuracy rate by sport/bet type
- Calibration (predicted vs actual probabilities)
- Confidence score reliability

**Recommendation Metrics**
- ROI by risk level
- Win rate vs expected win rate
- Kelly Criterion effectiveness
- User adoption rate

## Implementation Phases

### Phase 1: Outcome Verification (Task #15)
- Collect actual game results
- Store outcomes in existing prediction records
- Calculate prediction accuracy metrics

### Phase 2: Recommendation Storage
- Design final DynamoDB schema
- Implement recommendation persistence
- Add recommendation lifecycle management

### Phase 3: Performance Analysis
- Build recommendation vs outcome comparison
- Track model attribution and performance
- Implement feedback loop for model improvement

### Phase 4: Optimization
- A/B test different Kelly parameters
- Optimize risk level thresholds
- Implement dynamic model weighting

## Questions for Schema Design

1. **Partitioning Strategy**: Date-based vs game-based vs sport-based?
2. **Query Patterns**: How will we query recommendations (by date, sport, model, risk level)?
3. **Retention Policy**: How long to keep recommendation history?
4. **Indexing**: What GSIs needed for analytics queries?
5. **Volume**: Expected recommendations per day/sport/model combination?

## Next Steps

1. Finalize DynamoDB schema based on query patterns
2. Complete Task #15 (Outcome Verification System)
3. Implement recommendation storage and retrieval
4. Build performance tracking dashboard
