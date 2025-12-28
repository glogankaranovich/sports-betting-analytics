# Database Schema

## DynamoDB Tables

### Bets Table
**Table Name**: `sports-betting-bets`

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| bet_id | String | PK | Unique bet identifier |
| user_id | String | GSI-PK | User identifier |
| sport | String | - | Sport type (football, basketball, etc.) |
| event | String | - | Event description |
| bet_type | String | - | Type of bet (moneyline, spread, over_under) |
| selection | String | - | Bet selection |
| odds | Number | - | Betting odds |
| amount | Number | - | Bet amount |
| status | String | - | Bet status (active, won, lost, cancelled) |
| created_at | String | - | ISO timestamp |
| settled_at | String | - | ISO timestamp (optional) |

**Global Secondary Indexes**:
- `user-id-index`: user_id (PK), created_at (SK)
- `status-index`: status (PK), created_at (SK)

### Predictions Table
**Table Name**: `sports-betting-predictions`

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| prediction_id | String | PK | Unique prediction identifier |
| event | String | GSI-PK | Event description |
| sport | String | - | Sport type |
| prediction | String | - | Prediction result |
| probability | Number | - | Confidence probability (0-1) |
| confidence | Number | - | Model confidence score |
| model_version | String | - | ML model version used |
| created_at | String | SK | ISO timestamp |
| features | Map | - | Input features used |

**Global Secondary Indexes**:
- `event-index`: event (PK), created_at (SK)
- `sport-date-index`: sport (PK), created_at (SK)

### Sports Data Table
**Table Name**: `sports-betting-data`

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| data_id | String | PK | Unique data identifier |
| sport | String | GSI-PK | Sport type |
| event | String | - | Event description |
| source | String | - | Data source identifier |
| data_type | String | - | Type of data (stats, odds, etc.) |
| raw_data | Map | - | Raw collected data |
| processed_data | Map | - | Processed/cleaned data |
| collected_at | String | SK | ISO timestamp |
| s3_location | String | - | S3 path for large data files |

**Global Secondary Indexes**:
- `sport-date-index`: sport (PK), collected_at (SK)
- `source-index`: source (PK), collected_at (SK)

### Users Table
**Table Name**: `sports-betting-users`

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| user_id | String | PK | Unique user identifier |
| email | String | GSI-PK | User email |
| username | String | - | Display name |
| password_hash | String | - | Hashed password |
| preferences | Map | - | User preferences |
| created_at | String | - | ISO timestamp |
| last_login | String | - | ISO timestamp |
| is_active | Boolean | - | Account status |

**Global Secondary Indexes**:
- `email-index`: email (PK)

## S3 Bucket Structure

### Raw Data Bucket: `sports-betting-raw-data`
```
/sports-data/
  /{sport}/
    /{year}/
      /{month}/
        /{day}/
          /raw-{source}-{timestamp}.json
          /processed-{source}-{timestamp}.json

/model-data/
  /training-sets/
    /{model-version}/
      /features-{timestamp}.parquet
      /labels-{timestamp}.parquet
  /models/
    /{model-version}/
      /model.pkl
      /metadata.json
```

### Static Assets Bucket: `sports-betting-assets`
```
/frontend/
  /static/
  /images/
/documentation/
  /api-docs/
  /schemas/
```

## Data Relationships

```
Users (1) ──── (N) Bets
Bets (N) ──── (1) Predictions (via event matching)
Sports Data (N) ──── (1) Predictions (via event matching)
```

## Indexes and Query Patterns

### Common Query Patterns:
1. Get user's active bets: `user-id-index` where `status = 'active'`
2. Get predictions for event: `event-index` 
3. Get recent sports data: `sport-date-index` with date range
4. Get bet history: `user-id-index` with date range
5. Get model performance: `prediction_id` join with bet outcomes
