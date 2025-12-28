# API Documentation

## Overview

The Sports Betting Analytics API provides endpoints for managing bets, retrieving predictions, and accessing sports data.

## Base URL
```
http://localhost:8000
```

## Authentication

All endpoints require JWT authentication except for health checks.

```http
Authorization: Bearer <jwt_token>
```

## Endpoints

### Health Check
```http
GET /health
```
Returns system health status.

### Bets Management

#### Get All Bets
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
