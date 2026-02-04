# ML Model Training & Weighting System Implementation

## Overview
Technical implementation specifications for training, evaluating, and weighting the 12-model ML analysis system. This document defines the complete pipeline from data preparation to model deployment.

## Model Training Pipeline

### 1. Data Preparation
```python
class DataPipeline:
    def prepare_training_data(self, sport: str, lookback_days: int = 365):
        """Prepare training data with proper temporal splits"""
        # Collect historical game outcomes (ground truth)
        outcomes = self.get_game_outcomes(sport, lookback_days)
        
        # Collect feature data for each model
        features = {}
        for model_type in self.MODEL_TYPES:
            features[model_type] = self.collect_model_features(
                model_type, sport, outcomes.game_ids
            )
        
        # Temporal split: 70% train, 15% validation, 15% test
        return self.temporal_split(outcomes, features)
```

### 2. Individual Model Training
```python
class ModelTrainer:
    def train_model(self, model_type: str, sport: str, train_data: Dict):
        """Train individual model with cross-validation"""
        
        # Model-specific architectures
        model_configs = {
            'management': {'type': 'gradient_boosting', 'max_depth': 6},
            'team_momentum': {'type': 'lstm', 'sequence_length': 10},
            'team_stats': {'type': 'random_forest', 'n_estimators': 100},
            'player_stats': {'type': 'xgboost', 'learning_rate': 0.1},
            'weather': {'type': 'linear_regression'},  # Simple for weather
            'player_life_events': {'type': 'neural_network', 'hidden_layers': [64, 32]},
            'public_opinion': {'type': 'transformer', 'attention_heads': 8},
            'market_inefficiency': {'type': 'isolation_forest'},  # Anomaly detection
            'referee_bias': {'type': 'logistic_regression'},
            'referee_decision': {'type': 'decision_tree', 'max_depth': 8},
            'referee_life_events': {'type': 'naive_bayes'},
            'historical_performance': {'type': 'gradient_boosting', 'max_depth': 8}
        }
        
        config = model_configs[model_type]
        model = self.create_model(config)
        
        # Time series cross-validation (respects temporal order)
        cv_scores = self.time_series_cv(model, train_data, n_splits=5)
        
        # Hyperparameter tuning
        best_params = self.hyperparameter_search(model, train_data)
        
        # Final training on full dataset
        final_model = self.train_final_model(model, train_data, best_params)
        
        return final_model, cv_scores
```

### 3. Model Evaluation Framework
```python
class ModelEvaluator:
    def evaluate_model(self, model, test_data: Dict) -> Dict[str, float]:
        """Comprehensive model evaluation"""
        predictions = model.predict_proba(test_data['features'])
        actual_outcomes = test_data['outcomes']
        
        metrics = {
            # Probability calibration
            'brier_score': self.brier_score(predictions, actual_outcomes),
            'log_loss': self.log_loss(predictions, actual_outcomes),
            'calibration_error': self.calibration_error(predictions, actual_outcomes),
            
            # Classification metrics
            'accuracy': self.accuracy(predictions > 0.5, actual_outcomes),
            'precision': self.precision(predictions > 0.5, actual_outcomes),
            'recall': self.recall(predictions > 0.5, actual_outcomes),
            'f1_score': self.f1_score(predictions > 0.5, actual_outcomes),
            
            # Financial metrics
            'roi': self.calculate_roi(predictions, actual_outcomes, test_data['odds']),
            'sharpe_ratio': self.sharpe_ratio(predictions, actual_outcomes, test_data['odds']),
            'max_drawdown': self.max_drawdown(predictions, actual_outcomes, test_data['odds']),
            
            # Confidence metrics
            'confidence_correlation': self.confidence_correlation(predictions, actual_outcomes),
            'overconfidence_ratio': self.overconfidence_ratio(predictions, actual_outcomes)
        }
        
        return metrics
    
    def minimum_performance_thresholds(self) -> Dict[str, float]:
        """Minimum thresholds for model inclusion"""
        return {
            'brier_score': 0.24,  # Better than random (0.25)
            'accuracy': 0.52,     # Better than coin flip
            'roi': 0.02,          # Positive expected value
            'calibration_error': 0.1  # Well-calibrated probabilities
        }
```

## Dynamic Weighting System

### 1. Weight Calculation Algorithm
```python
class DynamicWeightingSystem:
    def __init__(self):
        self.min_weight = 0.02  # 2% minimum
        self.max_weight = 0.25  # 25% maximum
        self.recency_factor = 0.7  # Weight recent performance more
        
    def calculate_model_weights(self, performance_history: Dict) -> Dict[str, float]:
        """Calculate dynamic weights based on performance"""
        weights = {}
        
        for model_name, history in performance_history.items():
            # Recent performance (last 30 predictions)
            recent_performance = self.calculate_recent_performance(history[-30:])
            
            # Overall performance (full history)
            overall_performance = self.calculate_overall_performance(history)
            
            # Situational performance (context-specific)
            situational_performance = self.calculate_situational_performance(history)
            
            # Weighted combination
            raw_weight = (
                recent_performance * 0.7 +
                overall_performance * 0.2 +
                situational_performance * 0.1
            )
            
            # Apply constraints
            weights[model_name] = max(self.min_weight, min(self.max_weight, raw_weight))
        
        # Normalize to sum to 1.0
        total_weight = sum(weights.values())
        return {k: v / total_weight for k, v in weights.items()}
    
    def calculate_recent_performance(self, recent_history: List[Dict]) -> float:
        """Calculate performance with exponential decay"""
        if not recent_history:
            return 0.5  # Neutral weight for new models
            
        weighted_score = 0
        total_weight = 0
        
        for i, result in enumerate(reversed(recent_history)):
            # Exponential decay: more recent = higher weight
            weight = self.recency_factor ** i
            score = self.performance_score(result)
            
            weighted_score += score * weight
            total_weight += weight
            
        return weighted_score / total_weight if total_weight > 0 else 0.5
    
    def performance_score(self, result: Dict) -> float:
        """Convert prediction result to performance score"""
        # Multi-metric scoring
        brier_component = max(0, 1 - (result['brier_score'] / 0.25))  # Normalized
        roi_component = max(0, min(1, result['roi'] / 0.1))  # Cap at 10% ROI
        calibration_component = max(0, 1 - (result['calibration_error'] / 0.2))
        
        return (brier_component * 0.4 + roi_component * 0.4 + calibration_component * 0.2)
```

### 2. Situational Weight Adjustments
```python
class SituationalWeighting:
    def adjust_weights_by_context(self, base_weights: Dict, game_context: Dict) -> Dict:
        """Adjust weights based on game situation"""
        adjusted_weights = base_weights.copy()
        
        # Weather model boost for outdoor games
        if game_context.get('venue_type') == 'outdoor' and game_context.get('sport') == 'nfl':
            adjusted_weights['weather'] *= 1.5
            
        # Referee models boost for playoff games
        if game_context.get('game_type') == 'playoff':
            adjusted_weights['referee_bias'] *= 1.3
            adjusted_weights['referee_decision'] *= 1.3
            
        # Momentum model boost during streaks
        if game_context.get('team_streak', 0) >= 3:
            adjusted_weights['team_momentum'] *= 1.4
            
        # Public opinion boost for high-profile games
        if game_context.get('tv_audience', 0) > 10_000_000:
            adjusted_weights['public_opinion'] *= 1.2
            
        # Market inefficiency boost for low-liquidity markets
        if game_context.get('betting_volume', 'high') == 'low':
            adjusted_weights['market_inefficiency'] *= 1.6
            
        # Normalize after adjustments
        total_weight = sum(adjusted_weights.values())
        return {k: v / total_weight for k, v in adjusted_weights.items()}
```

## Ensemble Prediction System

### 1. Weighted Ensemble
```python
class EnsemblePredictor:
    def __init__(self, models: Dict, weighting_system: DynamicWeightingSystem):
        self.models = models
        self.weighting_system = weighting_system
        
    def generate_ensemble_prediction(self, game_data: Dict) -> Dict:
        """Generate weighted ensemble prediction"""
        
        # Get individual model predictions
        model_predictions = {}
        model_confidences = {}
        
        for model_name, model in self.models.items():
            try:
                prediction = model.predict_proba(game_data)
                confidence = model.get_confidence(game_data)
                
                model_predictions[model_name] = prediction
                model_confidences[model_name] = confidence
                
            except Exception as e:
                # Handle model failures gracefully
                model_predictions[model_name] = 0.5  # Neutral prediction
                model_confidences[model_name] = 0.1  # Low confidence
        
        # Get current model weights
        weights = self.weighting_system.get_current_weights()
        
        # Adjust weights by situation
        situational_weights = self.weighting_system.adjust_weights_by_context(
            weights, game_data
        )
        
        # Calculate weighted prediction
        weighted_prediction = sum(
            pred * situational_weights[model_name] 
            for model_name, pred in model_predictions.items()
        )
        
        # Calculate ensemble confidence
        ensemble_confidence = self.calculate_ensemble_confidence(
            model_predictions, model_confidences, situational_weights
        )
        
        return {
            'prediction': weighted_prediction,
            'confidence': ensemble_confidence,
            'model_contributions': {
                model: pred * situational_weights[model] 
                for model, pred in model_predictions.items()
            },
            'weights_used': situational_weights
        }
    
    def calculate_ensemble_confidence(self, predictions: Dict, confidences: Dict, weights: Dict) -> float:
        """Calculate ensemble confidence considering model agreement"""
        
        # Weighted average confidence
        avg_confidence = sum(
            confidences[model] * weights[model] 
            for model in predictions.keys()
        )
        
        # Model agreement factor (higher agreement = higher confidence)
        prediction_values = list(predictions.values())
        agreement_factor = 1 - (np.std(prediction_values) / 0.5)  # Normalized std
        
        # Combined confidence
        ensemble_confidence = avg_confidence * agreement_factor
        
        return max(0.1, min(0.9, ensemble_confidence))
```

## Model Validation & Deployment

### 1. Validation Pipeline
```python
class ValidationPipeline:
    def validate_model_update(self, new_model, current_model, validation_data: Dict) -> bool:
        """Validate model before deployment"""
        
        # Performance comparison
        new_metrics = self.evaluator.evaluate_model(new_model, validation_data)
        current_metrics = self.evaluator.evaluate_model(current_model, validation_data)
        
        # Statistical significance test
        improvement_significant = self.statistical_significance_test(
            new_metrics, current_metrics, alpha=0.05
        )
        
        # Minimum performance thresholds
        meets_thresholds = all(
            new_metrics[metric] >= threshold 
            for metric, threshold in self.evaluator.minimum_performance_thresholds().items()
        )
        
        # Stability check (performance variance)
        stability_check = self.stability_test(new_model, validation_data)
        
        return improvement_significant and meets_thresholds and stability_check
    
    def a_b_test_framework(self, model_a, model_b, test_duration_days: int = 14):
        """A/B test framework for model comparison"""
        # Split traffic 50/50 between models
        # Track performance metrics
        # Statistical significance testing
        # Automatic rollback if performance degrades
        pass
```

### 2. Continuous Learning System
```python
class ContinuousLearning:
    def __init__(self):
        self.retrain_threshold = 0.05  # 5% performance drop triggers retrain
        self.min_new_samples = 100     # Minimum samples before retrain
        
    def monitor_model_drift(self, model_name: str, recent_performance: List[float]):
        """Monitor for model performance drift"""
        if len(recent_performance) < 30:
            return False
            
        # Compare recent vs historical performance
        recent_avg = np.mean(recent_performance[-30:])
        historical_avg = np.mean(recent_performance[:-30])
        
        performance_drop = historical_avg - recent_avg
        
        return performance_drop > self.retrain_threshold
    
    def trigger_model_retrain(self, model_name: str, new_data: Dict):
        """Trigger model retraining with new data"""
        # Incremental learning for compatible models
        # Full retrain for others
        # Validation before deployment
        # Gradual rollout with monitoring
        pass
```

## Performance Tracking & Monitoring

### 1. Real-time Monitoring
```python
class ModelMonitor:
    def track_prediction_performance(self, prediction_id: str, actual_outcome: bool):
        """Track individual prediction performance"""
        # Update model performance metrics
        # Trigger weight recalculation if needed
        # Alert on significant performance changes
        pass
    
    def generate_performance_report(self, timeframe: str = 'weekly') -> Dict:
        """Generate comprehensive performance report"""
        return {
            'individual_model_performance': self.get_model_metrics(),
            'ensemble_performance': self.get_ensemble_metrics(),
            'weight_evolution': self.get_weight_history(),
            'roi_analysis': self.get_roi_analysis(),
            'calibration_analysis': self.get_calibration_analysis()
        }
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Implement data pipeline and temporal splitting
- Build model training framework
- Create evaluation metrics system
- Develop basic weighting algorithm

### Phase 2: Model Development (Week 3-6)
- Train initial versions of all 12 models
- Implement ensemble prediction system
- Build validation pipeline
- Create A/B testing framework

### Phase 3: Production Deployment (Week 7-8)
- Deploy models to production
- Implement real-time monitoring
- Set up continuous learning pipeline
- Create performance dashboards

### Phase 4: Optimization (Week 9-12)
- Fine-tune model parameters
- Optimize weighting algorithms
- Implement advanced features
- Scale system for multiple sports

## Success Metrics

### Model-Level Metrics
- **Brier Score**: < 0.24 (better than random)
- **ROI**: > 2% on recommended bets
- **Calibration Error**: < 0.1
- **Accuracy**: > 52%

### System-Level Metrics
- **Ensemble ROI**: > 5% annually
- **Model Diversity**: No single model > 25% weight
- **Adaptation Speed**: Weight updates within 24 hours
- **Uptime**: > 99.5% availability

This comprehensive implementation framework provides the technical foundation for building, training, and deploying the 12-model ML analysis system with proper validation, monitoring, and continuous improvement capabilities.
