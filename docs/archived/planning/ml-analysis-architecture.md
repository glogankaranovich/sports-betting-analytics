# ML Analysis Architecture

## Overview

The sports betting analytics system uses machine learning models to analyze betting opportunities and generate insights. The system focuses on data collection, model training, outcome verification, and insight generation rather than simple predictions.

## Core Concepts

### Terminology
- **Analysis**: ML-driven evaluation of betting opportunities (replaces "prediction")
- **Insight**: Actionable betting recommendations with confidence scores (replaces "recommendation")
- **Model**: Specialized ML algorithm trained on specific data types
- **Outcome Verification**: Tracking actual results vs model analysis for continuous improvement

## ML Model Architecture

### 1. Data Collection Models
Each model requires specific data types for training and analysis:

#### Consensus Model
- **Data Sources**: Bookmaker odds, line movements, market consensus
- **Purpose**: Identify value bets through odds discrepancy analysis
- **Training Data**: Historical odds vs actual outcomes

#### Performance Model  
- **Data Sources**: Player statistics, team performance, injury reports
- **Purpose**: Analyze player/team performance trends
- **Training Data**: Historical performance metrics vs game outcomes

#### Market Movement Model
- **Data Sources**: Real-time odds changes, betting volume, line movements
- **Purpose**: Detect sharp money and market inefficiencies
- **Training Data**: Historical line movements vs closing odds accuracy

#### Weather/External Model
- **Data Sources**: Weather conditions, venue factors, external events
- **Purpose**: Account for environmental impact on game outcomes
- **Training Data**: Historical weather/venue data vs game results

### 2. Model Weighting System

Models are weighted based on:
- **Historical Accuracy**: Track record of correct analyses
- **Confidence Score**: Model's internal confidence in analysis
- **Data Quality**: Completeness and freshness of input data
- **Market Conditions**: Current betting environment and liquidity

### 3. Outcome Verification

For each analysis:
1. **Store Analysis**: Model output, confidence, data inputs
2. **Track Outcome**: Actual game/bet result
3. **Calculate Accuracy**: Compare analysis vs reality
4. **Update Weights**: Adjust model importance based on performance
5. **Retrain Models**: Use new data to improve accuracy

## Insight Generation Process

### 1. Data Collection
- Gather real-time data for all models
- Validate data quality and completeness
- Store raw data for model training

### 2. Model Analysis
- Run each model against current data
- Generate analysis with confidence scores
- Weight results based on model performance

### 3. Insight Synthesis
- Combine weighted model outputs
- Calculate overall confidence score
- Estimate potential return on investment
- Rank opportunities by confidence × ROI

### 4. Top Picks Selection
Select insights based on:
- **Minimum Confidence Threshold**: Only high-confidence analyses
- **Expected Value**: Positive expected return calculations
- **Risk Assessment**: Bankroll management considerations
- **Market Availability**: Ensure bets are still available

## Data Storage Schema

### Analysis Records
```
{
  "analysis_id": "unique_identifier",
  "timestamp": "analysis_time",
  "bet_type": "game|prop|futures",
  "event_id": "game_or_event_identifier",
  "models_used": ["consensus", "performance", "market"],
  "model_outputs": {
    "consensus": {"confidence": 0.85, "analysis": "..."},
    "performance": {"confidence": 0.72, "analysis": "..."}
  },
  "weighted_confidence": 0.78,
  "expected_value": 0.15,
  "insight_type": "value_bet|arbitrage|trend",
  "status": "active|expired|settled"
}
```

### Outcome Verification
```
{
  "analysis_id": "reference_to_analysis",
  "actual_outcome": "win|loss|push",
  "model_accuracy": {
    "consensus": "correct|incorrect",
    "performance": "correct|incorrect"
  },
  "roi_actual": 0.12,
  "roi_predicted": 0.15,
  "verification_date": "settlement_time"
}
```

## Implementation Phases

### Phase 1: Data Collection Infrastructure
- Build data collectors for each model type
- Establish data validation and storage
- Create data quality monitoring

### Phase 2: Model Development
- Implement individual ML models
- Train on historical data
- Establish baseline accuracy metrics

### Phase 3: Insight Engine
- Build model weighting system
- Create insight synthesis logic
- Implement top picks selection

### Phase 4: Outcome Tracking
- Build verification system
- Implement model performance tracking
- Create automated retraining pipelines

## Success Metrics

- **Model Accuracy**: Percentage of correct analyses per model
- **ROI Performance**: Actual returns vs predicted returns
- **Insight Quality**: User engagement with top picks
- **System Reliability**: Uptime and data freshness
