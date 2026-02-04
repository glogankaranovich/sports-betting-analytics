# Data Collection Strategy for ML Analysis Models

## Overview

This document outlines the data collection requirements for each ML model in the sports betting analysis system. The system uses 12 specialized models per sport that generate independent analyses, combined through a weighted ensemble approach with dynamic performance-based weighting.

## Model Data Requirements

### 1. Management Model
**Purpose:** Analyze coaching decisions, game management, and strategic adjustments

**Required Data:**
- **NFL:** Head coach tendencies, play-calling patterns, timeout usage, 4th down decisions, red zone management
- **NBA:** Rotation patterns, timeout strategy, defensive schemes, late-game management, substitution patterns
- **Data Sources:** Coach statistics, historical decision patterns, team performance under pressure, situational coaching data

**Collection Frequency:** Daily (post-game analysis)
**Storage:** Coach/team-specific records with situational breakdowns

### 2. Team Momentum Model
**Purpose:** Analyze recent performance trends, winning/losing streaks, psychological factors

**Required Data:**
- **NFL:** Last 4 games performance, divisional record, home/away splits, primetime performance
- **NBA:** Last 10 games, back-to-back performance, rest days impact, road trip performance
- **Data Sources:** Recent game results, point differentials, performance trends, streak analysis

**Collection Frequency:** After each game
**Storage:** Rolling window of recent performance metrics

### 3. Team Stats Model
**Purpose:** Aggregate team performance metrics and efficiency analysis

**Required Data:**
- **NFL:** Offensive/defensive rankings, red zone efficiency, turnover differential, third down conversions
- **NBA:** Pace, offensive/defensive rating, rebounding, shooting percentages, assist-to-turnover ratio
- **Data Sources:** Season statistics, advanced metrics, efficiency ratings, team rankings

**Collection Frequency:** Daily (season-long aggregates)
**Storage:** Team-based statistical profiles with trend analysis

### 4. Player Stats Model
**Purpose:** Individual player performance, availability, and impact analysis

**Required Data:**
- **NFL:** Key player injuries, QB performance, skill position effectiveness, snap counts
- **NBA:** Star player usage, injury reports, minutes restrictions, load management
- **Data Sources:** Player statistics, injury reports, usage rates, performance metrics

**Collection Frequency:** Daily (injury reports), post-game (statistics)
**Storage:** Player-specific records with availability and performance tracking

### 5. Weather Conditions Model
**Purpose:** Environmental impact on game performance

**Required Data:**
- **NFL:** Temperature, wind speed, precipitation, dome vs outdoor, altitude effects
- **NBA:** Not applicable (indoor sport) - model returns neutral analysis
- **Data Sources:** Weather APIs, historical weather impact data, venue characteristics

**Collection Frequency:** Pre-game (6 hours before kickoff)
**Storage:** Game-specific weather records with historical impact correlation

### 6. Player Life Events Model
**Purpose:** Off-field factors affecting player performance

**Required Data:**
- **NFL/NBA:** Contract situations, personal milestones, trade rumors, family events, legal issues
- **Data Sources:** Sports news APIs, beat reporter updates, verified social media posts
- **Privacy Note:** Only publicly available information, no private data

**Collection Frequency:** Real-time monitoring of news sources
**Storage:** Player-specific event timeline with impact scoring

### 7. Public Opinion Model (Multi-Platform Sentiment)
**Purpose:** Betting public sentiment and social media analysis

**Required Data:**
- **Reddit:** r/sportsbook, team subreddits, game threads
- **Twitter/X:** Sports betting accounts, fan sentiment, trending topics
- **Discord:** Sports betting servers, community discussions, real-time chat sentiment
- **Sportsbook Data:** Betting percentages, handle distribution
- **Analysis:** Sentiment scoring, volume analysis, contrarian indicators

**Collection Frequency:** Real-time social media monitoring
**Storage:** Sentiment scores with platform-specific breakdowns

### 8. Market Inefficiency Model ("Unknown Force")
**Purpose:** Unexplained patterns, market anomalies, and contrarian opportunities

**Required Data:**
- **NFL/NBA:** Historical upset patterns, public fade opportunities, line value detection
- **Data Sources:** Historical betting data, upset analysis, market psychology patterns
- **Approach:** Statistical anomaly detection, pattern recognition, contrarian analysis

**Collection Frequency:** Continuous pattern analysis
**Storage:** Anomaly detection results with confidence scoring

### 9. Referee Bias Model
**Purpose:** Official tendencies and systematic patterns

**Required Data:**
- **NFL:** Penalty calling patterns, home field advantage impact, crew tendencies, flag distribution
- **NBA:** Foul calling rates, star player treatment, home court bias, technical foul patterns
- **Data Sources:** Referee statistics, historical officiating data, crew performance metrics

**Collection Frequency:** Post-game officiating analysis
**Storage:** Referee-specific tendency profiles with situational breakdowns

### 10. Referee Decision Model
**Purpose:** In-game officiating impact and critical calls

**Required Data:**
- **NFL:** Key penalty calls, replay reviews, game-changing decisions, spot calls
- **NBA:** Technical fouls, flagrant calls, late-game officiating, charge/block calls
- **Data Sources:** Real-time officiating data, historical decision patterns, game impact analysis

**Collection Frequency:** Real-time during games
**Storage:** Game-specific officiating impact records

### 11. Referee Life Events Model
**Purpose:** Personal factors affecting referee performance

**Required Data:**
- **NFL/NBA:** Referee travel schedules, career milestones, performance patterns, assignment history
- **Data Sources:** Public referee information, travel schedules, assignment patterns
- **Privacy Note:** Only publicly available professional information

**Collection Frequency:** Weekly schedule updates
**Storage:** Referee-specific professional timeline

### 12. Historical Performance Model
**Purpose:** Model learning from past analyses and outcomes

**Required Data:**
- **NFL/NBA:** Track each model's accuracy over time, learn from analysis errors, identify improvement patterns
- **Data Sources:** Historical analyses vs actual outcomes, model performance metrics, accuracy trends
- **Approach:** Meta-learning, performance pattern analysis, analytical accuracy optimization

**Collection Frequency:** Continuous performance tracking
**Storage:** Model performance metrics with trend analysis

## Enhanced Data Collection Architecture

### Current Infrastructure
- **Odds Collector:** Existing Lambda function collecting odds every 4 hours
- **DynamoDB:** Current storage for odds and game data
- **API Gateway:** Endpoints for data access

### Required Model-Specific Collectors

#### 1. Enhanced Odds & Market Collector
```python
# Increase frequency for real-time market analysis
# Current: Every 4 hours
# New: Every 5 minutes for active games, hourly for future games
```

#### 2. Performance Data Collectors
- **Team Stats Collector:** Daily team performance metrics
- **Player Stats Collector:** Individual player statistics and availability
- **Coaching Analytics Collector:** Strategic decision tracking

#### 3. External Data Collectors
- **Weather Collector:** Pre-game environmental conditions
- **News & Events Collector:** Player/team news monitoring
- **Social Sentiment Collector:** Multi-platform sentiment analysis

#### 4. Officiating Data Collectors
- **Referee Stats Collector:** Historical officiating patterns
- **Real-time Officiating Collector:** In-game decision tracking

### Data Storage Schema for ML Models

#### Model Analysis Records
```json
{
  "pk": "ANALYSIS#{game_id}#{model_name}",
  "sk": "ANALYSIS#{timestamp}",
  "model_type": "management|momentum|stats|player|weather|events|sentiment|inefficiency|referee_bias|referee_decision|referee_events|historical",
  "sport": "nfl|nba",
  "analysis_output": {
    "confidence": 0.85,
    "analysis_type": "value_bet|trend|anomaly",
    "key_factors": ["factor1", "factor2"],
    "expected_impact": 0.15
  },
  "input_data": {
    "data_sources": ["source1", "source2"],
    "data_quality": 0.95,
    "data_freshness": "2026-01-07T13:45:00Z"
  },
  "model_weight": 0.12,
  "status": "active|expired|verified"
}
```

#### Model Performance Tracking
```json
{
  "pk": "MODEL_PERF#{model_name}#{sport}",
  "sk": "PERFORMANCE#{date}",
  "accuracy": 0.72,
  "total_analyses": 45,
  "correct_analyses": 32,
  "roi": 0.08,
  "confidence_calibration": 0.85,
  "weight_adjustment": 0.02,
  "performance_trend": "improving|stable|declining"
}
```

#### Outcome Verification Records
```json
{
  "pk": "OUTCOME#{game_id}",
  "sk": "VERIFICATION#{model_name}",
  "analysis_id": "reference_to_analysis",
  "actual_outcome": "win|loss|push",
  "model_accuracy": "correct|incorrect",
  "confidence_vs_accuracy": {
    "predicted_confidence": 0.85,
    "actual_accuracy": 1.0
  },
  "roi_performance": {
    "predicted_roi": 0.15,
    "actual_roi": 0.12
  },
  "verification_date": "2026-01-07T20:00:00Z"
}
```

## Implementation Priority

### Phase 1: Core Model Data Collection
1. Enhanced odds collection with market movement tracking
2. Team and player statistics collectors
3. Basic performance tracking infrastructure

### Phase 2: Advanced Analytics Data
1. Social sentiment monitoring
2. Weather and external factors
3. Coaching and management analytics

### Phase 3: Officiating Intelligence
1. Referee statistics and patterns
2. Real-time officiating impact tracking
3. Historical officiating analysis

### Phase 4: Meta-Learning System
1. Model performance optimization
2. Dynamic weight adjustment
3. Continuous improvement algorithms

## Data Quality & Performance Metrics

### Data Quality Standards
- **Completeness:** 95% of required fields populated
- **Freshness:** Data updated within specified frequency windows
- **Accuracy:** 99% validation against authoritative sources
- **Consistency:** Cross-source data alignment verification

### Model Performance Tracking
- **Individual Model Accuracy:** Track each model's analysis accuracy
- **Ensemble Performance:** Combined weighted model performance
- **ROI Tracking:** Actual returns vs predicted returns
- **Confidence Calibration:** Alignment of confidence scores with accuracy

### Success Criteria
- **Real-time Data:** 95% of critical data updates within 5 minutes
- **Historical Coverage:** Complete training data for all models
- **System Reliability:** 99.9% uptime for data collection
- **Analysis Quality:** Consistent improvement in model accuracy over time
