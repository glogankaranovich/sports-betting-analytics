# Bet Recommendation Engine Design

## Overview
Convert ML predictions into actionable betting recommendations with proper risk management and bet sizing.

## Current State vs Target State

### Current State (Predictions Only)
- **GamePrediction**: `home_win_probability`, `away_win_probability`, `confidence_score`, `value_bets[]`
- **PlayerPropPrediction**: `over_probability`, `under_probability`, `confidence_score`, `value_bets[]`
- **Problem**: Just probabilities, no actionable "bet this" recommendations

### Target State (Actionable Recommendations)
- **BetRecommendation**: Specific bet with amount, reasoning, and risk level
- **Risk Management**: Conservative/Moderate/Aggressive options
- **Bet Sizing**: Kelly Criterion with risk multipliers
- **Value Filtering**: Only recommend bets with significant edge

## Architecture

### Core Components

#### 1. BetRecommendation Data Class
```python
@dataclass
class BetRecommendation:
    # Game/Bet Info
    game_id: str
    sport: str
    bet_type: str  # "home", "away", "over", "under"
    team_or_player: str
    market: str  # "moneyline", "spread", "total", "player_points"
    
    # Prediction Data
    predicted_probability: float
    confidence_score: float
    expected_value: float  # Edge over bookmaker
    
    # Recommendation Data
    risk_level: RiskLevel
    recommended_bet_amount: float
    potential_payout: float
    bookmaker: str
    odds: float
    
    # User Understanding
    reasoning: str
```

#### 2. Risk Levels
```python
class RiskLevel(Enum):
    CONSERVATIVE = "conservative"  # 15% edge required, 25% Kelly
    MODERATE = "moderate"          # 10% edge required, 50% Kelly  
    AGGRESSIVE = "aggressive"      # 5% edge required, 100% Kelly
```

#### 3. BetRecommendationEngine
- **Input**: Predictions + Odds Data
- **Output**: List of BetRecommendation objects
- **Logic**: Kelly Criterion + Risk Management + Value Filtering

## Default Configuration

### Bankroll Management
- **Default Bankroll**: $1000 (configurable later for users)
- **Bet Limits**: Min $5, Max $100 per bet
- **Kelly Cap**: Maximum 25% of bankroll on any single bet

### Risk Level Settings
| Risk Level | Min Edge Required | Kelly Multiplier | Description |
|------------|------------------|------------------|-------------|
| Conservative | 15% | 25% | High confidence, small bets |
| Moderate | 10% | 50% | Balanced risk/reward |
| Aggressive | 100% | 5% | Higher risk, full Kelly |

### Bet Sizing Formula
```
Kelly Fraction = (p * decimal_odds - 1) / (decimal_odds - 1)
Adjusted Fraction = Kelly Fraction * Risk Multiplier
Bet Amount = Bankroll * Adjusted Fraction (capped at limits)
```

## User Experience Flow

### 1. Top Recommendation Display
- Show **one** top recommendation prominently on dashboard
- Default to **Moderate** risk level
- Include: Team/Player, Bet Amount, Potential Payout, Reasoning

### 2. All Recommendations View
- Show **all** recommendations grouped by risk level
- Allow filtering by sport, market type, confidence
- Sort by expected value * confidence (risk-adjusted EV)

### 3. Recommendation Details
- Full reasoning with model confidence
- Bookmaker comparison (why this bookmaker was chosen)
- Expected value calculation breakdown
- Risk level explanation

## Implementation Plan

### Phase 1: Core Engine
1. Create `BetRecommendation` dataclass
2. Implement `BetRecommendationEngine` class
3. Add methods to convert predictions → recommendations
4. Unit tests for recommendation logic

### Phase 2: API Integration
1. Add `/recommendations` API endpoint
2. Add `/top-recommendation` API endpoint  
3. Integrate with existing prediction pipeline
4. Update API handler with new endpoints

### Phase 3: Frontend Integration
1. Create `TopRecommendation` React component
2. Add recommendations tab to main interface
3. Display risk level options and explanations
4. Add bet tracking (future: track if user follows recommendations)

## Future Enhancements

### User Customization
- Custom bankroll amounts
- Personal risk preferences
- Bet size limits
- Favorite sports/markets

### Advanced Features
- Multi-bet parlays with correlation analysis
- Bankroll tracking and performance metrics
- Model performance comparison
- Historical recommendation tracking

## Example Output

```json
{
  "game_id": "nfl_game_123",
  "sport": "americanfootball_nfl", 
  "bet_type": "home",
  "team_or_player": "Kansas City Chiefs",
  "market": "moneyline",
  "predicted_probability": 0.65,
  "confidence_score": 0.78,
  "expected_value": 0.18,
  "risk_level": "moderate",
  "recommended_bet_amount": 25.50,
  "potential_payout": 47.25,
  "bookmaker": "betmgm",
  "odds": -120,
  "reasoning": "78% confidence, 18% edge over bookmaker. Model predicts 65% chance vs 55% implied."
}
```

This creates a clear path from "Chiefs have 65% win probability" to "Bet $25.50 on Chiefs at BetMGM for $47.25 potential payout."
