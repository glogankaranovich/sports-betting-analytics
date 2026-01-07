# API Documentation

## Overview

The Sports Betting Analytics API provides endpoints for managing bets, retrieving analysis results, and accessing sports data. The API includes ML-powered analysis endpoints and real-time odds data.

## Base URLs

### Production
```
https://rk6h0zryz5.execute-api.us-east-1.amazonaws.com/prod
```

### Beta
```
https://fgguxgxr4b.execute-api.us-east-1.amazonaws.com/prod
```

### Development
```
https://pylcs4ypld.execute-api.us-east-1.amazonaws.com/prod
```

## Authentication

All endpoints require JWT authentication except for health checks. Use AWS Cognito tokens.

```http
Authorization: Bearer <jwt_token>
```

## Endpoints

### Health Check
```http
GET /health
```
Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "table": "carpool-bets-v2-prod",
  "environment": "prod"
}
```

### Games & Odds

#### Get All Games
```http
GET /games?sport=americanfootball_nfl&limit=100
```
Returns games with odds from multiple bookmakers.

#### Get Single Game
```http
GET /games/{game_id}
```
Returns detailed odds for a specific game.

### ML Analysis Results

#### Get Game Analysis
```http
GET /game-predictions?limit=50
```
Returns AI-generated game outcome predictions.

**Response:**
```json
{
  "predictions": [
    {
      "game_id": "abc123",
      "home_team": "Kansas City Chiefs",
      "away_team": "Buffalo Bills",
      "home_win_probability": 0.65,
      "away_win_probability": 0.35,
      "confidence_score": 0.82,
      "value_bets": ["home_moneyline"],
      "predicted_at": "2026-01-02T12:00:00Z"
    }
  ],
  "count": 25
}
```

#### Get Prop Predictions
```http
GET /prop-predictions?limit=100
```
Returns AI-generated player prop predictions.

**Response:**
```json
{
  "predictions": [
    {
      "player_name": "Patrick Mahomes",
      "prop_type": "player_pass_yds",
      "predicted_value": 285.5,
      "over_probability": 0.58,
      "under_probability": 0.42,
      "confidence_score": 0.75
    }
  ],
  "count": 50
}
```

### Player Props

#### Get Player Props
```http
GET /player-props?sport=americanfootball_nfl&prop_type=player_pass_yds
```
Returns raw player prop data from bookmakers.

### Utility Endpoints

#### Get Sports
```http
GET /sports
```
Returns available sports.

#### Get Bookmakers
```http
GET /bookmakers
```
Returns available bookmakers.
```http
GET /api/v1/bets
```

#### Create New Bet
```http
POST /api/v1/bets
Content-Type: application/json

{
  "sport": "football",
  "event": "Team A vs Team B",
  "bet_type": "moneyline",
  "selection": "Team A",
  "odds": 1.85,
  "amount": 100.00
}
```

#### Update Bet Outcome
```http
PUT /api/v1/bets/{bet_id}/outcome
Content-Type: application/json

{
  "status": "won",
  "settled_at": "2025-12-27T22:00:00Z"
}
```

### Predictions

#### Get Predictions
```http
GET /api/v1/predictions?sport=football&date=2025-12-28
```

#### Request New Prediction
```http
POST /api/v1/predictions
Content-Type: application/json

{
  "sport": "football",
  "event": "Team A vs Team B",
  "data": {
    "team_a_stats": {...},
    "team_b_stats": {...}
  }
}
```

### Sports Data

#### Get Sports Data
```http
GET /api/v1/sports-data?sport=football&date=2025-12-28
```

## Response Format

All responses follow this structure:

```json
{
  "success": true,
  "data": {...},
  "message": "Success",
  "timestamp": "2025-12-27T22:00:00Z"
}
```

## Error Handling

Error responses include:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid bet amount",
    "details": {...}
  },
  "timestamp": "2025-12-27T22:00:00Z"
}
```

## Rate Limiting

- 100 requests per minute per user
- 1000 requests per hour per user
