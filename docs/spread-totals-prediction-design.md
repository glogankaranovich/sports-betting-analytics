# Spread and Totals Prediction Implementation Plan

## Current State
- **Implemented**: Moneyline (h2h) predictions using consensus probability analysis
- **Missing**: Spread and totals predictions require different modeling approaches

## Implementation Approach

### 1. Data Structure Changes

#### New Prediction Classes
```python
@dataclass
class SpreadPrediction:
    game_id: str
    home_team: str
    away_team: str
    predicted_margin: float  # Positive = home team wins by X
    spread_line: float       # Current market spread
    cover_probability: float # Probability favorite covers spread
    confidence_score: float
    bookmaker_count: int
    model_version: str

@dataclass
class TotalsPrediction:
    game_id: str
    home_team: str
    away_team: str
    predicted_total: float   # Combined score prediction
    posted_total: float      # Market over/under line
    over_probability: float  # Probability total goes over
    confidence_score: float
    bookmaker_count: int
    model_version: str
```

### 2. Model Enhancement Strategy

#### Option A: Consensus-Based (Easier)
- Analyze spread odds across bookmakers to infer market expectations
- Use consensus implied probabilities for spread coverage
- Similar approach for totals using over/under odds

**Data Requirements:**
- Current spread lines from multiple bookmakers
- Spread odds (both sides) for each bookmaker
- Over/under totals lines from multiple bookmakers  
- Over/under odds for each bookmaker
- Historical spread/totals accuracy for confidence scoring

#### Option B: Predictive Modeling (More Advanced)
- Build models to predict actual game scores
- Requires additional data sources:
  - Team offensive/defensive efficiency ratings
  - Pace of play statistics
  - Recent form and trends
  - Injury reports
  - Historical matchup data

**Data Requirements:**
- **Team Statistics:**
  - Points per game (offensive efficiency)
  - Points allowed per game (defensive efficiency)
  - Field goal percentage, 3-point percentage
  - Rebounds, assists, turnovers per game
  - Pace of play (possessions per game)
  
- **Advanced Metrics:**
  - Offensive/Defensive rating (points per 100 possessions)
  - Effective field goal percentage
  - True shooting percentage
  - Net rating (offensive - defensive rating)
  
- **Situational Data:**
  - Home/away performance splits
  - Rest days between games (back-to-back impact)
  - Recent form (last 5-10 games performance)
  - Head-to-head historical results and scoring
  
- **External Factors:**
  - Injury reports and player availability
  - Weather conditions (for outdoor sports)
  - Referee assignments and their tendencies
  - Motivation factors (playoff implications, rivalry games)
  
- **Historical Data:**
  - Season-long trends and patterns
  - Performance against similar opponents
  - Scoring trends over time (early season vs late season)
  - Performance in different game situations (close games, blowouts)

### 3. Database Schema Updates

#### DynamoDB Changes
```python
# Spread predictions
PK: "SPREAD_PREDICTION#{game_id}"
SK: "SPREAD#{model}#{timestamp}"

# Totals predictions  
PK: "TOTALS_PREDICTION#{game_id}"
SK: "TOTALS#{model}#{timestamp}"
```

### 4. API Endpoints

#### New Routes
- `GET /spread-predictions` - Get spread predictions
- `GET /totals-predictions` - Get totals predictions
- `GET /predictions/{game_id}` - Get all prediction types for a game

### 5. Frontend Integration

#### UI Components
- Spread predictions tab showing cover probabilities
- Totals predictions tab showing over/under recommendations
- Combined predictions view for complete game analysis

### 6. Implementation Steps

1. **Phase 1**: Extend data collection to capture spread/totals odds
2. **Phase 2**: Implement consensus-based spread/totals analysis
3. **Phase 3**: Create new prediction classes and database schema
4. **Phase 4**: Build API endpoints for new prediction types
5. **Phase 5**: Add frontend components for spread/totals display
6. **Phase 6**: (Future) Advanced predictive modeling with external data

### 7. Technical Considerations

#### Challenges
- Spread lines vary between bookmakers (need to handle multiple lines)
- Totals can have different values across books
- More complex validation (need actual final scores + margins)
- Requires more sophisticated confidence scoring

#### Benefits
- More comprehensive betting analysis
- Additional revenue opportunities
- Better user engagement with multiple bet types
- Competitive advantage over moneyline-only systems

### 8. Success Metrics

- Spread prediction accuracy (% of correct covers)
- Totals prediction accuracy (% of correct over/under)
- User engagement with new prediction types
- ROI improvement from diversified bet recommendations

## Next Steps

1. **Data Requirements Assessment**
   - Evaluate current data sources vs requirements for each approach
   - Identify external APIs needed for advanced modeling (ESPN, NBA.com, etc.)
   - Estimate costs for premium sports data subscriptions
   - Plan data pipeline architecture for real-time updates

2. Decide between consensus vs predictive modeling approach
3. Design detailed data structures and API contracts
4. Plan database migration for new prediction types
5. Implement in development environment
6. Test with historical data before production deployment

## Data Source Considerations

### Current Available Data
- ✅ Betting odds from The Odds API (moneyline, spreads, totals)
- ✅ Basic game information (teams, start times)
- ✅ Bookmaker consensus analysis capability

### Additional Data Sources Needed
- **Free Options:**
  - ESPN API (basic team stats)
  - NBA.com stats API (advanced metrics)
  - Sports Reference (historical data)
  
- **Premium Options:**
  - SportsRadar API (comprehensive real-time data)
  - Sportradar (injury reports, player props)
  - The Athletic API (insider information)
  
- **Cost Considerations:**
  - Free APIs: Rate limited, basic data only
  - Premium APIs: $100-1000+/month depending on usage
  - Real-time vs delayed data pricing tiers

## Related Files
- `backend/ml/models.py` - Current moneyline model implementation
- `backend/prediction_tracker.py` - Prediction generation logic
- `frontend/src/components/` - UI components for predictions display
