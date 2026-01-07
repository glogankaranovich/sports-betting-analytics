# ML Model Development Bias Analysis & Mitigation Guide

## Overview
This document identifies potential biases in the existing codebase that could negatively impact the development of our new 12-model ML analysis system. These biases must be addressed to ensure our models discover genuine predictive signals rather than reinforcing market inefficiencies.

## Identified Biases in Current Code

### 1. Market Consensus Bias (ConsensusModel)
**Location**: `backend/ml/models.py` - ConsensusModel class
**Issue**: Uses bookmaker odds as ground truth for probability calculations
**Problem**: Creates circular reasoning where models learn to replicate bookmaker behavior instead of finding genuine edges
**Code Example**:
```python
# Current problematic approach
home_probs = [self.decimal_to_probability(odds) for odds in home_odds]
avg_home_prob = sum(home_probs) / len(home_probs)
```

### 2. Equal Bookmaker Weighting
**Location**: `backend/ml/models.py` - Line 108-109
**Issue**: All bookmakers treated equally regardless of accuracy, volume, or market position
**Problem**: Small regional books get same weight as major market makers like FanDuel
**Impact**: Reduces signal quality from high-volume, efficient markets

### 3. Hardcoded Default Assumptions
**Location**: `backend/ml/models.py` - Lines 99-100, 171-172
**Issue**: Default 50/50 probability assumptions when no data available
**Problem**: Ignores known factors like home field advantage, team strength differences
**Code Example**:
```python
# Problematic defaults
home_win_probability=0.5,
away_win_probability=0.5,
```

### 4. Fixed Value Bet Threshold
**Location**: `backend/ml/models.py` - Line 127
**Issue**: Hardcoded 5% edge threshold for all situations
**Problem**: Same threshold regardless of sport variance, confidence level, or market conditions
**Code Example**:
```python
if home_ev > 0.05:  # Fixed threshold problematic
    value_bets.append(f"{bookmaker}_home")
```

### 5. Binary Outcome Classification
**Location**: `backend/outcome_collector.py` - Line 91
**Issue**: Treats all probabilities above 50% as equivalent predictions
**Problem**: 51% confidence treated same as 99% confidence in evaluation
**Code Example**:
```python
predicted_home_win = float(item.get("home_win_probability", 0.5)) > 0.5
analysis_correct = home_won == predicted_home_win
```

### 6. Simplified Vig Removal
**Location**: `backend/ml/models.py` - Lines 110-113
**Issue**: Assumes bookmakers distribute vig equally across all outcomes
**Problem**: Doesn't reflect actual bookmaker pricing strategies and market dynamics

## Bias Mitigation Strategies for New ML System

### 1. Independent Ground Truth
- **Use historical game outcomes** as training labels, not market consensus
- **Collect actual game results** from sports data APIs (ESPN, official league APIs)
- **Separate training data** from market pricing data completely

### 2. Weighted Market Analysis
- **Weight bookmakers** by volume, accuracy, and market efficiency
- **Track bookmaker performance** over time to adjust weights dynamically
- **Identify sharp vs recreational** bookmaker classifications

### 3. Sport-Specific Baselines
- **Calculate historical home field advantage** by sport, league, and venue
- **Use team strength ratings** as baseline probabilities instead of 50/50
- **Account for situational factors** (rest days, travel, injuries)

### 4. Dynamic Confidence Thresholds
- **Calculate value bet thresholds** based on model confidence intervals
- **Adjust thresholds by sport variance** (NFL vs NBA have different predictability)
- **Use Kelly Criterion** or similar for optimal bet sizing

### 5. Probabilistic Evaluation Metrics
- **Use Brier Score** for probability calibration assessment
- **Implement log-loss** for proper probability evaluation
- **Track calibration curves** to ensure model confidence matches reality

### 6. Bookmaker-Specific Modeling
- **Learn individual bookmaker biases** and pricing patterns
- **Model vig distribution** per bookmaker and market type
- **Identify bookmaker-specific inefficiencies**

## Implementation Guidelines for 12-Model System

### Model Training Principles
1. **Never use market odds as training targets** - only as features
2. **Validate on out-of-sample periods** with actual game outcomes
3. **Use cross-validation** that respects temporal ordering
4. **Separate model development** from market analysis

### Data Collection Standards
1. **Historical game outcomes** from official sources
2. **Team/player statistics** independent of betting markets
3. **Situational data** (weather, injuries, rest) from sports sources
4. **Market data** collected separately for comparison, not training

### Evaluation Framework
1. **Probabilistic metrics** (Brier score, log-loss, calibration)
2. **Long-term ROI tracking** with proper bankroll management
3. **Model performance** measured against actual outcomes, not market
4. **Regular bias audits** to detect model drift or market adaptation

## Action Items for Development Team

### Immediate (Before Model Development)
- [ ] Establish independent outcome data pipeline
- [ ] Implement probabilistic evaluation metrics
- [ ] Create sport-specific baseline calculations
- [ ] Document bookmaker weighting methodology

### During Model Development
- [ ] Regular bias audits of training data and model outputs
- [ ] Validation against actual outcomes, not market consensus
- [ ] Cross-validation with temporal splits
- [ ] Calibration testing for probability outputs

### Ongoing Monitoring
- [ ] Track model performance vs actual outcomes
- [ ] Monitor for market adaptation to model signals
- [ ] Regular recalibration of confidence thresholds
- [ ] Bookmaker bias pattern analysis

## Key Principle
**The goal is to predict actual game outcomes, not to replicate bookmaker pricing.** Our models should find genuine predictive signals that the market may be missing or mispricing, not learn to follow market consensus.
