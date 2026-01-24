# User-Defined Models Feature

## Overview
Allow users to create, configure, and share custom betting analysis models. Users can monetize their models by sharing them with other users, with the platform taking a revenue share.

## Core Concept

Users create custom betting models by:
1. **Selecting data sources** (team stats, player stats, odds movement, etc.)
2. **Assigning weights** to each data source
3. **Configuring analysis parameters** (confidence thresholds, dynamic weighting, etc.)
4. **Sharing models** with others (potentially monetized)

## Model Configuration Schema

```json
{
  "model_id": "user123_momentum_v2",
  "name": "My Custom Momentum Model",
  "description": "Focuses on recent team performance and line movement",
  "creator_user_id": "user123",
  "version": 1,
  "sport": "basketball_nba",
  "bet_type": "game",
  "data_sources": {
    "team_stats": {
      "enabled": true,
      "weight": 0.4,
      "fields": ["offensive_rating", "defensive_rating", "pace"],
      "lookback_games": 10
    },
    "player_stats": {
      "enabled": true,
      "weight": 0.3,
      "fields": ["PTS", "REB", "AST"],
      "min_minutes": 20
    },
    "odds_movement": {
      "enabled": true,
      "weight": 0.2,
      "time_window_hours": 24
    },
    "historical_performance": {
      "enabled": true,
      "weight": 0.1,
      "lookback_days": 30
    }
  },
  "dynamic_weighting": true,
  "min_confidence": 0.6,
  "max_confidence": 0.95,
  "sharing": {
    "public": true,
    "price_per_month": 9.99,
    "revenue_share": 0.7,
    "trial_days": 7
  },
  "created_at": "2026-01-23T19:00:00Z",
  "updated_at": "2026-01-23T19:00:00Z"
}
```

## Scoring Algorithm

### Base Equation
```python
def calculate_model_score(data_sources, weights, game_data):
    """
    Weighted sum of normalized data source scores
    
    Score = Σ(source_score_i × weight_i) / Σ(weight_i)
    
    Where:
    - source_score_i: Normalized score (0-1) from data source i
    - weight_i: User-defined weight for data source i
    """
    total_score = 0
    total_weight = 0
    
    for source, config in data_sources.items():
        if not config['enabled']:
            continue
            
        # Get score from data source (0-1 normalized)
        source_score = evaluate_data_source(source, config, game_data)
        
        # Apply dynamic weighting if enabled
        if config.get('dynamic_weighting'):
            performance_multiplier = get_performance_multiplier(source)
            adjusted_weight = config['weight'] * performance_multiplier
        else:
            adjusted_weight = config['weight']
        
        total_score += source_score * adjusted_weight
        total_weight += adjusted_weight
    
    # Normalize to 0-1 confidence score
    confidence = total_score / total_weight if total_weight > 0 else 0
    
    # Clamp to min/max confidence
    confidence = max(min_confidence, min(confidence, max_confidence))
    
    return confidence
```

### Data Sources

Each data source must return a normalized score (0-1):

**Team Stats:**
```python
def evaluate_team_stats(config, game_data):
    """
    Compare team stats to league averages
    Returns 0-1 score based on relative performance
    """
    team_score = 0
    for field in config['fields']:
        team_value = get_team_stat(game_data, field, config['lookback_games'])
        league_avg = get_league_average(field)
        league_std = get_league_std(field)
        
        # Z-score normalization
        z_score = (team_value - league_avg) / league_std
        normalized = sigmoid(z_score)  # Convert to 0-1
        team_score += normalized
    
    return team_score / len(config['fields'])
```

**Odds Movement:**
```python
def evaluate_odds_movement(config, game_data):
    """
    Analyze line movement over time window
    Returns 0-1 score based on sharp action indicators
    """
    initial_line = get_opening_line(game_data)
    current_line = get_current_line(game_data)
    line_movement = abs(current_line - initial_line)
    
    # More movement = higher confidence in direction
    movement_score = min(line_movement / 3.0, 1.0)  # Cap at 3 point moves
    
    # Check for reverse line movement (sharp action)
    public_betting_pct = get_public_betting_percentage(game_data)
    if is_reverse_line_movement(public_betting_pct, line_movement):
        movement_score *= 1.2  # Boost for sharp action
    
    return min(movement_score, 1.0)
```

**Custom Data (User-Imported):**
```python
def evaluate_custom_data(config, game_data):
    """
    Process user-imported data with custom transformation
    Returns 0-1 score based on user-defined logic
    """
    # Fetch user's custom data for this game
    custom_data = get_custom_data(
        user_id=config['user_id'],
        dataset_id=config['dataset_id'],
        game_id=game_data['id']
    )
    
    # Apply user-defined transformation
    if config['transformation'] == 'linear':
        # Linear scaling: (value - min) / (max - min)
        score = (custom_data['value'] - config['min_value']) / (config['max_value'] - config['min_value'])
    elif config['transformation'] == 'threshold':
        # Binary threshold: 1 if above threshold, 0 otherwise
        score = 1.0 if custom_data['value'] > config['threshold'] else 0.0
    elif config['transformation'] == 'percentile':
        # Percentile rank within dataset
        score = calculate_percentile(custom_data['value'], config['dataset_id'])
    elif config['transformation'] == 'custom_formula':
        # User-defined formula (sandboxed execution)
        score = evaluate_formula(config['formula'], custom_data)
    
    return max(0.0, min(score, 1.0))  # Clamp to 0-1
```

## Custom Data Import

### Overview
Allow users to import their own datasets and use them as data sources in their models. This enables advanced users to incorporate proprietary data, external APIs, or custom analytics.

### Use Cases
- **Weather data**: Temperature, wind, precipitation for outdoor sports
- **Travel metrics**: Distance traveled, time zone changes, rest days
- **Social sentiment**: Twitter/Reddit sentiment analysis
- **Injury probability**: Custom injury risk models
- **Referee tendencies**: Historical referee stats
- **Betting market data**: Sharp money indicators from other sources
- **Custom analytics**: User's own statistical models

### Data Import Schema

```json
{
  "dataset_id": "user123_weather_data",
  "name": "Weather Impact Dataset",
  "description": "Temperature and wind data for NFL games",
  "user_id": "user123",
  "sport": "americanfootball_nfl",
  "data_type": "game_level",  // or "team_level", "player_level"
  "schema": {
    "game_id": "string",
    "temperature": "float",
    "wind_speed": "float",
    "precipitation": "float",
    "dome": "boolean"
  },
  "transformation_options": {
    "available_methods": ["linear", "threshold", "percentile", "custom_formula"],
    "min_value": 0,
    "max_value": 100,
    "default_transformation": "linear"
  },
  "storage": {
    "type": "s3",  // or "dynamodb" for small datasets
    "location": "s3://user-datasets/user123/weather_data.csv",
    "format": "csv"  // or "json", "parquet"
  },
  "metadata": {
    "row_count": 1500,
    "last_updated": "2026-01-23T19:00:00Z",
    "size_bytes": 45000,
    "status": "active"
  }
}
```

### Data Import Flow

```
1. User uploads file (CSV, JSON, Excel)
   ↓
2. Validate schema and data quality
   ↓
3. Store in S3 (or DynamoDB for small datasets)
   ↓
4. Create dataset metadata record
   ↓
5. Index data for fast lookups
   ↓
6. Make available in model builder
```

### Transformation Methods

**1. Linear Scaling**
```python
# Scale value to 0-1 range
score = (value - min_value) / (max_value - min_value)

# Example: Temperature 32-100°F → 0-1
score = (temp - 32) / (100 - 32)
```

**2. Threshold**
```python
# Binary: above/below threshold
score = 1.0 if value > threshold else 0.0

# Example: Wind speed > 15mph = 1, else 0
score = 1.0 if wind_speed > 15 else 0.0
```

**3. Percentile Rank**
```python
# Rank within historical distribution
score = percentile_rank(value, historical_values)

# Example: 75th percentile = 0.75
```

**4. Custom Formula (Sandboxed)**
```python
# User-defined formula with safety constraints
# Allowed: +, -, *, /, (), math functions
# Blocked: imports, file access, network calls

formula = "(temperature - 32) * 0.01 + (wind_speed / 20)"
score = safe_eval(formula, data)
```

### Model Configuration with Custom Data

```json
{
  "data_sources": {
    "custom_weather": {
      "enabled": true,
      "weight": 0.15,
      "dataset_id": "user123_weather_data",
      "field": "temperature",
      "transformation": "linear",
      "min_value": 32,
      "max_value": 100,
      "invert": false  // Higher temp = higher score
    },
    "custom_travel": {
      "enabled": true,
      "weight": 0.10,
      "dataset_id": "user123_travel_metrics",
      "field": "rest_days",
      "transformation": "threshold",
      "threshold": 2,
      "invert": true  // More rest = higher score
    }
  }
}
```

### Database Schema for Custom Datasets

**User Datasets Table:**
```
PK: USER_DATASET#{user_id}#{dataset_id}
SK: METADATA

Attributes:
- dataset_id
- name
- description
- user_id
- sport
- data_type
- schema (JSON)
- transformation_options (JSON)
- storage (JSON)
- metadata (JSON)
- created_at
- updated_at
- status (active, processing, error)
```

**Dataset Data (for small datasets):**
```
PK: DATASET_DATA#{dataset_id}
SK: {game_id}#{timestamp}

Attributes:
- dataset_id
- game_id
- data (JSON)
- created_at
```

**Dataset Index (for fast lookups):**
```
GSI: DatasetGameIndex
PK: DATASET#{dataset_id}
SK: GAME#{game_id}

Attributes:
- dataset_id
- game_id
- data (JSON)
```

### API Endpoints

**Dataset Management:**
```
POST   /datasets                  - Upload new dataset
GET    /datasets                  - List user's datasets
GET    /datasets/{id}             - Get dataset details
PUT    /datasets/{id}             - Update dataset
DELETE /datasets/{id}             - Delete dataset
POST   /datasets/{id}/refresh     - Re-upload/update data
GET    /datasets/{id}/preview     - Preview first 10 rows
GET    /datasets/{id}/stats       - Get dataset statistics
```

**Data Validation:**
```
POST   /datasets/validate         - Validate file before upload
GET    /datasets/{id}/quality     - Check data quality metrics
```

### Storage Strategy

**Small Datasets (<1MB, <1000 rows):**
- Store in DynamoDB
- Fast lookups
- No S3 costs

**Medium Datasets (1MB-100MB):**
- Store in S3
- Cache frequently accessed data in DynamoDB
- Use S3 Select for queries

**Large Datasets (>100MB):**
- Store in S3
- Use Athena for queries
- Require data aggregation before use

### Data Quality Checks

**Validation Rules:**
1. **Schema validation**: All required fields present
2. **Data types**: Values match declared types
3. **Missing values**: <10% missing data per field
4. **Duplicates**: No duplicate game_id entries
5. **Date range**: Data within reasonable timeframe
6. **Value ranges**: No extreme outliers (>5 std dev)

**Quality Score:**
```python
quality_score = (
    schema_valid * 0.3 +
    type_valid * 0.2 +
    completeness * 0.2 +
    uniqueness * 0.15 +
    freshness * 0.15
)

# Require quality_score > 0.8 to use in models
```

### Security & Limits

**Access Control:**
- Users can only access their own datasets
- Datasets used in shared models remain private
- No data sharing between users (yet)

**Storage Limits:**
- Free tier: 10 datasets, 100MB total
- Pro tier: 50 datasets, 1GB total
- Enterprise: Unlimited (custom pricing)

**Processing Limits:**
- Max file size: 100MB per upload
- Max rows: 100,000 per dataset
- Max fields: 50 per dataset
- Upload rate: 10 per day

**Formula Safety:**
- Sandboxed execution (no imports, file access, network)
- Timeout: 100ms per evaluation
- Memory limit: 10MB per formula
- Whitelist of allowed functions

### UI/UX

**Dataset Upload Flow:**
1. Drag-and-drop file or select from computer
2. Auto-detect schema from file headers
3. Preview data (first 10 rows)
4. Configure transformation options
5. Validate data quality
6. Confirm and upload

**Model Builder Integration:**
1. "Add Custom Data Source" button
2. Select from user's datasets
3. Choose field to use
4. Configure transformation
5. Set weight
6. Preview impact on model

### Pricing

**Data Import Costs:**
- Storage: $0.023/GB/month (S3 pricing)
- Processing: $0.10 per 1000 rows processed
- Queries: $5 per TB scanned (Athena pricing)

**User Pricing:**
- Free tier: Included in base subscription
- Pro tier: $5/month for 1GB storage
- Enterprise: Custom pricing for >1GB

### Implementation Phases

**Phase 1: Basic Import (MVP)**
- CSV upload
- Simple schema validation
- DynamoDB storage for small datasets
- Linear transformation only

**Phase 2: Advanced Transformations**
- Multiple transformation methods
- Custom formulas (sandboxed)
- Data quality scoring
- S3 storage for large datasets

**Phase 3: Data Marketplace**
- Share datasets with other users (paid)
- Browse public datasets
- Dataset subscriptions
- Revenue sharing

### Risks & Mitigations

**Risk 1: Data Quality**
- **Mitigation**: Strict validation, quality scoring, user reviews

**Risk 2: Storage Costs**
- **Mitigation**: Tiered pricing, storage limits, auto-cleanup of unused data

**Risk 3: Security**
- **Mitigation**: Sandboxed execution, no cross-user data access, audit logs

**Risk 4: Performance**
- **Mitigation**: Caching, indexing, query optimization, rate limiting

**Risk 5: Abuse**
- **Mitigation**: Upload limits, file size limits, content scanning

### Success Metrics

- Number of datasets uploaded
- Average dataset size
- Datasets used in models
- Custom data source adoption rate
- Data quality scores
- Storage costs vs revenue

### Future Enhancements

- **Real-time data**: API integrations for live data
- **Data marketplace**: Buy/sell datasets
- **Collaborative datasets**: Share with team members
- **Data versioning**: Track changes over time
- **Automated updates**: Scheduled data refreshes
- **Data visualization**: Charts and graphs for datasets
- **ML feature engineering**: Auto-generate features from raw data

### User Models Table
```
PK: USER_MODEL#{user_id}#{model_id}
SK: CONFIG#v{version}

Attributes:
- model_id
- name
- description
- creator_user_id
- version
- sport
- bet_type
- data_sources (JSON)
- dynamic_weighting
- min_confidence
- max_confidence
- sharing (JSON)
- created_at
- updated_at
- status (active, archived, suspended)
```

### Shared Models Index (GSI)
```
GSI: SharedModelsIndex
PK: SHARED_MODEL#{sport}#{bet_type}
SK: {performance_score}#{model_id}

Attributes:
- model_id
- creator_user_id
- name
- description
- price_per_month
- trial_days
- performance_metrics (JSON)
- subscriber_count
- created_at
```

### Model Subscriptions
```
PK: MODEL_SUBSCRIPTION#{user_id}
SK: {model_id}

Attributes:
- model_id
- user_id
- creator_user_id
- subscription_status (active, trial, cancelled, expired)
- price_per_month
- trial_end_date
- subscription_start_date
- next_billing_date
- stripe_subscription_id
```

### Model Performance Tracking
```
PK: MODEL_PERFORMANCE#{model_id}
SK: {date}

Attributes:
- model_id
- date
- total_predictions
- correct_predictions
- accuracy
- avg_confidence
- roi
- brier_score
```

### Model Analyses
```
PK: ANALYSIS#{sport}#{game_id}#{bookmaker}
SK: {model_id}#{bet_type}#LATEST

Attributes:
- model_id (user-defined or system model)
- creator_user_id (if user-defined)
- is_custom_model (boolean)
- ... (existing analysis fields)
```

## Architecture

### Execution Model

**Option 1: Scheduled Execution**
- Run all active models at fixed intervals (e.g., daily at 9am)
- Pros: Predictable costs, batch processing efficiency
- Cons: Not real-time, may miss late-breaking info

**Option 2: On-Demand Execution**
- Generate analyses when user requests them
- Pros: Real-time, only pay for what's used
- Cons: Higher latency, unpredictable costs

**Option 3: Hybrid (Recommended)**
- **Scheduled**: Popular shared models (>10 subscribers)
- **On-Demand**: Private models and low-subscriber models
- **Cached**: Results cached for 1 hour to reduce duplicate runs

### Model Execution Flow

```
1. Trigger (scheduled or on-demand)
   ↓
2. Load model configuration
   ↓
3. Fetch required data sources
   ↓
4. Calculate scores for each data source
   ↓
5. Apply weights and dynamic adjustments
   ↓
6. Generate confidence score
   ↓
7. Create analysis record
   ↓
8. Update performance metrics
   ↓
9. Notify subscribers (if shared model)
```

### API Endpoints

**Model Management:**
```
POST   /models                    - Create new model
GET    /models                    - List user's models
GET    /models/{model_id}         - Get model details
PUT    /models/{model_id}         - Update model
DELETE /models/{model_id}         - Delete model
POST   /models/{model_id}/test    - Backtest model
```

**Model Marketplace:**
```
GET    /marketplace/models        - Browse public models
GET    /marketplace/models/{id}   - Get model details
POST   /marketplace/subscribe     - Subscribe to model
DELETE /marketplace/unsubscribe   - Unsubscribe from model
GET    /marketplace/subscriptions - List user's subscriptions
```

**Model Execution:**
```
POST   /models/{model_id}/analyze - Run model on-demand
GET    /models/{model_id}/results - Get recent analyses
GET    /models/{model_id}/performance - Get performance metrics
```

## Monetization

### Revenue Model
- **Platform fee**: 30% of subscription revenue
- **Creator payout**: 70% of subscription revenue
- **Minimum payout**: $50 (accumulate until threshold)
- **Payout frequency**: Monthly (1st of each month)

### Pricing Tiers
- **Free**: Public models with no subscription fee
- **Basic**: $4.99 - $9.99/month
- **Premium**: $10 - $24.99/month
- **Pro**: $25+/month

### Stripe Integration
```python
# Create subscription
subscription = stripe.Subscription.create(
    customer=user.stripe_customer_id,
    items=[{
        'price': model.stripe_price_id,
    }],
    trial_period_days=model.trial_days,
    metadata={
        'model_id': model.model_id,
        'creator_user_id': model.creator_user_id,
    }
)

# Handle webhook for successful payment
@webhook_handler('invoice.payment_succeeded')
def handle_payment(invoice):
    # Calculate creator payout (70%)
    creator_amount = invoice.amount_paid * 0.7
    
    # Add to creator's pending balance
    update_creator_balance(creator_user_id, creator_amount)
    
    # Process payout if threshold met
    if creator_balance >= 5000:  # $50 in cents
        process_payout(creator_user_id)
```

## Implementation Phases

### Phase 1: Model Builder (MVP)
**Goal**: Allow users to create and save custom models

**Features:**
- Model configuration UI
- Data source selection
- Weight assignment
- Save/load personal models
- Basic validation

**Timeline**: 2-3 weeks

**Deliverables:**
- Model builder UI component
- Model configuration API
- DynamoDB schema for user models
- Unit tests

### Phase 2: Model Execution
**Goal**: Generate analyses using custom models

**Features:**
- Model execution engine
- Data source evaluation functions
- Performance tracking
- Results display in UI

**Timeline**: 3-4 weeks

**Deliverables:**
- Model execution Lambda
- Data source evaluators
- Performance tracking system
- Integration with existing analysis display

### Phase 3: Sharing & Marketplace
**Goal**: Enable model sharing (free only)

**Features:**
- Make models public
- Browse marketplace
- Subscribe to free models
- Model performance leaderboard

**Timeline**: 2-3 weeks

**Deliverables:**
- Marketplace UI
- Subscription management
- Public model discovery
- Performance metrics display

### Phase 4: Monetization
**Goal**: Enable paid subscriptions and creator payouts

**Features:**
- Stripe integration
- Subscription management
- Revenue tracking
- Creator payouts
- Trial periods

**Timeline**: 3-4 weeks

**Deliverables:**
- Stripe integration
- Payment processing
- Payout system
- Billing management UI

## Key Challenges & Solutions

### 1. Data Normalization
**Challenge**: Each data source has different scales and distributions

**Solution**: 
- Use z-score normalization for stats
- Sigmoid function to convert to 0-1 range
- Define clear normalization rules per data source

### 2. Performance Validation
**Challenge**: Prevent overfitting and gaming the system

**Solution**:
- Minimum sample size (50 predictions) before going public
- Rolling 30-day performance window
- Automatic suspension if accuracy drops below 50%
- Backtesting required before publishing

### 3. Compute Costs
**Challenge**: Running many custom models can be expensive

**Solution**:
- Cache results for 1 hour
- Batch processing for scheduled runs
- Limit complexity (max 5 data sources per model)
- Charge premium for high-frequency updates

### 4. Quality Control
**Challenge**: Bad models could hurt platform reputation

**Solution**:
- Model review process for paid models
- Performance-based ranking
- User ratings and reviews
- Automatic suspension for poor performance

### 5. Legal/Compliance
**Challenge**: Gambling advice regulations vary by jurisdiction

**Solution**:
- Clear disclaimers (entertainment only)
- Age verification
- Geo-blocking where required
- Terms of service for model creators

## Success Metrics

### User Engagement
- Number of custom models created
- Active model creators
- Models published to marketplace
- Average models per user

### Marketplace Performance
- Model subscriptions
- Subscription retention rate
- Average subscription price
- Top performing models

### Financial
- Monthly recurring revenue (MRR)
- Creator payouts
- Platform revenue (30% share)
- Average revenue per user (ARPU)

### Model Quality
- Average model accuracy
- Models with >55% accuracy
- User satisfaction ratings
- Subscription renewal rate

## Future Enhancements

### Advanced Features
- **Ensemble models**: Combine multiple models
- **Auto-tuning**: ML-based weight optimization
- **Real-time updates**: Live odds integration
- **Social features**: Follow creators, model discussions
- **API access**: Programmatic model execution

### Data Sources
- **Weather data**: For outdoor sports
- **Injury reports**: Real-time injury tracking
- **Social sentiment**: Twitter/Reddit analysis
- **Referee stats**: Historical referee tendencies
- **Travel schedules**: Back-to-back games, time zones

### Advanced Analytics
- **Backtesting**: Test models on historical data
- **Monte Carlo simulation**: Risk analysis
- **Correlation analysis**: Find data source relationships
- **Feature importance**: Which factors matter most

## Questions for Discussion

1. **Minimum performance threshold?** 
   - Require >55% accuracy to stay public?
   - Grace period before suspension?

2. **Model versioning?**
   - Allow updates without breaking subscriptions?
   - Notify subscribers of changes?

3. **Compute limits?**
   - Max data sources per model?
   - Rate limiting for on-demand execution?

4. **Data access?**
   - What data can users access?
   - Premium data sources for paid tiers?

5. **Backtesting?**
   - Required before publishing?
   - How much historical data to provide?

6. **Revenue share?**
   - 70/30 split fair?
   - Different tiers for top performers?

7. **Trial periods?**
   - Standard 7 days?
   - Allow creators to customize?

8. **Model limits?**
   - Max models per user?
   - Different limits for free vs paid users?

## Next Steps

1. **Review and refine** this document with team
2. **Prioritize features** for Phase 1
3. **Create detailed technical specs** for model builder
4. **Design UI mockups** for model configuration
5. **Set up project tracking** (Jira/GitHub issues)
6. **Begin Phase 1 implementation**

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-23  
**Author**: Planning Discussion  
**Status**: Draft - Pending Review
