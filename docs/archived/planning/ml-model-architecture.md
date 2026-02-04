# ML Model Architecture Design

## Model Overview
**Objective**: Predict game outcomes and identify value bets using betting odds data

## Model Inputs
- **Odds Data**: Moneyline, spread, totals from multiple bookmakers
- **Implied Probabilities**: Calculated from odds
- **Bookmaker Consensus**: Average odds across all bookmakers
- **Odds Movement**: Changes over time (future enhancement)

## Model Outputs
- **Win Probability**: 0-1 probability for each team
- **Confidence Score**: Model certainty (0-1)
- **Value Bet Flag**: Boolean indicating if bet offers value
- **Expected Value**: Calculated EV for each bet

## Architecture Components

### 1. Data Preprocessing Pipeline
```python
class OddsPreprocessor:
    def calculate_implied_probability(self, odds)
    def normalize_bookmaker_data(self, raw_odds)
    def detect_consensus(self, bookmaker_odds)
```

### 2. Feature Engineering
- Convert American odds to decimal/implied probability
- Calculate bookmaker consensus (mean, median, std dev)
- Identify outlier bookmakers
- Generate market efficiency metrics

### 3. Model Types (Phase 1)
**Simple Consensus Model**: Use bookmaker consensus as baseline
- Input: Multiple bookmaker odds
- Output: Weighted average probability
- Logic: More bookmakers agreeing = higher confidence

### 4. Value Detection Algorithm
```python
def detect_value_bet(model_probability, bookmaker_odds):
    implied_prob = 1 / decimal_odds
    if model_probability > implied_prob:
        return True, calculate_expected_value()
    return False, 0
```

## Implementation Plan
1. Create `ml/` directory with model modules
2. Build odds preprocessing pipeline
3. Implement consensus model
4. Add value detection logic
5. Create prediction API endpoints

## Data Flow
```
Raw Odds → Preprocessing → Feature Engineering → Model → Predictions → API
```
