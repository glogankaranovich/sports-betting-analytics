# User-Defined Models MVP Design

**Last Updated:** February 3, 2026  
**Status:** Active Development

---

## MVP Scope

### What's Included
- ✅ Weight-based model configuration
- ✅ 5 pre-defined data sources
- ✅ Personal models only (no sharing)
- ✅ Basic performance tracking
- ✅ Simple slider-based UI

### What's Excluded (Future Phases)
- ❌ Custom code/formulas
- ❌ Custom data import
- ❌ Model marketplace
- ❌ Monetization
- ❌ Advanced backtesting

---

## Data Sources (MVP)

### 1. Team Stats
**What it measures:** Recent team performance metrics
- Offensive rating (points per 100 possessions)
- Defensive rating (points allowed per 100 possessions)
- Net rating (offensive - defensive)
- Lookback: Last 10 games

**Score calculation:** Compare to league average, normalize to 0-1

### 2. Odds Movement
**What it measures:** Line movement and sharp action
- Opening line vs current line
- Line movement magnitude
- Reverse line movement (sharp action indicator)
- Time window: Last 24 hours

**Score calculation:** Movement magnitude + sharp action bonus

### 3. Recent Form
**What it measures:** Win/loss streak and momentum
- Last 5 games record
- Point differential trend
- Home vs away splits

**Score calculation:** Win rate + point differential trend

### 4. Rest & Schedule
**What it measures:** Fatigue and travel factors
- Days of rest
- Back-to-back games
- Travel distance
- Home/away/neutral

**Score calculation:** Rest advantage + home court advantage

### 5. Head-to-Head
**What it measures:** Historical matchup performance
- Last 5 meetings
- Season series record
- Average point differential

**Score calculation:** Historical win rate + point differential

---

## Model Configuration Schema

```json
{
  "model_id": "user_abc123_model_001",
  "user_id": "abc123",
  "name": "My Momentum Model",
  "description": "Focuses on recent form and line movement",
  "sport": "basketball_nba",
  "bet_types": ["h2h", "spreads"],
  "data_sources": {
    "team_stats": {
      "enabled": true,
      "weight": 0.30
    },
    "odds_movement": {
      "enabled": true,
      "weight": 0.25
    },
    "recent_form": {
      "enabled": true,
      "weight": 0.25
    },
    "rest_schedule": {
      "enabled": true,
      "weight": 0.15
    },
    "head_to_head": {
      "enabled": false,
      "weight": 0.05
    }
  },
  "min_confidence": 0.60,
  "created_at": "2026-02-03T20:30:00Z",
  "updated_at": "2026-02-03T20:30:00Z",
  "status": "active"
}
```

---

## Scoring Algorithm

### Simple Weighted Average
```python
def calculate_prediction(model_config, game_data):
    """
    Calculate weighted score from enabled data sources
    Returns: (prediction, confidence)
    """
    total_score = 0
    total_weight = 0
    
    for source, config in model_config['data_sources'].items():
        if not config['enabled']:
            continue
        
        # Get normalized score (0-1) from data source
        score = evaluate_source(source, game_data)
        
        total_score += score * config['weight']
        total_weight += config['weight']
    
    # Normalize to 0-1
    confidence = total_score / total_weight if total_weight > 0 else 0
    
    # Apply minimum confidence threshold
    if confidence < model_config['min_confidence']:
        return None  # Skip low-confidence predictions
    
    # Determine prediction based on score
    if confidence > 0.55:
        prediction = "home_win"
    elif confidence < 0.45:
        prediction = "away_win"
    else:
        prediction = "no_bet"  # Too close to call
    
    return {
        "prediction": prediction,
        "confidence": confidence,
        "reasoning": generate_reasoning(model_config, game_data)
    }
```

---

## UI Design

### Model Builder Form

```
┌─────────────────────────────────────────┐
│  Create Your Model                      │
├─────────────────────────────────────────┤
│                                         │
│  Model Name: [________________]         │
│  Description: [________________]        │
│                                         │
│  Sport: [Basketball (NBA) ▼]           │
│  Bet Types: ☑ Moneyline ☑ Spread       │
│                                         │
│  ─── Data Sources ───                  │
│                                         │
│  ☑ Team Stats                          │
│     Weight: [━━━━━━━━━━] 30%          │
│                                         │
│  ☑ Odds Movement                       │
│     Weight: [━━━━━━━━━━] 25%          │
│                                         │
│  ☑ Recent Form                         │
│     Weight: [━━━━━━━━━━] 25%          │
│                                         │
│  ☑ Rest & Schedule                     │
│     Weight: [━━━━━━━━━━] 15%          │
│                                         │
│  ☐ Head-to-Head                        │
│     Weight: [━━━━━━━━━━] 5%           │
│                                         │
│  Total Weight: 100% ✓                  │
│                                         │
│  Min Confidence: [━━━━━━━━━━] 60%     │
│                                         │
│  [Cancel]  [Save Model]                │
└─────────────────────────────────────────┘
```

### Model List View

```
┌─────────────────────────────────────────┐
│  My Models                    [+ New]   │
├─────────────────────────────────────────┤
│                                         │
│  📊 My Momentum Model                  │
│     NBA • Moneyline, Spread            │
│     Accuracy: 58.3% (24/42)            │
│     [View] [Edit] [Delete]             │
│                                         │
│  📊 Conservative Value Model           │
│     NBA • Totals                       │
│     Accuracy: 61.5% (16/26)            │
│     [View] [Edit] [Delete]             │
│                                         │
└─────────────────────────────────────────┘
```

---

## Database Schema

### USER_MODEL Table
```
PK: USER#{user_id}
SK: MODEL#{model_id}

Attributes:
- model_id (string)
- user_id (string)
- name (string)
- description (string)
- sport (string)
- bet_types (list)
- data_sources (map)
- min_confidence (number)
- created_at (string)
- updated_at (string)
- status (string: active, archived)

GSI: UserModelsIndex
PK: USER#{user_id}
SK: CREATED#{created_at}
```

### MODEL_PREDICTION Table
```
PK: MODEL#{model_id}
SK: GAME#{game_id}#{timestamp}

Attributes:
- model_id (string)
- user_id (string)
- game_id (string)
- sport (string)
- prediction (string)
- confidence (number)
- reasoning (string)
- outcome (string: pending, correct, incorrect)
- created_at (string)

GSI: ModelPerformanceIndex
PK: MODEL#{model_id}
SK: OUTCOME#{outcome}#{timestamp}
```

---

## API Endpoints

### Model Management
```
POST   /user-models              - Create new model
GET    /user-models              - List user's models
GET    /user-models/{model_id}   - Get model details
PUT    /user-models/{model_id}   - Update model
DELETE /user-models/{model_id}   - Delete model
```

### Model Execution
```
POST   /user-models/{model_id}/run       - Generate predictions
GET    /user-models/{model_id}/predictions - Get recent predictions
GET    /user-models/{model_id}/performance - Get performance metrics
```

---

## Implementation Steps

### Step 1: Backend Schema (Day 1)
- Create USER_MODEL table
- Create MODEL_PREDICTION table
- Add GSIs for queries

### Step 2: API Endpoints (Day 2-3)
- Model CRUD operations
- Validation logic
- Error handling

### Step 3: Execution Engine (Day 4-5)
- Data source evaluators
- Scoring algorithm
- Prediction generation

### Step 4: Frontend UI (Day 6-8)
- Model builder form
- Model list view
- Weight sliders
- Validation

### Step 5: Integration (Day 9-10)
- Show user model predictions in analysis tabs
- Add "Custom" badge
- Filter by model type

### Step 6: Performance Tracking (Day 11-12)
- Track prediction outcomes
- Calculate accuracy metrics
- Display in UI

### Step 7: Testing & Deploy (Day 13-14)
- End-to-end testing
- Deploy to dev
- User acceptance testing

---

## Validation Rules

### Model Configuration
- ✅ Name: 3-50 characters
- ✅ Description: 10-200 characters
- ✅ At least 1 data source enabled
- ✅ Total weight = 100% (±1% tolerance)
- ✅ Min confidence: 50-95%
- ✅ Max 5 models per user (MVP limit)

### Data Source Weights
- ✅ Each weight: 0-100%
- ✅ Enabled sources must have weight > 0
- ✅ Disabled sources have weight = 0

---

## User Flow

### Creating a Model
1. Click "Create Model" button
2. Enter name and description
3. Select sport and bet types
4. Enable data sources
5. Adjust weights with sliders (auto-normalize to 100%)
6. Set minimum confidence threshold
7. Click "Save Model"
8. Model starts generating predictions on next scheduled run

### Viewing Predictions
1. Go to "Game Analysis" or "Prop Analysis" tab
2. Filter by "My Models"
3. See predictions with "Custom" badge
4. Click to see reasoning and data source breakdown

### Tracking Performance
1. Go to "My Models" page
2. See accuracy percentage for each model
3. Click "View Details" for breakdown by bet type
4. See recent predictions and outcomes

---

## Success Metrics

### Adoption
- Models created per user
- Active models (generating predictions)
- Models with >10 predictions

### Performance
- Average model accuracy
- Models beating system models
- User satisfaction with predictions

### Engagement
- Daily active model creators
- Predictions viewed per day
- Model edits/iterations

---

## Future Enhancements (Post-MVP)

### Phase 2: Advanced Features
- Custom confidence thresholds per data source
- Dynamic weighting based on recent performance
- Backtesting on historical data
- Model templates (starter configurations)

### Phase 3: Sharing
- Make models public (view-only)
- Model leaderboard
- Copy/fork other users' models

### Phase 4: Marketplace
- Paid subscriptions
- Revenue sharing
- Trial periods

---

## Questions & Decisions

### ✅ Decided
- Weight-based only (no code)
- 5 data sources for MVP
- Personal models only
- Max 5 models per user

### 🤔 To Decide
- Should weights auto-normalize or require manual adjustment?
  - **Decision:** Auto-normalize as user adjusts sliders
- How often to run user models?
  - **Decision:** Same schedule as system models (every 4 hours)
- Show predictions for all games or only high-confidence?
  - **Decision:** Only show predictions above min_confidence threshold

---

**Ready to implement!** Starting with DynamoDB schema next.
