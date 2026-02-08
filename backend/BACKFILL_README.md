# Historical Odds Backfill

This script backfills historical odds data from The Odds API into DynamoDB for backtesting.

## Prerequisites

1. The Odds API key with historical data access (paid plan)
2. AWS credentials configured for each environment
3. Python dependencies: `boto3`, `requests`

## Usage

### Backfill Dev Environment
```bash
cd backend
python backfill_historical_odds.py --env dev --api-key YOUR_API_KEY
```

### Backfill Beta Environment
```bash
python backfill_historical_odds.py --env beta --api-key YOUR_API_KEY
```

### Backfill Prod Environment
```bash
python backfill_historical_odds.py --env prod --api-key YOUR_API_KEY
```

### Custom Options
```bash
# Backfill 3 years instead of 2
python backfill_historical_odds.py --env dev --api-key YOUR_API_KEY --years 3

# Use custom AWS profile
python backfill_historical_odds.py --env dev --api-key YOUR_API_KEY --profile my-profile
```

## What It Does

1. Fetches historical odds for the past 2 years (default)
2. Covers 5 sports: NBA, NFL, NHL, MLB, EPL
3. Fetches one snapshot per day (at noon)
4. Stores odds in DynamoDB with structure:
   - PK: `GAME#{sport}#{game_id}`
   - SK: `ODDS#{bookmaker}#{market}`
   - Includes: teams, commence_time, odds, outcomes

## Cost Estimation

- **API Requests**: ~3,650 per sport (2 years × 365 days × 5 sports = ~18,250 total)
- **API Cost**: 10 requests per call × $0.01 = ~$1,825 total
- **Time**: ~5 hours (1 second per request + API processing)

## Data Structure

Each game is stored with:
```json
{
  "PK": "GAME#basketball_nba#abc123",
  "SK": "ODDS#draftkings#h2h",
  "GSI1PK": "SPORT#basketball_nba",
  "GSI1SK": "2024-01-15T19:00:00Z",
  "game_id": "abc123",
  "sport": "basketball_nba",
  "home_team": "Lakers",
  "away_team": "Warriors",
  "commence_time": "2024-01-15T19:00:00Z",
  "bookmaker": "draftkings",
  "market_key": "h2h",
  "outcomes": [...],
  "historical_backfill": true,
  "backfill_date": "2026-02-08T18:30:00Z"
}
```

## After Backfill

Once backfilled, users can run backtests against this historical data without any additional API calls. The backtest engine will query DynamoDB for historical odds and outcomes.

## Monitoring

The script outputs:
- Progress per sport and date
- Total API requests used
- Total games stored
- Estimated cost
- Time elapsed

## Notes

- Run once per environment
- Can be re-run safely (will overwrite existing data)
- Rate limited to 1 request per second
- Skips dates with no data
- Marks backfilled data with `historical_backfill: true` flag
