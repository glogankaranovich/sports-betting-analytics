# Data Model Documentation

## DynamoDB Single Table Design

### Table Name
`carpool-bets-v2-{environment}`

### Primary Key Structure
- **PK (Partition Key):** Entity identifier
- **SK (Sort Key):** Entity type + timestamp/identifier

### Global Secondary Indexes (GSIs)

#### 1. ActiveBetsIndexV2
- **Purpose:** Query games by sport and time
- **PK:** `active_bet_pk` = `GAME#{sport}` or `PROP#{sport}`
- **SK:** `commence_time`
- **Use Cases:**
  - Get upcoming games for a sport
  - Get games in a time range
  - Filter by latest odds

#### 2. AnalysisGSI
- **Purpose:** Query analyses by model and sport
- **PK:** `analysis_pk` = `ANALYSIS#{sport}#{bookmaker}#{model}#{type}`
- **SK:** `model_type` = `{model}#{type}`
- **Use Cases:**
  - Get all analyses for a model
  - Filter by sport and bookmaker

#### 3. AnalysisTimeGSI
- **Purpose:** Query analyses by time
- **PK:** `analysis_time_pk` = `ANALYSIS#{sport}#{bookmaker}#{model}#{type}`
- **SK:** `commence_time`
- **Use Cases:**
  - Get recent analyses
  - Time-based filtering
  - Outcome verification

#### 4. VerifiedAnalysisGSI
- **Purpose:** Query verified predictions for performance tracking
- **PK:** `verified_analysis_pk` = `VERIFIED#{model}#{sport}#{type}[#inverse]`
- **SK:** `verified_analysis_sk` = `{timestamp}`
- **Use Cases:**
  - Calculate model accuracy
  - Track performance over time
  - Compare original vs inverse

#### 5. TeamOutcomesIndex
- **Purpose:** Query team's recent games
- **PK:** `team_outcome_pk` = `TEAM#{sport}#{team}`
- **SK:** `completed_at`
- **Use Cases:**
  - Get team's last 5 games
  - Calculate recent form
  - Streak analysis

#### 6. UserModelsIndex
- **Purpose:** Query user's models
- **PK:** `user_id`
- **SK:** `model_id`
- **Use Cases:**
  - List user's models
  - User-scoped queries

---

## Entity Types

### 1. Games & Odds

#### Game Odds Record
```
PK: GAME#{game_id}
SK: {bookmaker}#{market_key}#{timestamp}

Attributes:
- game_id: string
- sport: string (basketball_nba, americanfootball_nfl, etc.)
- home_team: string
- away_team: string
- bookmaker: string (fanduel, draftkings, etc.)
- market_key: string (h2h, spreads, totals)
- commence_time: ISO timestamp
- outcomes: list of {name, price, point?}
- latest: boolean
- active_bet_pk: GAME#{sport} (for GSI)
- created_at: ISO timestamp
```

**Example:**
```json
{
  "pk": "GAME#abc123",
  "sk": "fanduel#h2h#2026-02-11T19:00:00Z",
  "game_id": "abc123",
  "sport": "basketball_nba",
  "home_team": "Los Angeles Lakers",
  "away_team": "Boston Celtics",
  "bookmaker": "fanduel",
  "market_key": "h2h",
  "commence_time": "2026-02-11T19:00:00Z",
  "outcomes": [
    {"name": "Los Angeles Lakers", "price": -150},
    {"name": "Boston Celtics", "price": 130}
  ],
  "latest": true,
  "active_bet_pk": "GAME#basketball_nba",
  "created_at": "2026-02-11T14:00:00Z"
}
```

---

### 2. Analyses & Predictions

#### Analysis Record
```
PK: ANALYSIS#{sport}#{game_id}#{bookmaker}
SK: {model}#{type}#LATEST or {model}#{type}#INVERSE

Attributes:
- model: string (consensus, value, momentum, etc.)
- analysis_type: string (game, prop)
- sport: string
- bookmaker: string
- game_id: string
- home_team: string
- away_team: string
- player_name: string (for props)
- market_key: string (for props)
- prediction: string (team name or "Over X.X")
- confidence: decimal (0-1)
- reasoning: string
- commence_time: ISO timestamp
- created_at: ISO timestamp
- latest: boolean
- is_inverse: boolean (for inverse predictions)
- original_prediction: string (for inverse)

# GSI attributes
- analysis_pk: ANALYSIS#{sport}#{bookmaker}#{model}#{type}
- analysis_time_pk: ANALYSIS#{sport}#{bookmaker}#{model}#{type}
- model_type: {model}#{type}

# Verification attributes (added after game completes)
- actual_home_won: boolean
- analysis_correct: boolean
- outcome_verified_at: ISO timestamp
- verified_analysis_pk: VERIFIED#{model}#{sport}#{type}[#inverse]
- verified_analysis_sk: {timestamp}
```

**Example:**
```json
{
  "pk": "ANALYSIS#basketball_nba#abc123#fanduel",
  "sk": "consensus#game#LATEST",
  "model": "consensus",
  "analysis_type": "game",
  "sport": "basketball_nba",
  "bookmaker": "fanduel",
  "game_id": "abc123",
  "home_team": "Los Angeles Lakers",
  "away_team": "Boston Celtics",
  "prediction": "Los Angeles Lakers",
  "confidence": 0.72,
  "reasoning": "Strong consensus across bookmakers favoring Lakers",
  "commence_time": "2026-02-11T19:00:00Z",
  "created_at": "2026-02-11T14:00:00Z",
  "latest": true,
  "analysis_pk": "ANALYSIS#basketball_nba#fanduel#consensus#game",
  "analysis_time_pk": "ANALYSIS#basketball_nba#fanduel#consensus#game",
  "model_type": "consensus#game"
}
```

**Inverse Example:**
```json
{
  "pk": "ANALYSIS#basketball_nba#abc123#fanduel",
  "sk": "consensus#game#INVERSE",
  "model": "consensus",
  "analysis_type": "game",
  "sport": "basketball_nba",
  "prediction": "Boston Celtics",
  "confidence": 0.28,
  "is_inverse": true,
  "original_prediction": "Los Angeles Lakers",
  "reasoning": "INVERSE of: Strong consensus across bookmakers favoring Lakers",
  ...
}
```

---

### 3. Outcomes

#### Game Outcome
```
PK: OUTCOME#{sport}#{game_id}
SK: RESULT

Attributes:
- game_id: string
- sport: string
- home_team: string
- away_team: string
- home_score: decimal
- away_score: decimal
- winner: string
- completed_at: ISO timestamp
- h2h_pk: H2H#{sport}#{team1}#{team2} (sorted alphabetically)
- h2h_sk: {completed_at}
```

#### Team Outcome (for recent form)
```
PK: TEAM_OUTCOME#{sport}#{team}
SK: {completed_at}#{game_id}

Attributes:
- team_outcome_pk: TEAM#{sport}#{team} (for GSI)
- completed_at: ISO timestamp
- game_id: string
- sport: string
- team: string
- opponent: string
- team_score: decimal
- opponent_score: decimal
- winner: string
- is_home: boolean
```

**Example:**
```json
{
  "pk": "TEAM_OUTCOME#basketball_nba#los_angeles_lakers",
  "sk": "2026-02-11T22:00:00Z#abc123",
  "team_outcome_pk": "TEAM#basketball_nba#los_angeles_lakers",
  "completed_at": "2026-02-11T22:00:00Z",
  "game_id": "abc123",
  "sport": "basketball_nba",
  "team": "Los Angeles Lakers",
  "opponent": "Boston Celtics",
  "team_score": 112,
  "opponent_score": 108,
  "winner": "Los Angeles Lakers",
  "is_home": true
}
```

---

### 4. User Models

#### User Model
```
PK: USER_MODEL#{user_id}
SK: {model_id}

Attributes:
- user_id: string
- model_id: string (UUID)
- name: string
- sport: string
- bet_types: list of strings
- data_sources: map of {source: weight}
  - team_stats: decimal (0-1)
  - odds_movement: decimal (0-1)
  - injuries: decimal (0-1)
  - recent_form: decimal (0-1)
  - head_to_head: decimal (0-1)
- min_confidence: decimal (0-1)
- status: string (active, paused)
- created_at: ISO timestamp
- updated_at: ISO timestamp
```

**Example:**
```json
{
  "pk": "USER_MODEL#user123",
  "sk": "model-uuid-456",
  "user_id": "user123",
  "model_id": "model-uuid-456",
  "name": "My NBA Model",
  "sport": "basketball_nba",
  "bet_types": ["h2h", "spreads"],
  "data_sources": {
    "team_stats": 0.3,
    "odds_movement": 0.2,
    "injuries": 0.2,
    "recent_form": 0.2,
    "head_to_head": 0.1
  },
  "min_confidence": 0.6,
  "status": "active",
  "created_at": "2026-02-01T10:00:00Z",
  "updated_at": "2026-02-11T14:00:00Z"
}
```

---

### 5. Benny Bets

#### Benny Bet
```
PK: BENNY
SK: BET#{timestamp}#{game_id}

Attributes:
- bet_id: string
- game_id: string
- sport: string
- home_team: string
- away_team: string
- prediction: string
- confidence: decimal
- ai_reasoning: string
- ai_key_factors: list of strings
- bet_amount: decimal
- odds: decimal (American odds)
- market_key: string (h2h)
- commence_time: ISO timestamp
- placed_at: ISO timestamp
- status: string (pending, won, lost)
- bankroll_before: decimal

# Settlement attributes (added after game completes)
- payout: decimal
- profit: decimal
- settled_at: ISO timestamp

# GSI attributes
- GSI1PK: BENNY#BETS
- GSI1SK: {commence_time}
```

**Example:**
```json
{
  "pk": "BENNY",
  "sk": "BET#2026-02-11T14:00:00Z#abc123",
  "bet_id": "BET#2026-02-11T14:00:00Z#abc123",
  "game_id": "abc123",
  "sport": "basketball_nba",
  "home_team": "Los Angeles Lakers",
  "away_team": "Boston Celtics",
  "prediction": "Los Angeles Lakers",
  "confidence": 0.72,
  "ai_reasoning": "Lakers have strong home record and Celtics missing key player",
  "ai_key_factors": ["Home court advantage", "Injury impact", "Recent form"],
  "bet_amount": 15.50,
  "odds": -150,
  "market_key": "h2h",
  "commence_time": "2026-02-11T19:00:00Z",
  "placed_at": "2026-02-11T14:00:00Z",
  "status": "pending",
  "bankroll_before": 85.50,
  "GSI1PK": "BENNY#BETS",
  "GSI1SK": "2026-02-11T19:00:00Z"
}
```

**After Settlement:**
```json
{
  ...
  "status": "won",
  "payout": 25.83,  // bet_amount + profit
  "profit": 10.33,  // 15.50 / (150/100) = 10.33
  "settled_at": "2026-02-11T22:00:00Z"
}
```

#### Benny Bankroll
```
PK: BENNY
SK: BANKROLL

Attributes:
- amount: decimal
- last_reset: ISO timestamp (Monday of current week)
- updated_at: ISO timestamp
```

#### Benny Bankroll History
```
PK: BENNY
SK: BANKROLL#{timestamp}

Attributes:
- amount: decimal
- updated_at: ISO timestamp
```

---

### 6. Model Adjustments

#### Model Adjustment
```
PK: MODEL_ADJUSTMENT#{sport}#{bet_type}
SK: {model}

Attributes:
- model: string
- sport: string
- bet_type: string (game, prop)
- recommendation: string (ORIGINAL, INVERSE, AVOID)
- original_accuracy: decimal
- inverse_accuracy: decimal
- sample_size: number
- confidence_multiplier: decimal
- updated_at: ISO timestamp
- lookback_days: number (30)
```

**Example:**
```json
{
  "pk": "MODEL_ADJUSTMENT#basketball_nba#game",
  "sk": "momentum",
  "model": "momentum",
  "sport": "basketball_nba",
  "bet_type": "game",
  "recommendation": "INVERSE",
  "original_accuracy": 0.422,
  "inverse_accuracy": 0.578,
  "sample_size": 45,
  "confidence_multiplier": 0.3,
  "updated_at": "2026-02-11T06:00:00Z",
  "lookback_days": 30
}
```

---

### 7. Team Stats

#### Team Stats
```
PK: TEAM_STATS#{sport}#{team}
SK: {season}#{date}

Attributes:
- team: string
- sport: string
- season: string
- stats: map of {stat_name: value}
  - Field Goal %: decimal
  - Three Point %: decimal
  - Rebounds: decimal
  - Assists: decimal
  - etc.
- updated_at: ISO timestamp
```

---

### 8. Player Stats

#### Player Stats
```
PK: PLAYER_STATS#{sport}#{player}
SK: {game_id}

Attributes:
- player_name: string
- sport: string
- team: string
- game_id: string
- stats: map of {stat_name: value}
  - PTS: decimal
  - REB: decimal
  - AST: decimal
  - etc.
- game_index_pk: {game_id} (for GameIndex GSI)
- game_index_sk: PLAYER_STATS#{sport}#{player}
- updated_at: ISO timestamp
```

---

### 9. Injuries

#### Injury Record
```
PK: INJURIES#{sport}#{team}
SK: {player}#{date}

Attributes:
- team: string
- player: string
- sport: string
- status: string (out, questionable, doubtful)
- injury: string (description)
- impact: decimal (0-1, estimated impact)
- updated_at: ISO timestamp
```

---

## Access Patterns

### 1. Get upcoming games for a sport
```
Query ActiveBetsIndexV2
PK = GAME#{sport}
SK >= {now}
Filter: latest = true
```

### 2. Get all predictions for a game
```
Query
PK = ANALYSIS#{sport}#{game_id}#{bookmaker}
SK begins_with {model}
```

### 3. Get model performance (last 30 days)
```
Query VerifiedAnalysisGSI
PK = VERIFIED#{model}#{sport}#game
SK >= {30_days_ago}
```

### 4. Get team's recent games
```
Query TeamOutcomesIndex
PK = TEAM#{sport}#{team}
SK descending
Limit = 5
```

### 5. Get user's models
```
Query UserModelsIndex
PK = {user_id}
```

### 6. Get Benny's recent bets
```
Query
PK = BENNY
SK begins_with BET#
Limit = 20
```

### 7. Get model adjustments for a sport
```
Query
PK = MODEL_ADJUSTMENT#{sport}#game
```

### 8. Get historical odds for a game
```
Query
PK = HISTORICAL_ODDS#{game_id}
```

### 9. Get Benny's learning parameters
```
Get Item
PK = BENNY#LEARNING
SK = PARAMETERS
```

---

## New Entity Types (Added 2026-02-11)

### 6. Historical Odds

#### Historical Odds Record
```
PK: HISTORICAL_ODDS#{game_id}
SK: {bookmaker}#{market_key}

Attributes:
- game_id: string
- sport: string
- home_team: string
- away_team: string
- bookmaker: string
- market_key: string
- outcomes: list of {name, price, point?}
- commence_time: ISO timestamp
- updated_at: ISO timestamp (when odds were captured)
- archived_at: ISO timestamp (when game completed)
```

**Purpose:** Preserve odds data after game completes for backtesting and learning

**Example:**
```json
{
  "pk": "HISTORICAL_ODDS#abc123",
  "sk": "fanduel#h2h",
  "game_id": "abc123",
  "sport": "basketball_nba",
  "home_team": "Los Angeles Lakers",
  "away_team": "Boston Celtics",
  "bookmaker": "fanduel",
  "market_key": "h2h",
  "outcomes": [
    {"name": "Los Angeles Lakers", "price": -150},
    {"name": "Boston Celtics", "price": 130}
  ],
  "commence_time": "2026-02-11T19:00:00Z",
  "updated_at": "2026-02-11T14:00:00Z",
  "archived_at": "2026-02-11T22:00:00Z"
}
```

---

### 7. Benny Learning Parameters

#### Learning Parameters Record
```
PK: BENNY#LEARNING
SK: PARAMETERS

Attributes:
- min_confidence_adjustment: decimal (added to BASE_MIN_CONFIDENCE)
- kelly_fraction: decimal (0.25 = quarter Kelly)
- performance_by_sport: map of {sport: {wins, total}}
- performance_by_bet_type: map of {bet_type: {wins, total}}
- overall_win_rate: decimal
- total_bets_analyzed: integer
- last_updated: ISO timestamp
```

**Purpose:** Store Benny's learned parameters for adaptive betting strategy

**Example:**
```json
{
  "pk": "BENNY#LEARNING",
  "sk": "PARAMETERS",
  "min_confidence_adjustment": -0.02,
  "kelly_fraction": 0.25,
  "performance_by_sport": {
    "basketball_nba": {"wins": 15, "total": 25},
    "americanfootball_nfl": {"wins": 8, "total": 12}
  },
  "performance_by_bet_type": {
    "h2h": {"wins": 20, "total": 32},
    "spreads": {"wins": 3, "total": 5}
  },
  "overall_win_rate": 0.622,
  "total_bets_analyzed": 37,
  "last_updated": "2026-02-11T12:00:00Z"
}
```

---

### 8. Model Adjustments (Cache)

#### Model Adjustment Record
```
PK: MODEL_ADJUSTMENT#{sport}#{bet_type}
SK: {model}

Attributes:
- model: string
- sport: string
- bet_type: string
- recommendation: string (ORIGINAL, INVERSE, AVOID)
- original_accuracy: decimal
- inverse_accuracy: decimal
- confidence_multiplier: decimal
- sample_size: integer
- calculated_at: ISO timestamp
- expires_at: ISO timestamp (24 hours)
```

**Purpose:** Cache model performance adjustments to reduce query load

**Example:**
```json
{
  "pk": "MODEL_ADJUSTMENT#basketball_nba#game",
  "sk": "consensus",
  "model": "consensus",
  "sport": "basketball_nba",
  "bet_type": "game",
  "recommendation": "ORIGINAL",
  "original_accuracy": 0.625,
  "inverse_accuracy": 0.375,
  "confidence_multiplier": 1.15,
  "sample_size": 48,
  "calculated_at": "2026-02-11T06:00:00Z",
  "expires_at": "2026-02-12T06:00:00Z"
}
```

---

## Data Lifecycle

### Odds Data
- **Created:** Every 4 hours by odds_collector
- **Updated:** New records with latest=true, old records marked latest=false
- **Archived:** When game completes, moved to HISTORICAL_ODDS#
- **Cleanup:** Stale uncompleted games >7 days deleted by odds_cleanup
- **Retention:** Indefinite for historical records

### Predictions
- **Created:** Every 4-6 hours by analysis_generator
- **Updated:** Verified after game completes (outcome_collector)
- **Retention:** Indefinite (for performance tracking)

### Outcomes
- **Created:** Every 4 hours by outcome_collector (last 3 days)
- **Updated:** Never (immutable)
- **Retention:** Indefinite

### User Models
- **Created:** On-demand by users
- **Updated:** By users or weekly by user_model_weight_adjuster (if auto_adjust_weights=true)
- **Deleted:** By users
- **Retention:** Until deleted

### Benny Bets
- **Created:** Daily by benny_trader
- **Updated:** Settled by outcome_collector
- **Retention:** Indefinite (for performance history)

### Benny Learning Parameters
- **Created:** On first bet
- **Updated:** Before each daily analysis run (if 10+ settled bets)
- **Retention:** Single record, continuously updated

### Model Adjustments
- **Created:** Daily by model_adjustment_calculator
- **Updated:** Daily (overwrite)
- **Retention:** 24 hours (cache), then recalculated

### Historical Odds
- **Created:** When game completes by outcome_collector
- **Updated:** Never (immutable)
- **Retention:** Indefinite (for backtesting)

---

## Capacity Planning

### Current Scale
- **Games per day:** ~25 (NBA + NFL)
- **Predictions per day:** ~250 (10 models × 25 games)
- **Users:** Unlimited
- **User models:** 5 per user
- **Benny bets:** ~5 per day
- **Historical odds:** ~100 per completed game

### Storage Estimates
- **Odds records:** ~100 per game × 25 games × 365 days = 912,500/year
- **Historical odds:** ~100 per game × 25 games × 365 days = 912,500/year
- **Prediction records:** ~20 per game × 25 games × 365 days = 182,500/year
- **Outcome records:** ~3 per game × 25 games × 365 days = 27,375/year
- **Learning parameters:** ~10 records (static)
- **Model adjustments:** ~30 records (cached, refreshed daily)
- **Total:** ~2.0M records/year (doubled with historical odds)

### Read/Write Patterns
- **Reads:** Heavy (API queries, model performance, backtesting)
- **Writes:** Moderate (scheduled jobs, user actions)
- **Hot data:** Last 90 days
- **Warm data:** Historical odds (for backtesting)
- **Cold data:** Old predictions (rarely accessed)

---

**Last Updated:** 2026-02-11
**Version:** 2.0
