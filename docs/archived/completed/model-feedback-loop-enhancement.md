# Model Performance Feedback Loop

## Overview
Implement a feedback loop that uses verified analysis outcomes to improve model performance over time through dynamic weighting and retraining.

## Current State
- **Analytics**: Passive tracking of model performance (accuracy, confidence, ROI)
- **Models**: Static consensus model using bookmaker odds averaging
- **No Learning**: Models don't improve based on past performance

## Proposed Enhancement

### 1. Dynamic Model Weighting
Adjust model confidence and weights based on recent performance:

```python
class DynamicModelWeighting:
    def calculate_adjusted_confidence(self, base_confidence, model_name, sport):
        """Adjust confidence based on recent model performance"""
        recent_accuracy = get_recent_accuracy(model_name, sport, days=30)
        
        # Boost or reduce confidence based on performance
        if recent_accuracy > 0.6:
            multiplier = 1.0 + (recent_accuracy - 0.6) * 0.5  # Up to 1.2x
        else:
            multiplier = recent_accuracy / 0.6  # Down to 0.5x at 30% accuracy
        
        return min(base_confidence * multiplier, 1.0)
```

### 2. Performance-Based Model Selection
Dynamically weight multiple models based on their recent performance:

```python
class EnsembleWeighting:
    def get_dynamic_weights(self, sport, bet_type):
        """Calculate model weights based on recent performance"""
        models = ['consensus', 'value', 'momentum']
        performances = {}
        
        for model in models:
            accuracy = get_recent_accuracy(model, sport, bet_type, days=30)
            brier_score = get_recent_brier_score(model, sport, bet_type, days=30)
            
            # Combined performance score
            performances[model] = (accuracy * 0.7) + ((1 - brier_score) * 0.3)
        
        # Normalize to weights
        total = sum(performances.values())
        return {m: p/total for m, p in performances.items()}
```

### 3. Feature Importance Learning
Identify which factors lead to accurate predictions:

```python
class FeatureAnalyzer:
    def analyze_prediction_factors(self, sport):
        """Analyze what factors correlate with accurate predictions"""
        verified_analyses = get_verified_analyses(sport)
        
        factors = {
            'odds_consensus_strength': [],
            'confidence_level': [],
            'bookmaker_agreement': [],
            'market_efficiency': []
        }
        
        for analysis in verified_analyses:
            if analysis['analysis_correct']:
                # Track factors that led to correct predictions
                factors['odds_consensus_strength'].append(
                    calculate_consensus_strength(analysis)
                )
                # ... track other factors
        
        return calculate_feature_importance(factors)
```

### 4. Model Retraining Pipeline
Periodically retrain models with verified outcomes:

```python
class ModelRetrainingPipeline:
    def retrain_models(self, sport, min_samples=100):
        """Retrain models when enough verified data is available"""
        verified_data = get_verified_analyses(sport)
        
        if len(verified_data) < min_samples:
            return False
        
        # Prepare training data
        X, y = prepare_training_data(verified_data)
        
        # Retrain each model
        for model_name in ['consensus', 'value', 'momentum']:
            model = load_model(model_name)
            model.fit(X, y)
            
            # Validate on holdout set
            accuracy = validate_model(model, holdout_data)
            
            if accuracy > get_current_accuracy(model_name):
                deploy_model(model, model_name)
                log_model_update(model_name, accuracy)
```

### 5. Adaptive Confidence Calibration
Adjust confidence scores to match actual accuracy:

```python
class ConfidenceCalibrator:
    def calibrate_confidence(self, model_name, sport):
        """Calibrate confidence scores based on historical accuracy"""
        analyses = get_verified_analyses(model_name, sport)
        
        # Group by confidence buckets
        buckets = {
            'high': {'predicted': [], 'actual': []},
            'medium': {'predicted': [], 'actual': []},
            'low': {'predicted': [], 'actual': []}
        }
        
        for analysis in analyses:
            bucket = get_confidence_bucket(analysis['confidence'])
            buckets[bucket]['predicted'].append(analysis['confidence'])
            buckets[bucket]['actual'].append(analysis['analysis_correct'])
        
        # Calculate calibration adjustments
        adjustments = {}
        for bucket, data in buckets.items():
            avg_predicted = np.mean(data['predicted'])
            avg_actual = np.mean(data['actual'])
            adjustments[bucket] = avg_actual / avg_predicted
        
        return adjustments
```

## Implementation Plan

### Phase 1: Dynamic Weighting (1-2 days)
- [ ] Implement performance-based confidence adjustment
- [ ] Add dynamic model weighting based on recent accuracy
- [ ] Update analysis generator to use adjusted confidence

### Phase 2: Feature Analysis (2-3 days)
- [ ] Build feature importance analyzer
- [ ] Track factors that correlate with accuracy
- [ ] Generate insights on what makes predictions accurate

### Phase 3: Confidence Calibration (1-2 days)
- [ ] Implement confidence calibration system
- [ ] Adjust confidence scores to match actual accuracy
- [ ] Add calibration metrics to analytics dashboard

### Phase 4: Model Retraining (3-4 days)
- [ ] Build automated retraining pipeline
- [ ] Implement model validation and deployment
- [ ] Add monitoring for model performance drift
- [ ] Schedule periodic retraining jobs

## Success Metrics

### Short-term (1 month)
- Confidence scores calibrated within 5% of actual accuracy
- Dynamic weighting improves ensemble accuracy by 3-5%
- Feature importance insights documented

### Long-term (3-6 months)
- Models retrained monthly with verified data
- Overall accuracy improves by 10-15%
- Automated drift detection and retraining
- Confidence calibration error < 3%

## Dependencies
- Sufficient verified outcomes (100+ per sport/bet type)
- Model analytics infrastructure (✅ Complete)
- Outcome verification system (✅ Complete, needs bug fix)
- Historical performance data storage

## Risks & Considerations
- **Overfitting**: Need sufficient data to avoid overfitting to recent results
- **Concept Drift**: Sports betting markets change, need to balance recent vs historical data
- **Computational Cost**: Retraining models requires compute resources
- **Data Quality**: Accurate feedback requires correct outcome verification

## Next Steps
1. Fix prop bet verification bug (prerequisite)
2. Collect 2-4 weeks of verified outcomes
3. Implement Phase 1 (Dynamic Weighting)
4. Monitor impact on accuracy
5. Proceed to subsequent phases based on results

---

**Status**: Proposed Enhancement  
**Priority**: Medium (after prop verification fix)  
**Estimated Effort**: 2-3 weeks  
**Created**: 2026-01-22
