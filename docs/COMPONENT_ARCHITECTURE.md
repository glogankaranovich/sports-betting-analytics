# Component Architecture - Detailed Documentation

## Table of Contents
1. [Data Collection Components](#data-collection-components)
2. [Analysis & Prediction Components](#analysis--prediction-components)
3. [User Models System](#user-models-system)
4. [Benny Trading Agent](#benny-trading-agent)
5. [Performance Tracking](#performance-tracking)
6. [API Layer](#api-layer)

---

## Data Collection Components

### Odds Collector

**File:** `backend/odds_collector.py`

**Purpose:** Fetches and stores betting odds from The Odds API

**Schedule:** Every 4 hours (EventBridge)

**Process:**
1. Query The Odds API for each sport
2. For each game:
   - Extract game metadata (teams, commence time)
   - Extract odds for each bookmaker
   - Store in DynamoDB with composite keys
3. Mark latest odds with `latest=true`
4. Deduplicate using game_id + bookmaker + market_key

**DynamoDB Schema:**
```
PK: GAME#{game_id}
SK: {bookmaker}#{market_key}#{timestamp}
GSI1PK: GAME#{sport}
GSI1SK: {commence_time}
active_bet_pk: GAME#{sport} (for ActiveBetsIndexV2)
latest: true/false
```

**Key Features:**
- Supports 5 sports: NBA, NFL, MLB, NHL, EPL
- Tracks 3 market types: h2h, spreads, totals
- Stores historical odds for trend analysis
- Efficient querying via GSIs

---

### Outcome Collector

**File:** `backend/outcome_collector.py`

**Purpose:** Collects game results and verifies predictions

**Schedule:** Every 4 hours (EventBridge)

**Process:**
1. Fetch completed games from Odds API (last 3 days)
2. For each completed game:
   - Store game outcome (winner, scores)
   - Store team-specific outcomes (2 per game)
   - Query all predictions for this game
   - Verify original predictions
   - Verify inverse predictions
   - Settle Benny bets
   - Update Benny bankroll

**DynamoDB Schema:**
```
# Main outcome
PK: OUTCOME#{sport}#{game_id}
SK: RESULT

# Team outcomes (for recent form)
PK: TEAM_OUTCOME#{sport}#{team}
SK: {timestamp}#{game_id}
team_outcome_pk: TEAM#{sport}#{team} (for TeamOutcomesIndex)
```

**Bet Settlement Logic:**
```python
if bet_won:
    if odds > 0:
        profit = bet_amount * odds / 100
    else:
        profit = bet_amount / (abs(odds) / 100)
    payout = bet_amount + profit
else:
    payout = 0
    profit = -bet_amount
```

**Team Name Matching:**
- Full name match
- Normalized match (last word)
- Partial match
- Logs warnings for unmatched predictions

---

## Analysis & Prediction Components

### Analysis Generator

**File:** `backend/analysis_generator.py`

**Purpose:** Generates predictions for all models

**Schedule:** Every 4-6 hours (EventBridge)

**Process:**
1. Query upcoming games (next 3 hours)
2. For each model:
   - Analyze game using model-specific logic
   - Generate base prediction + confidence
   - Apply dynamic confidence adjustment
   - Store original prediction
   - Generate and store inverse prediction
3. Store one record per bookmaker

**Models Processed:**
- consensus, value, momentum, contrarian
- hot_cold, rest_schedule, matchup, injury_aware
- ensemble, benny

**Confidence Adjustment:**
```python
# Check cache first
cached = get_cached_adjustment(model, sport)
if cached:
    adjusted = base_confidence * cached['confidence_multiplier']
else:
    # Calculate from scratch
    accuracy = get_recent_accuracy(model, sport)
    inverse_accuracy = get_recent_accuracy(model, sport, inverse=True)
    
    if inverse_accuracy > accuracy and inverse_accuracy > 0.5:
        multiplier = 0.3  # Heavily penalize
    elif accuracy < 0.5:
        multiplier = accuracy  # Direct scaling
    elif accuracy > 0.6:
        multiplier = 1.0 + (accuracy - 0.6) * 0.5  # Boost
    else:
        multiplier = 0.8 + (accuracy - 0.5) * 2  # Slight reduction
    
    adjusted = base_confidence * multiplier
```

**Inverse Prediction Generation:**
```python
def create_inverse_prediction(analysis):
    if analysis_type == "game":
        # Flip the team
        if home_team in prediction:
            inverse_prediction = away_team
        else:
            inverse_prediction = home_team
    elif analysis_type == "prop":
        # Flip over/under
        if "over" in prediction:
            inverse_prediction = prediction.replace("Over", "Under")
        else:
            inverse_prediction = prediction.replace("Under", "Over")
    
    inverse_confidence = 1.0 - original_confidence
    return inverse_prediction, inverse_confidence
```

---

### System Models

**File:** `backend/ml/models.py`

**Base Class:** `BaseAnalysisModel`

**Model Implementations:**

#### 1. ConsensusModel
- **Logic:** Averages odds across all bookmakers
- **Prediction:** Team with better average odds
- **Confidence:** Based on odds consensus strength

#### 2. ValueModel
- **Logic:** Finds discrepancies between bookmakers
- **Prediction:** Team with best value (highest odds variance)
- **Confidence:** Based on odds standard deviation

#### 3. MomentumModel
- **Logic:** Recent team performance (last 5 games)
- **Prediction:** Team with better recent record
- **Confidence:** Based on win streak and margin

#### 4. ContrarianModel
- **Logic:** Bets against public consensus
- **Prediction:** Opposite of consensus pick
- **Confidence:** Inverse of consensus confidence

#### 5. HotColdModel
- **Logic:** Identifies hot/cold streaks
- **Prediction:** Hot team over cold team
- **Confidence:** Based on streak length

#### 6. RestScheduleModel
- **Logic:** Back-to-back game analysis
- **Prediction:** Rested team over tired team
- **Confidence:** Based on rest differential

#### 7. MatchupModel
- **Logic:** Head-to-head history
- **Prediction:** Team with better H2H record
- **Confidence:** Based on H2H sample size

#### 8. InjuryAwareModel
- **Logic:** Adjusts for player injuries
- **Prediction:** Team with fewer/less impactful injuries
- **Confidence:** Based on injury severity

#### 9. EnsembleModel
- **Logic:** Combines multiple models
- **Prediction:** Weighted average of all models
- **Confidence:** Consensus of model confidences

---

### Dynamic Weighting System

**File:** `backend/ml/dynamic_weighting.py`

**Class:** `DynamicModelWeighting`

**Key Methods:**

```python
def get_recent_accuracy(model, sport, bet_type, inverse=False):
    """Query last 30 days of verified predictions"""
    verified_pk = f"VERIFIED#{model}#{sport}#{bet_type}"
    if inverse:
        verified_pk += "#inverse"
    
    # Query VerifiedAnalysisGSI
    analyses = query_verified_analyses(verified_pk, cutoff_date)
    correct = sum(1 for a in analyses if a['analysis_correct'])
    return correct / len(analyses)

def calculate_adjusted_confidence(base_confidence, model, sport):
    """Adjust confidence based on performance"""
    # Try cache first (24 hour TTL)
    cached = get_cached_adjustment(model, sport)
    if cached:
        return base_confidence * cached['confidence_multiplier']
    
    # Calculate from scratch
    accuracy = get_recent_accuracy(model, sport)
    inverse_accuracy = get_recent_accuracy(model, sport, inverse=True)
    
    # Determine multiplier
    multiplier = calculate_multiplier(accuracy, inverse_accuracy)
    return min(base_confidence * multiplier, 1.0)

def store_model_adjustments(sport, bet_type):
    """Calculate and store adjustments for all models"""
    for model in all_models:
        recommendation = get_model_recommendation(model, sport)
        
        # Store in DynamoDB
        table.put_item({
            'pk': f'MODEL_ADJUSTMENT#{sport}#{bet_type}',
            'sk': model,
            'recommendation': recommendation,  # ORIGINAL/INVERSE/AVOID
            'confidence_multiplier': multiplier,
            'original_accuracy': accuracy,
            'inverse_accuracy': inverse_accuracy,
            'updated_at': now
        })
```

---

## User Models System

### User Model Structure

**File:** `backend/user_models.py`

**Class:** `UserModel`

**Configuration:**
```python
{
    'user_id': str,
    'model_id': str,
    'name': str,
    'sport': str,
    'bet_types': ['h2h', 'spreads', 'totals'],
    'data_sources': {
        'team_stats': 0.3,        # Weight: 0-1
        'odds_movement': 0.2,
        'injuries': 0.2,
        'recent_form': 0.2,
        'head_to_head': 0.1
    },
    'min_confidence': 0.6,        # Threshold for predictions
    'status': 'active',           # active/paused
    'created_at': timestamp,
    'updated_at': timestamp
}
```

**Data Source Evaluators:**

#### 1. Team Stats
```python
def evaluate_team_stats(game_data):
    # Query recent stats for both teams
    home_stats = get_team_stats(home_team)
    away_stats = get_team_stats(away_team)
    
    # Calculate composite score
    home_score = (
        0.4 * (home_fg_pct / (home_fg_pct + away_fg_pct)) +
        0.3 * (home_3pt_pct / (home_3pt_pct + away_3pt_pct)) +
        0.3 * (home_reb / (home_reb + away_reb))
    )
    
    return home_score  # 0-1 (>0.5 favors home)
```

#### 2. Odds Movement
```python
def evaluate_odds_movement(game_data):
    # Query historical odds for this game
    odds_history = get_odds_history(game_id)
    
    # Compare opening vs current lines
    opening_line = odds_history[0]
    current_line = odds_history[-1]
    
    # Detect sharp action
    if current_line moved significantly:
        return direction_of_movement
    
    return 0.5  # Neutral
```

#### 3. Injuries
```python
def evaluate_injuries(game_data):
    home_injuries = get_injuries(home_team)
    away_injuries = get_injuries(away_team)
    
    # Weight by player importance
    home_impact = sum(injury['impact'] for injury in home_injuries)
    away_impact = sum(injury['impact'] for injury in away_injuries)
    
    # More injuries = lower score
    return 1 - (home_impact / (home_impact + away_impact + 1))
```

#### 4. Recent Form
```python
def evaluate_recent_form(game_data):
    # Query last 5 games via TeamOutcomesIndex
    home_form = get_recent_form(home_team)  # e.g., "4-1"
    away_form = get_recent_form(away_team)  # e.g., "2-3"
    
    home_wins = home_form['wins']
    away_wins = away_form['wins']
    
    return home_wins / (home_wins + away_wins)
```

#### 5. Head-to-Head
```python
def evaluate_head_to_head(game_data):
    # Query H2H history
    h2h_games = get_h2h_history(home_team, away_team)
    
    home_wins = sum(1 for g in h2h_games if g['winner'] == home_team)
    
    return home_wins / len(h2h_games) if h2h_games else 0.5
```

**Prediction Generation:**
```python
def generate_prediction(user_model, game_data):
    # Evaluate each data source
    scores = {}
    for source, weight in user_model.data_sources.items():
        scores[source] = evaluate_source(source, game_data) * weight
    
    # Weighted average
    final_score = sum(scores.values())
    
    # Determine prediction
    if final_score > 0.5:
        prediction = home_team
        confidence = final_score
    else:
        prediction = away_team
        confidence = 1 - final_score
    
    # Check threshold
    if confidence >= user_model.min_confidence:
        return prediction, confidence
    else:
        return None  # Don't predict
```

---

### User Model Executor

**File:** `backend/user_model_executor.py`

**Purpose:** Processes user models from SQS queue

**Process:**
1. Receive message from SQS
2. Load user model configuration
3. Query upcoming games
4. For each game:
   - Evaluate all data sources
   - Calculate weighted score
   - Generate prediction if above threshold
   - Store in DynamoDB
5. Delete message from queue

**SQS Integration:**
```python
def lambda_handler(event, context):
    for record in event['Records']:
        message = json.loads(record['body'])
        user_model_id = message['user_model_id']
        
        # Load model
        user_model = UserModel.get(user_model_id)
        
        # Generate predictions
        predictions = generate_predictions(user_model)
        
        # Store predictions
        for prediction in predictions:
            store_prediction(prediction)
        
        # Delete message
        sqs.delete_message(record['receiptHandle'])
```

---

## Benny Trading Agent

### Benny Trader

**File:** `backend/benny_trader.py`

**Class:** `BennyTrader`

**Configuration:**
```python
WEEKLY_BUDGET = $100
MIN_CONFIDENCE = 0.65
MAX_BET_PERCENTAGE = 0.20  # Max 20% of bankroll per bet
```

**Trading Process:**

#### 1. Game Analysis
```python
def analyze_games():
    # Query upcoming games (next 24 hours)
    games = get_upcoming_games()
    
    opportunities = []
    for game in games:
        # Gather data
        odds = get_average_odds(game)
        home_stats = get_team_stats(home_team)
        away_stats = get_team_stats(away_team)
        injuries = get_injuries(both_teams)
        h2h = get_h2h_history(teams)
        form = get_recent_form(both_teams)
        
        # AI analysis
        analysis = ai_analyze_game(game, all_data)
        
        if analysis['confidence'] >= MIN_CONFIDENCE:
            opportunities.append({
                'game_id': game_id,
                'prediction': analysis['prediction'],
                'confidence': analysis['confidence'],
                'reasoning': analysis['reasoning'],
                'odds': predicted_team_odds
            })
    
    return opportunities
```

#### 2. AI Analysis (Claude 3.5 Sonnet)
```python
def ai_analyze_game(game_data, stats, injuries, h2h, form):
    prompt = f"""
    You are Benny, an expert sports betting analyst.
    
    Game: {away_team} @ {home_team}
    
    ODDS:
    Home: {home_odds} ({home_prob:.1%} implied)
    Away: {away_odds} ({away_prob:.1%} implied)
    
    TEAM STATS: {stats}
    RECENT FORM: {form}
    HEAD-TO-HEAD: {h2h}
    INJURIES: {injuries}
    
    Analyze and predict:
    1. Which team wins and why?
    2. Is there value vs the odds?
    3. Key factors driving your prediction?
    
    Respond with JSON:
    {
        "prediction": "Team Name",
        "confidence": 0.75,
        "reasoning": "Brief explanation",
        "key_factors": ["factor1", "factor2", "factor3"]
    }
    """
    
    response = bedrock.invoke_model(
        modelId="claude-3-5-sonnet",
        body={"messages": [{"role": "user", "content": prompt}]}
    )
    
    return parse_json_response(response)
```

#### 3. Bet Sizing (Kelly Criterion)
```python
def calculate_bet_size(confidence):
    # Convert American odds to decimal
    decimal_odds = american_to_decimal(odds)
    
    # Kelly Criterion
    win_prob = confidence
    kelly_fraction = (decimal_odds * win_prob - 1) / (decimal_odds - 1)
    
    # Half Kelly for safety
    bet_size = bankroll * kelly_fraction * 0.5
    
    # Apply constraints
    max_bet = bankroll * MAX_BET_PERCENTAGE
    bet_size = min(bet_size, max_bet)
    bet_size = max(bet_size, 5.00)  # Minimum $5
    
    return bet_size
```

#### 4. Bet Placement
```python
def place_bet(opportunity):
    bet_size = calculate_bet_size(opportunity['confidence'])
    
    # Check bankroll
    if bet_size > bankroll:
        return {'success': False, 'reason': 'Insufficient bankroll'}
    
    # Store bet
    bet = {
        'pk': 'BENNY',
        'sk': f"BET#{timestamp}#{game_id}",
        'game_id': game_id,
        'prediction': opportunity['prediction'],
        'confidence': opportunity['confidence'],
        'bet_amount': bet_size,
        'odds': opportunity['odds'],
        'status': 'pending',
        'placed_at': timestamp
    }
    table.put_item(bet)
    
    # Store as analysis for verification
    analysis = {
        'pk': f"ANALYSIS#{sport}#{game_id}#fanduel",
        'sk': 'benny#game#LATEST',
        'model': 'benny',
        'prediction': opportunity['prediction'],
        'confidence': opportunity['confidence'],
        'latest': True
    }
    table.put_item(analysis)
    
    # Update bankroll
    bankroll -= bet_size
    update_bankroll(bankroll)
    
    return {'success': True, 'bet_id': bet_id}
```

#### 5. Bet Settlement (in Outcome Collector)
```python
def settle_benny_bets(game):
    # Query pending bets
    bets = query_benny_bets(game_id, status='pending')
    
    for bet in bets:
        # Determine if won
        bet_won = check_bet_outcome(
            bet['prediction'],
            game['home_team'],
            game['away_team'],
            game['winner']
        )
        
        # Calculate payout
        if bet_won:
            if bet['odds'] > 0:
                profit = bet_amount * odds / 100
            else:
                profit = bet_amount / (abs(odds) / 100)
            payout = bet_amount + profit
        else:
            payout = 0
            profit = -bet_amount
        
        # Update bet
        update_bet(bet_id, {
            'status': 'won' if bet_won else 'lost',
            'payout': payout,
            'profit': profit,
            'settled_at': timestamp
        })
        
        # Update bankroll
        bankroll += payout
    
    update_bankroll(bankroll)
```

---

## Performance Tracking

### Inverse Prediction System

**Purpose:** Track both original and inverse predictions to identify models that should be bet against

**Implementation:**

```python
# In analysis_generator.py
def store_analysis(analysis_item):
    # Store original
    table.put_item(analysis_item)
    
    # Create and store inverse
    inverse_item = create_inverse_prediction(analysis_item)
    if inverse_item:
        table.put_item(inverse_item)

def create_inverse_prediction(analysis):
    inverse = analysis.copy()
    inverse['sk'] = analysis['sk'].replace('#LATEST', '#INVERSE')
    inverse['prediction'] = flip_prediction(analysis['prediction'])
    inverse['confidence'] = 1.0 - analysis['confidence']
    inverse['is_inverse'] = True
    return inverse
```

**Verification:**

```python
# In outcome_collector.py
def verify_inverse_predictions(original_items, game):
    for original in original_items:
        # Find inverse
        inverse_sk = original['sk'].replace('#LATEST', '#INVERSE')
        inverse = get_item(original['pk'], inverse_sk)
        
        if inverse:
            # Verify inverse
            inverse_correct = check_accuracy(inverse['prediction'], game)
            
            # Update inverse record
            update_item(inverse, {
                'analysis_correct': inverse_correct,
                'verified_analysis_pk': f"VERIFIED#{model}#{sport}#game#inverse",
                'verified_analysis_sk': timestamp
            })
            
            print(f"Original: {original_correct}, Inverse: {inverse_correct}")
```

---

### Model Comparison Dashboard

**Backend:** `backend/api_handler.py` - `handle_get_model_comparison()`

**Frontend:** `frontend/src/components/ModelComparison.tsx`

**API Endpoint:** `GET /model-comparison?sport={sport}&days={days}&user_id={user_id}`

**Process:**
1. Query original predictions from VerifiedAnalysisGSI
2. Query inverse predictions from VerifiedAnalysisGSI
3. Calculate accuracy for both versions
4. Determine recommendation:
   - ORIGINAL: Use predictions as-is
   - INVERSE: Bet against predictions
   - AVOID: Neither version profitable
5. Include user models if user_id provided
6. Sort by best performing version

**Response:**
```json
{
  "sport": "basketball_nba",
  "days": 30,
  "models": [
    {
      "model": "consensus",
      "is_user_model": false,
      "sample_size": 45,
      "original_accuracy": 0.622,
      "original_correct": 28,
      "inverse_accuracy": 0.378,
      "inverse_correct": 17,
      "recommendation": "ORIGINAL",
      "accuracy_diff": -0.244
    },
    {
      "model": "momentum",
      "is_user_model": false,
      "sample_size": 45,
      "original_accuracy": 0.422,
      "original_correct": 19,
      "inverse_accuracy": 0.578,
      "inverse_correct": 26,
      "recommendation": "INVERSE",
      "accuracy_diff": 0.156
    }
  ],
  "summary": {
    "total_models": 10,
    "inverse_recommended": 2,
    "original_recommended": 6,
    "avoid": 2
  }
}
```

---

## API Layer

### API Gateway Configuration

**File:** `infrastructure/lib/bet-collector-api-stack.ts`

**Endpoints:**

```typescript
// Public endpoints
GET /health

// Protected endpoints (Cognito auth)
GET /games?sport={sport}&bookmaker={bookmaker}
GET /analyses?sport={sport}&model={model}&type={type}
GET /model-comparison?sport={sport}&days={days}&user_id={user_id}
GET /benny/dashboard

// User models
GET /user-models?user_id={user_id}
POST /user-models
GET /user-models/{model_id}
PUT /user-models/{model_id}
DELETE /user-models/{model_id}
GET /user-models/{model_id}/performance
GET /user-models/{model_id}/backtests
POST /user-models/{model_id}/backtests
```

**CORS Configuration:**
```typescript
allowOrigins: [
  'http://localhost:3000',
  'https://*.amplifyapp.com',
  'https://beta.carpoolbets.com',
  'https://carpoolbets.com'
]
```

**Cognito Authorizer:**
```typescript
const authorizer = new CognitoUserPoolsAuthorizer({
  cognitoUserPools: [userPool],
  authorizerName: 'carpool-bets-authorizer'
});
```

---

### API Handler

**File:** `backend/api_handler.py`

**Request Flow:**
```python
def lambda_handler(event, context):
    # Parse request
    path = event['path']
    method = event['httpMethod']
    query_params = event.get('queryStringParameters', {})
    body = json.loads(event.get('body', '{}'))
    
    # Route to handler
    if path == '/games':
        return handle_get_games(query_params)
    elif path == '/model-comparison':
        return handle_get_model_comparison(query_params)
    # ... etc
    
    # Return response
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(response_data)
    }
```

**Helper Functions:**
```python
def create_response(status_code, body):
    """Create standardized API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True
        },
        'body': json.dumps(body, default=decimal_to_float)
    }

def decimal_to_float(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError
```

---

**Last Updated:** 2026-02-11
**Version:** 1.0
