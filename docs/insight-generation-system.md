# Insight Generation & Confidence Scoring System

## Overview
This system generates actionable betting insights by combining model analyses, confidence scores, and expected value calculations to identify the highest-quality opportunities. It transforms raw model outputs into ranked, actionable recommendations.

## Insight Generation Pipeline

### 1. Analysis Aggregation
```python
class InsightGenerator:
    def __init__(self):
        self.ensemble_predictor = EnsemblePredictor()
        self.confidence_calculator = ConfidenceCalculator()
        self.value_calculator = ValueCalculator()
        self.risk_assessor = RiskAssessor()
        
    def generate_game_insights(self, game_data: Dict) -> List[Dict]:
        """Generate ranked insights for a single game"""
        
        # Get ensemble prediction
        ensemble_result = self.ensemble_predictor.generate_ensemble_prediction(game_data)
        
        # Calculate market inefficiencies
        market_analysis = self.analyze_market_inefficiencies(game_data, ensemble_result)
        
        # Generate potential insights
        potential_insights = []
        
        # Moneyline insights
        ml_insights = self.generate_moneyline_insights(game_data, ensemble_result, market_analysis)
        potential_insights.extend(ml_insights)
        
        # Spread insights
        spread_insights = self.generate_spread_insights(game_data, ensemble_result, market_analysis)
        potential_insights.extend(spread_insights)
        
        # Total insights
        total_insights = self.generate_total_insights(game_data, ensemble_result, market_analysis)
        potential_insights.extend(total_insights)
        
        # Player prop insights (if available)
        if game_data.get('player_props'):
            prop_insights = self.generate_prop_insights(game_data, ensemble_result)
            potential_insights.extend(prop_insights)
        
        # Score and rank insights
        scored_insights = self.score_insights(potential_insights)
        ranked_insights = self.rank_insights(scored_insights)
        
        # Apply filters and limits
        filtered_insights = self.apply_insight_filters(ranked_insights)
        
        return filtered_insights
    
    def generate_moneyline_insights(self, game_data: Dict, ensemble: Dict, market: Dict) -> List[Dict]:
        """Generate moneyline betting insights"""
        insights = []
        
        home_prob = ensemble['prediction']
        away_prob = 1 - home_prob
        confidence = ensemble['confidence']
        
        # Get best available odds
        home_odds = market['best_home_odds']
        away_odds = market['best_away_odds']
        
        # Calculate expected values
        home_ev = self.value_calculator.calculate_expected_value(home_prob, home_odds)
        away_ev = self.value_calculator.calculate_expected_value(away_prob, away_odds)
        
        # Home team insight
        if home_ev > 0.02:  # 2% minimum edge
            insights.append({
                'type': 'moneyline',
                'selection': 'home',
                'team': game_data['home_team'],
                'probability': home_prob,
                'odds': home_odds,
                'expected_value': home_ev,
                'confidence': confidence,
                'reasoning': self.generate_reasoning('moneyline_home', ensemble, market),
                'risk_level': self.assess_risk_level(home_prob, confidence, home_ev)
            })
        
        # Away team insight
        if away_ev > 0.02:
            insights.append({
                'type': 'moneyline',
                'selection': 'away', 
                'team': game_data['away_team'],
                'probability': away_prob,
                'odds': away_odds,
                'expected_value': away_ev,
                'confidence': confidence,
                'reasoning': self.generate_reasoning('moneyline_away', ensemble, market),
                'risk_level': self.assess_risk_level(away_prob, confidence, away_ev)
            })
        
        return insights
```

### 2. Confidence Scoring System
```python
class ConfidenceCalculator:
    def __init__(self):
        self.confidence_factors = {
            'model_agreement': 0.3,      # How much models agree
            'data_quality': 0.25,       # Completeness of input data
            'historical_accuracy': 0.2,  # Model track record in similar situations
            'market_efficiency': 0.15,   # How efficient is this market
            'sample_size': 0.1          # Amount of historical data
        }
    
    def calculate_insight_confidence(self, insight: Dict, ensemble_data: Dict, market_data: Dict) -> float:
        """Calculate comprehensive confidence score for an insight"""
        
        confidence_components = {}
        
        # Model agreement factor
        model_predictions = ensemble_data['model_contributions']
        agreement_score = self.calculate_model_agreement(model_predictions, insight['probability'])
        confidence_components['model_agreement'] = agreement_score
        
        # Data quality factor
        data_quality_score = self.assess_data_quality(insight, market_data)
        confidence_components['data_quality'] = data_quality_score
        
        # Historical accuracy factor
        historical_score = self.get_historical_accuracy_score(insight)
        confidence_components['historical_accuracy'] = historical_score
        
        # Market efficiency factor
        efficiency_score = self.assess_market_efficiency(market_data, insight)
        confidence_components['market_efficiency'] = efficiency_score
        
        # Sample size factor
        sample_score = self.assess_sample_size(insight)
        confidence_components['sample_size'] = sample_score
        
        # Weighted combination
        total_confidence = sum(
            score * self.confidence_factors[factor]
            for factor, score in confidence_components.items()
        )
        
        # Apply confidence bounds
        final_confidence = max(0.1, min(0.95, total_confidence))
        
        return {
            'confidence_score': final_confidence,
            'confidence_components': confidence_components,
            'confidence_level': self.categorize_confidence(final_confidence)
        }
    
    def calculate_model_agreement(self, model_predictions: Dict, final_probability: float) -> float:
        """Calculate how much models agree on the prediction"""
        predictions = list(model_predictions.values())
        
        # Standard deviation of predictions (lower = more agreement)
        std_dev = np.std(predictions)
        
        # Convert to agreement score (0-1, higher = more agreement)
        max_possible_std = 0.5  # Maximum possible std for probabilities
        agreement_score = 1 - (std_dev / max_possible_std)
        
        return max(0, min(1, agreement_score))
    
    def assess_data_quality(self, insight: Dict, market_data: Dict) -> float:
        """Assess quality and completeness of input data"""
        quality_factors = []
        
        # Odds availability across bookmakers
        odds_coverage = len(market_data.get('bookmaker_odds', {})) / 8  # Assume 8 target bookmakers
        quality_factors.append(min(1.0, odds_coverage))
        
        # Data freshness (how recent is the data)
        data_age_hours = market_data.get('data_age_hours', 24)
        freshness_score = max(0, 1 - (data_age_hours / 24))  # Decay over 24 hours
        quality_factors.append(freshness_score)
        
        # Market liquidity (betting volume)
        liquidity_score = self.assess_market_liquidity(market_data)
        quality_factors.append(liquidity_score)
        
        return np.mean(quality_factors)
    
    def categorize_confidence(self, confidence_score: float) -> str:
        """Categorize confidence into human-readable levels"""
        if confidence_score >= 0.8:
            return 'Very High'
        elif confidence_score >= 0.65:
            return 'High'
        elif confidence_score >= 0.5:
            return 'Medium'
        elif confidence_score >= 0.35:
            return 'Low'
        else:
            return 'Very Low'
```

### 3. Value Calculation System
```python
class ValueCalculator:
    def __init__(self):
        self.kelly_calculator = KellyCriterion()
        self.risk_adjuster = RiskAdjuster()
        
    def calculate_expected_value(self, true_probability: float, odds: int) -> float:
        """Calculate expected value of a bet"""
        decimal_odds = self.american_to_decimal(odds)
        implied_probability = 1 / decimal_odds
        
        # Expected value formula: (true_prob * (decimal_odds - 1)) - (1 - true_prob)
        expected_value = (true_probability * (decimal_odds - 1)) - (1 - true_probability)
        
        return expected_value
    
    def calculate_kelly_bet_size(self, true_probability: float, odds: int, bankroll: float) -> float:
        """Calculate optimal bet size using Kelly Criterion"""
        decimal_odds = self.american_to_decimal(odds)
        
        # Kelly formula: f = (bp - q) / b
        # where b = decimal_odds - 1, p = true_probability, q = 1 - p
        b = decimal_odds - 1
        p = true_probability
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # Apply conservative scaling (quarter Kelly)
        conservative_kelly = kelly_fraction * 0.25
        
        # Calculate bet amount
        bet_amount = bankroll * max(0, conservative_kelly)
        
        return {
            'kelly_fraction': kelly_fraction,
            'conservative_fraction': conservative_kelly,
            'bet_amount': bet_amount,
            'max_bet_percentage': min(0.05, conservative_kelly)  # Cap at 5% of bankroll
        }
    
    def calculate_risk_adjusted_value(self, insight: Dict) -> Dict:
        """Calculate risk-adjusted value metrics"""
        base_ev = insight['expected_value']
        confidence = insight['confidence']['confidence_score']
        probability = insight['probability']
        
        # Risk adjustments
        confidence_adjustment = confidence  # Scale by confidence
        probability_adjustment = self.probability_risk_adjustment(probability)
        market_adjustment = self.market_risk_adjustment(insight)
        
        # Combined risk adjustment
        risk_multiplier = confidence_adjustment * probability_adjustment * market_adjustment
        
        risk_adjusted_ev = base_ev * risk_multiplier
        
        return {
            'base_expected_value': base_ev,
            'risk_adjusted_expected_value': risk_adjusted_ev,
            'risk_multiplier': risk_multiplier,
            'confidence_adjustment': confidence_adjustment,
            'probability_adjustment': probability_adjustment,
            'market_adjustment': market_adjustment
        }
    
    def probability_risk_adjustment(self, probability: float) -> float:
        """Adjust for probability-based risk (extreme probabilities are riskier)"""
        # Penalize extreme probabilities (very high or very low)
        distance_from_center = abs(probability - 0.5)
        
        # Risk increases as we move away from 50/50
        risk_penalty = 1 - (distance_from_center * 0.5)  # Max 25% penalty
        
        return max(0.75, risk_penalty)
```

### 4. Insight Ranking System
```python
class InsightRanker:
    def __init__(self):
        self.ranking_weights = {
            'expected_value': 0.35,      # Primary factor
            'confidence': 0.25,         # How sure we are
            'risk_adjusted_value': 0.2,  # Risk consideration
            'market_inefficiency': 0.1,  # How wrong is the market
            'liquidity': 0.1            # Can we actually bet this
        }
    
    def rank_insights(self, insights: List[Dict]) -> List[Dict]:
        """Rank insights by composite score"""
        
        for insight in insights:
            # Calculate composite ranking score
            ranking_score = self.calculate_ranking_score(insight)
            insight['ranking_score'] = ranking_score
            insight['rank_components'] = ranking_score['components']
        
        # Sort by ranking score (descending)
        ranked_insights = sorted(insights, key=lambda x: x['ranking_score']['total_score'], reverse=True)
        
        # Add rank positions
        for i, insight in enumerate(ranked_insights):
            insight['rank'] = i + 1
            insight['tier'] = self.assign_tier(insight['ranking_score']['total_score'])
        
        return ranked_insights
    
    def calculate_ranking_score(self, insight: Dict) -> Dict:
        """Calculate composite ranking score"""
        components = {}
        
        # Expected value component (normalized)
        ev_score = min(1.0, max(0, insight['expected_value'] / 0.2))  # Cap at 20% EV
        components['expected_value'] = ev_score
        
        # Confidence component
        confidence_score = insight['confidence']['confidence_score']
        components['confidence'] = confidence_score
        
        # Risk-adjusted value component
        risk_adj_ev = insight.get('risk_adjusted_value', {}).get('risk_adjusted_expected_value', 0)
        risk_adj_score = min(1.0, max(0, risk_adj_ev / 0.15))  # Cap at 15% risk-adj EV
        components['risk_adjusted_value'] = risk_adj_score
        
        # Market inefficiency component
        market_score = self.calculate_market_inefficiency_score(insight)
        components['market_inefficiency'] = market_score
        
        # Liquidity component
        liquidity_score = self.calculate_liquidity_score(insight)
        components['liquidity'] = liquidity_score
        
        # Weighted total
        total_score = sum(
            components[factor] * self.ranking_weights[factor]
            for factor in components.keys()
        )
        
        return {
            'total_score': total_score,
            'components': components
        }
    
    def assign_tier(self, score: float) -> str:
        """Assign tier based on ranking score"""
        if score >= 0.8:
            return 'Elite'
        elif score >= 0.65:
            return 'Premium'
        elif score >= 0.5:
            return 'Standard'
        elif score >= 0.35:
            return 'Speculative'
        else:
            return 'Avoid'
```

### 5. Insight Filtering & Selection
```python
class InsightFilter:
    def __init__(self):
        self.filters = {
            'minimum_ev': 0.02,          # 2% minimum expected value
            'minimum_confidence': 0.3,    # 30% minimum confidence
            'maximum_risk': 0.8,         # Maximum risk level
            'minimum_liquidity': 0.4,    # Minimum market liquidity
            'maximum_insights_per_game': 3,  # Limit insights per game
            'tier_threshold': 'Standard'  # Minimum tier to include
        }
    
    def apply_filters(self, insights: List[Dict]) -> List[Dict]:
        """Apply quality filters to insights"""
        filtered_insights = []
        
        for insight in insights:
            if self.passes_filters(insight):
                filtered_insights.append(insight)
        
        # Apply per-game limits
        game_limited = self.apply_per_game_limits(filtered_insights)
        
        # Apply diversity requirements
        diversified = self.apply_diversity_requirements(game_limited)
        
        return diversified
    
    def passes_filters(self, insight: Dict) -> bool:
        """Check if insight passes all filters"""
        
        # Expected value filter
        if insight['expected_value'] < self.filters['minimum_ev']:
            return False
        
        # Confidence filter
        if insight['confidence']['confidence_score'] < self.filters['minimum_confidence']:
            return False
        
        # Risk filter
        if insight['risk_level'] > self.filters['maximum_risk']:
            return False
        
        # Tier filter
        tier_order = ['Avoid', 'Speculative', 'Standard', 'Premium', 'Elite']
        min_tier_index = tier_order.index(self.filters['tier_threshold'])
        insight_tier_index = tier_order.index(insight['tier'])
        
        if insight_tier_index < min_tier_index:
            return False
        
        return True
    
    def apply_diversity_requirements(self, insights: List[Dict]) -> List[Dict]:
        """Ensure diversity in insight types and games"""
        diversified = []
        
        # Track diversity metrics
        bet_types = set()
        games = set()
        teams = set()
        
        for insight in insights:
            # Check diversity constraints
            if len(bet_types) < 3 or insight['type'] not in bet_types:
                bet_types.add(insight['type'])
                
            if len(games) < 5 or insight['game_id'] not in games:
                games.add(insight['game_id'])
                
            if len(teams) < 8 or insight['team'] not in teams:
                teams.add(insight['team'])
                
            diversified.append(insight)
            
            # Stop when we have enough diverse insights
            if len(diversified) >= 10:
                break
        
        return diversified
```

### 6. Insight Presentation System
```python
class InsightPresenter:
    def format_insight_for_display(self, insight: Dict) -> Dict:
        """Format insight for user presentation"""
        
        return {
            'id': insight['id'],
            'rank': insight['rank'],
            'tier': insight['tier'],
            
            # Basic info
            'game': f"{insight['away_team']} @ {insight['home_team']}",
            'bet_type': insight['type'].title(),
            'selection': insight['selection_display'],
            'odds': self.format_odds(insight['odds']),
            
            # Key metrics
            'expected_value': f"{insight['expected_value']:.1%}",
            'confidence': insight['confidence']['confidence_level'],
            'confidence_score': f"{insight['confidence']['confidence_score']:.0%}",
            
            # Betting guidance
            'recommended_bet_size': insight['kelly_sizing']['max_bet_percentage'],
            'risk_level': insight['risk_level'],
            
            # Reasoning
            'key_factors': insight['reasoning']['key_factors'],
            'model_consensus': insight['reasoning']['model_consensus'],
            'market_analysis': insight['reasoning']['market_analysis'],
            
            # Metadata
            'generated_at': insight['generated_at'],
            'expires_at': insight['expires_at'],
            'data_freshness': insight['data_freshness']
        }
    
    def generate_insight_summary(self, insights: List[Dict]) -> Dict:
        """Generate summary of all insights"""
        
        if not insights:
            return {'message': 'No qualifying insights found'}
        
        return {
            'total_insights': len(insights),
            'tier_distribution': self.calculate_tier_distribution(insights),
            'avg_expected_value': np.mean([i['expected_value'] for i in insights]),
            'avg_confidence': np.mean([i['confidence']['confidence_score'] for i in insights]),
            'bet_type_distribution': self.calculate_bet_type_distribution(insights),
            'total_recommended_allocation': sum(i['kelly_sizing']['max_bet_percentage'] for i in insights),
            'top_insight': insights[0] if insights else None
        }
```

## Implementation Timeline

### Week 1: Core Generation
- [ ] Implement insight generation pipeline
- [ ] Create confidence calculation system
- [ ] Build value calculation framework

### Week 2: Ranking & Filtering
- [ ] Implement insight ranking system
- [ ] Create filtering and selection logic
- [ ] Build diversity requirements

### Week 3: Presentation & API
- [ ] Create insight presentation system
- [ ] Build insight API endpoints
- [ ] Implement real-time updates

### Week 4: Integration & Testing
- [ ] Integrate with ensemble prediction system
- [ ] Test with historical data
- [ ] Performance optimization

## Success Metrics

### Quality Metrics
- **Insight Accuracy**: >60% of insights should be profitable
- **Expected Value Realization**: Actual returns within 20% of expected
- **Confidence Calibration**: Confidence scores match actual success rates
- **Diversity**: Cover 3+ bet types, 5+ games daily

### User Experience
- **Response Time**: <2 seconds for insight generation
- **Update Frequency**: Real-time updates as odds change
- **Clarity**: 90%+ user comprehension of reasoning
- **Actionability**: Clear bet sizing and risk guidance

This insight generation system transforms raw model outputs into actionable, ranked betting opportunities with comprehensive confidence scoring and risk assessment.
