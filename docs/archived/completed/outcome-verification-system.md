# Outcome Verification & Model Performance Tracking System

## Overview
This system tracks actual game outcomes against model analyses to provide bias-free performance evaluation and continuous model improvement. It implements the evaluation framework defined in our ML training implementation.

## Data Collection Architecture

### 1. Outcome Data Sources
```python
class OutcomeDataCollector:
    def __init__(self):
        self.sources = {
            'espn_api': ESPNScoreAPI(),
            'nfl_api': NFLOfficialAPI(),
            'nba_api': NBAOfficialAPI(),
            'sports_reference': SportsReferenceAPI(),
            'backup_manual': ManualEntrySystem()
        }
    
    def collect_game_outcome(self, game_id: str, sport: str) -> Dict:
        """Collect verified game outcome from multiple sources"""
        outcomes = {}
        
        # Try primary sources first
        for source_name, source in self.sources.items():
            try:
                outcome = source.get_game_result(game_id, sport)
                if outcome and self.validate_outcome(outcome):
                    outcomes[source_name] = outcome
            except Exception as e:
                logger.warning(f"Failed to get outcome from {source_name}: {e}")
        
        # Consensus validation (require 2+ sources to agree)
        verified_outcome = self.consensus_validation(outcomes)
        
        if not verified_outcome:
            # Flag for manual review
            self.flag_for_manual_review(game_id, outcomes)
            
        return verified_outcome
    
    def validate_outcome(self, outcome: Dict) -> bool:
        """Validate outcome data completeness and consistency"""
        required_fields = ['home_score', 'away_score', 'game_status', 'final_time']
        return all(field in outcome for field in required_fields)
```

### 2. Analysis Storage Schema
```python
# DynamoDB Schema for Analysis Tracking
ANALYSIS_RECORD = {
    'PK': 'ANALYSIS#{game_id}',
    'SK': 'MODEL#{model_name}#{timestamp}',
    'GSI1PK': 'MODEL#{model_name}',
    'GSI1SK': 'DATE#{date}',
    
    # Analysis Data
    'game_id': str,
    'sport': str,
    'model_name': str,
    'analysis_timestamp': str,
    'home_win_probability': float,
    'away_win_probability': float,
    'confidence_score': float,
    'value_bets': List[str],
    'model_version': str,
    'input_features': Dict,
    
    # Outcome Data (populated after game)
    'actual_home_score': int,
    'actual_away_score': int,
    'actual_home_won': bool,
    'outcome_verified_at': str,
    'outcome_source': str,
    
    # Performance Metrics (calculated)
    'prediction_correct': bool,
    'brier_score': float,
    'log_loss': float,
    'calibration_error': float,
    'roi': float,
    'confidence_accuracy': float
}
```

## Performance Tracking System

### 1. Real-time Performance Calculator
```python
class PerformanceTracker:
    def __init__(self):
        self.metrics_calculator = MetricsCalculator()
        self.weight_updater = WeightUpdater()
        
    def process_game_outcome(self, game_id: str, actual_outcome: Dict):
        """Process completed game and update all model performance"""
        
        # Get all analyses for this game
        analyses = self.get_game_analyses(game_id)
        
        for analysis in analyses:
            # Calculate performance metrics
            metrics = self.calculate_analysis_metrics(analysis, actual_outcome)
            
            # Update analysis record with outcome and metrics
            self.update_analysis_record(analysis['PK'], analysis['SK'], {
                'actual_home_score': actual_outcome['home_score'],
                'actual_away_score': actual_outcome['away_score'],
                'actual_home_won': actual_outcome['home_won'],
                'outcome_verified_at': datetime.utcnow().isoformat(),
                'outcome_source': actual_outcome['source'],
                **metrics
            })
            
            # Update model performance history
            self.update_model_performance(analysis['model_name'], metrics)
        
        # Trigger weight recalculation if needed
        self.check_weight_update_trigger(game_id)
    
    def calculate_analysis_metrics(self, analysis: Dict, outcome: Dict) -> Dict:
        """Calculate comprehensive performance metrics"""
        predicted_prob = analysis['home_win_probability']
        actual_outcome = outcome['home_won']
        
        return {
            'prediction_correct': (predicted_prob > 0.5) == actual_outcome,
            'brier_score': self.metrics_calculator.brier_score(predicted_prob, actual_outcome),
            'log_loss': self.metrics_calculator.log_loss(predicted_prob, actual_outcome),
            'calibration_error': self.metrics_calculator.calibration_error(predicted_prob, actual_outcome),
            'confidence_accuracy': self.metrics_calculator.confidence_accuracy(
                analysis['confidence_score'], predicted_prob, actual_outcome
            )
        }
```

### 2. Model Performance Aggregation
```python
class ModelPerformanceAggregator:
    def __init__(self):
        self.lookback_periods = {
            'recent': 30,      # Last 30 predictions
            'monthly': 90,     # Last 3 months
            'seasonal': 180,   # Last 6 months
            'yearly': 365      # Full year
        }
    
    def calculate_model_performance(self, model_name: str, sport: str) -> Dict:
        """Calculate comprehensive model performance metrics"""
        performance = {}
        
        for period_name, days in self.lookback_periods.items():
            # Get analyses from this period
            analyses = self.get_model_analyses(model_name, sport, days)
            
            if len(analyses) < 10:  # Minimum sample size
                performance[period_name] = None
                continue
            
            # Calculate aggregated metrics
            performance[period_name] = {
                'sample_size': len(analyses),
                'accuracy': self.calculate_accuracy(analyses),
                'avg_brier_score': self.calculate_avg_brier(analyses),
                'avg_log_loss': self.calculate_avg_log_loss(analyses),
                'calibration_slope': self.calculate_calibration_slope(analyses),
                'calibration_intercept': self.calculate_calibration_intercept(analyses),
                'roi': self.calculate_roi(analyses),
                'sharpe_ratio': self.calculate_sharpe_ratio(analyses),
                'max_drawdown': self.calculate_max_drawdown(analyses),
                'confidence_correlation': self.calculate_confidence_correlation(analyses),
                'overconfidence_ratio': self.calculate_overconfidence_ratio(analyses)
            }
        
        return performance
    
    def calculate_calibration_slope(self, analyses: List[Dict]) -> float:
        """Calculate calibration slope (perfect calibration = 1.0)"""
        probabilities = [a['home_win_probability'] for a in analyses]
        outcomes = [float(a['actual_home_won']) for a in analyses]
        
        # Linear regression: outcome ~ probability
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(np.array(probabilities).reshape(-1, 1), outcomes)
        
        return model.coef_[0]
```

### 3. Performance Monitoring & Alerts
```python
class PerformanceMonitor:
    def __init__(self):
        self.alert_thresholds = {
            'accuracy_drop': 0.05,      # 5% accuracy drop
            'brier_increase': 0.02,     # Brier score increase
            'roi_drop': 0.03,           # 3% ROI drop
            'calibration_drift': 0.1    # Calibration error increase
        }
    
    def monitor_model_drift(self, model_name: str, sport: str):
        """Monitor for model performance drift"""
        current_performance = self.get_recent_performance(model_name, sport, days=30)
        baseline_performance = self.get_baseline_performance(model_name, sport)
        
        alerts = []
        
        # Check for significant performance drops
        for metric, threshold in self.alert_thresholds.items():
            current_value = current_performance.get(metric, 0)
            baseline_value = baseline_performance.get(metric, 0)
            
            if metric in ['accuracy', 'roi']:  # Higher is better
                if baseline_value - current_value > threshold:
                    alerts.append({
                        'type': 'performance_drop',
                        'metric': metric,
                        'current': current_value,
                        'baseline': baseline_value,
                        'drop': baseline_value - current_value
                    })
            else:  # Lower is better (brier, calibration_error)
                if current_value - baseline_value > threshold:
                    alerts.append({
                        'type': 'performance_degradation',
                        'metric': metric,
                        'current': current_value,
                        'baseline': baseline_value,
                        'increase': current_value - baseline_value
                    })
        
        if alerts:
            self.send_performance_alerts(model_name, sport, alerts)
            self.trigger_model_review(model_name, sport, alerts)
        
        return alerts
```

## Weight Update System

### 1. Dynamic Weight Calculator
```python
class DynamicWeightCalculator:
    def __init__(self):
        self.min_weight = 0.02
        self.max_weight = 0.25
        self.recency_factor = 0.7
        
    def calculate_updated_weights(self, sport: str) -> Dict[str, float]:
        """Calculate new model weights based on recent performance"""
        model_performances = {}
        
        # Get performance for each model
        for model_name in self.get_active_models(sport):
            performance = self.get_model_performance_score(model_name, sport)
            model_performances[model_name] = performance
        
        # Calculate raw weights
        raw_weights = {}
        for model_name, performance in model_performances.items():
            raw_weights[model_name] = self.performance_to_weight(performance)
        
        # Apply constraints and normalize
        constrained_weights = self.apply_weight_constraints(raw_weights)
        normalized_weights = self.normalize_weights(constrained_weights)
        
        return normalized_weights
    
    def performance_to_weight(self, performance: Dict) -> float:
        """Convert performance metrics to weight score"""
        # Multi-metric scoring with different weights
        accuracy_score = max(0, (performance['accuracy'] - 0.5) * 2)  # Scale 0.5-1.0 to 0-1
        brier_score = max(0, 1 - (performance['brier_score'] / 0.25))  # Scale vs random
        roi_score = max(0, min(1, performance['roi'] / 0.1))  # Cap at 10% ROI
        calibration_score = max(0, 1 - (performance['calibration_error'] / 0.2))
        
        # Weighted combination
        weight_score = (
            accuracy_score * 0.3 +
            brier_score * 0.3 +
            roi_score * 0.25 +
            calibration_score * 0.15
        )
        
        return weight_score
    
    def should_update_weights(self, sport: str) -> bool:
        """Determine if weights should be updated"""
        last_update = self.get_last_weight_update(sport)
        hours_since_update = (datetime.utcnow() - last_update).total_seconds() / 3600
        
        # Update conditions
        min_hours_passed = hours_since_update >= 24  # Daily updates
        significant_games_completed = self.count_completed_games_since_update(sport, last_update) >= 5
        performance_drift_detected = self.detect_performance_drift(sport)
        
        return min_hours_passed or significant_games_completed or performance_drift_detected
```

### 2. Weight Update Execution
```python
class WeightUpdater:
    def __init__(self):
        self.calculator = DynamicWeightCalculator()
        self.validator = WeightValidator()
        
    def update_model_weights(self, sport: str, force: bool = False):
        """Update model weights if conditions are met"""
        
        if not force and not self.calculator.should_update_weights(sport):
            return False
        
        # Calculate new weights
        new_weights = self.calculator.calculate_updated_weights(sport)
        
        # Validate weights
        if not self.validator.validate_weights(new_weights):
            logger.error(f"Invalid weights calculated for {sport}: {new_weights}")
            return False
        
        # Get current weights for comparison
        current_weights = self.get_current_weights(sport)
        
        # Check for significant changes
        weight_changes = self.calculate_weight_changes(current_weights, new_weights)
        
        # Log weight update
        self.log_weight_update(sport, current_weights, new_weights, weight_changes)
        
        # Apply new weights
        self.apply_new_weights(sport, new_weights)
        
        # Send notifications for significant changes
        if self.has_significant_changes(weight_changes):
            self.notify_weight_changes(sport, weight_changes)
        
        return True
    
    def log_weight_update(self, sport: str, old_weights: Dict, new_weights: Dict, changes: Dict):
        """Log weight update for audit trail"""
        update_record = {
            'PK': f'WEIGHT_UPDATE#{sport}',
            'SK': f'UPDATE#{datetime.utcnow().isoformat()}',
            'sport': sport,
            'old_weights': old_weights,
            'new_weights': new_weights,
            'weight_changes': changes,
            'update_timestamp': datetime.utcnow().isoformat(),
            'trigger_reason': self.get_update_trigger_reason(sport)
        }
        
        self.dynamodb.put_item(TableName='model-performance', Item=update_record)
```

## Performance Dashboard Data

### 1. Real-time Metrics API
```python
class PerformanceAPI:
    def get_model_dashboard_data(self, sport: str, timeframe: str = 'recent') -> Dict:
        """Get comprehensive dashboard data for models"""
        
        dashboard_data = {
            'sport': sport,
            'timeframe': timeframe,
            'last_updated': datetime.utcnow().isoformat(),
            'models': {},
            'ensemble_performance': {},
            'recent_predictions': [],
            'weight_history': [],
            'performance_trends': {}
        }
        
        # Individual model performance
        for model_name in self.get_active_models(sport):
            model_perf = self.aggregator.calculate_model_performance(model_name, sport)
            dashboard_data['models'][model_name] = {
                'current_weight': self.get_current_weight(model_name, sport),
                'performance': model_perf[timeframe],
                'recent_predictions': self.get_recent_predictions(model_name, sport, 10),
                'performance_trend': self.calculate_trend(model_name, sport),
                'status': self.get_model_status(model_name, sport)
            }
        
        # Ensemble performance
        dashboard_data['ensemble_performance'] = self.calculate_ensemble_performance(sport, timeframe)
        
        # Weight evolution
        dashboard_data['weight_history'] = self.get_weight_history(sport, days=30)
        
        return dashboard_data
    
    def get_calibration_data(self, model_name: str, sport: str) -> Dict:
        """Get calibration plot data"""
        analyses = self.get_model_analyses(model_name, sport, days=90)
        
        # Bin predictions by probability ranges
        bins = np.linspace(0, 1, 11)  # 10 bins
        calibration_data = []
        
        for i in range(len(bins) - 1):
            bin_start, bin_end = bins[i], bins[i + 1]
            
            # Get predictions in this bin
            bin_analyses = [
                a for a in analyses 
                if bin_start <= a['home_win_probability'] < bin_end
            ]
            
            if len(bin_analyses) > 0:
                avg_predicted = np.mean([a['home_win_probability'] for a in bin_analyses])
                avg_actual = np.mean([float(a['actual_home_won']) for a in bin_analyses])
                count = len(bin_analyses)
                
                calibration_data.append({
                    'bin_start': bin_start,
                    'bin_end': bin_end,
                    'avg_predicted': avg_predicted,
                    'avg_actual': avg_actual,
                    'count': count,
                    'perfect_calibration': (bin_start + bin_end) / 2
                })
        
        return {
            'calibration_points': calibration_data,
            'overall_calibration_error': self.calculate_overall_calibration_error(analyses),
            'calibration_slope': self.calculate_calibration_slope(analyses),
            'calibration_intercept': self.calculate_calibration_intercept(analyses)
        }
```

## Implementation Schedule

### Week 1: Foundation
- [ ] Implement outcome data collection system
- [ ] Create analysis storage schema
- [ ] Build basic performance calculation

### Week 2: Tracking System  
- [ ] Implement real-time performance tracker
- [ ] Create model performance aggregation
- [ ] Build performance monitoring & alerts

### Week 3: Weight Management
- [ ] Implement dynamic weight calculator
- [ ] Create weight update system
- [ ] Build weight validation & logging

### Week 4: Dashboard & API
- [ ] Create performance dashboard API
- [ ] Implement calibration analysis
- [ ] Build performance visualization data

## Success Metrics

### System Performance
- **Outcome Collection**: 99%+ accuracy in game result collection
- **Processing Latency**: < 5 minutes from game completion to metrics update
- **Data Integrity**: 100% consistency between sources
- **Alert Response**: < 1 hour for performance drift detection

### Model Evaluation
- **Calibration Quality**: Calibration error < 0.05 for well-performing models
- **Performance Tracking**: Track 10+ metrics per model per prediction
- **Weight Adaptation**: Weights update within 24 hours of performance changes
- **Drift Detection**: Identify performance drift within 48 hours

This comprehensive outcome verification and performance tracking system provides the foundation for bias-free model evaluation and continuous improvement of the 12-model ML analysis system.
