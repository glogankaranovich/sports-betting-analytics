# Adding New Sports

This guide explains how to add support for a new sport to the platform.

## Overview

Sports are centrally managed through constants that propagate to backend, infrastructure, and frontend. Most components automatically pick up new sports from these constants.

## Steps to Add a New Sport

### 1. Add to Backend Constants

**File:** `backend/constants.py`

Add the sport key to `SUPPORTED_SPORTS` default value:
```python
SUPPORTED_SPORTS = os.environ.get(
    "SUPPORTED_SPORTS",
    "basketball_nba,americanfootball_nfl,...,your_new_sport",
).split(",")
```

Add display name to `SPORT_NAMES`:
```python
SPORT_NAMES = {
    "basketball_nba": "NBA",
    # ...
    "your_new_sport": "Your Sport Name",
}
```

### 2. Add to Infrastructure Constants

**File:** `infrastructure/lib/utils/constants.ts`

Add to `SUPPORTED_SPORTS`:
```typescript
export const PLATFORM_CONSTANTS = {
  SUPPORTED_SPORTS: 'basketball_nba,americanfootball_nfl,...,your_new_sport',
  // ...
};
```

### 3. Add to Frontend

**File:** `frontend/src/App.tsx`

Add to all `availableSports` arrays (4 occurrences):
```typescript
availableSports={['basketball_nba', ..., 'your_new_sport']}
```

**File:** `frontend/src/components/Settings.tsx`

Add to `sportDisplayNames`:
```typescript
const sportDisplayNames: Record<string, string> = {
  'basketball_nba': 'NBA',
  // ...
  'your_new_sport': 'Your Sport Name'
};
```

**File:** `frontend/src/components/ModelBuilder.tsx`

Add to `SPORTS` array:
```typescript
const SPORTS = [
  { value: 'basketball_nba', label: 'NBA' },
  // ...
  { value: 'your_new_sport', label: 'Your Sport Name' }
];
```

**File:** `frontend/src/components/ModelList.tsx`

Add to `sportNames`:
```typescript
const sportNames: Record<string, string> = {
  'basketball_nba': 'NBA',
  // ...
  'your_new_sport': 'Your Sport Name'
};
```

### 4. Add to Odds Collector Schedule

**File:** `infrastructure/lib/odds-collector-schedule-stack.ts`

Add to `sports` array with a unique short name:
```typescript
const sports = [
  { key: 'basketball_nba', name: 'NBA' },
  // ...
  { key: 'your_new_sport', name: 'YOURSPORT' }
];
```

Add cron schedules (stagger by 5-15 minutes from other sports):
```typescript
const oddsSchedules = [
  'cron(0 */4 * * ? *)',   // NBA
  // ...
  'cron(20 */4 * * ? *)',  // Your sport - every 4 hours at :20
];

const propsSchedules = [
  'cron(0 */8 * * ? *)',   // NBA
  // ...
  'cron(20 */8 * * ? *)',  // Your sport - every 8 hours at :20
];
```

## Components That Auto-Update

These components automatically pick up new sports from `PLATFORM_CONSTANTS`:

- **News Collector** - Uses `SUPPORTED_SPORTS` env var
- **Schedule Collector** - Uses `getSupportedSportsArray()`
- **Weather Collector** - Uses `getSupportedSportsArray()`
- **Season Stats Collector** - Uses `getSupportedSportsArray()`
- **Analysis Generator** - Uses `SUPPORTED_SPORTS` env var
- **Team Stats Collector** - Uses `SUPPORTED_SPORTS` env var
- **Player Stats Collector** - Uses `SUPPORTED_SPORTS` env var

## Deployment

After adding a new sport, deploy these stacks:

```bash
cd infrastructure

# Deploy data collectors
make deploy-stack STACK=Dev-OddsCollector
make deploy-stack STACK=Dev-ScheduleCollector
make deploy-stack STACK=Dev-WeatherCollector
make deploy-stack STACK=Dev-SeasonStatsCollector
make deploy-stack STACK=Dev-TeamStatsCollector
make deploy-stack STACK=Dev-PlayerStatsCollector
make deploy-stack STACK=Dev-NewsCollectors

# Deploy analysis
make deploy-stack STACK=Dev-AnalysisSchedule
```

## Sport Key Format

Use the format from The Odds API:
- `basketball_nba` - NBA Basketball
- `americanfootball_nfl` - NFL Football
- `baseball_mlb` - MLB Baseball
- `icehockey_nhl` - NHL Hockey
- `soccer_epl` - English Premier League
- `basketball_mens-college-basketball` - NCAA Men's Basketball
- `basketball_womens-college-basketball` - NCAA Women's Basketball
- `football_college-football` - NCAA Football

Check [The Odds API documentation](https://the-odds-api.com/sports-odds-data/sports-apis.html) for available sports.

## Verification

After deployment:

1. Check frontend Settings dropdown shows new sport
2. Check Model Builder shows new sport
3. Verify odds collection runs (check CloudWatch logs)
4. Verify games appear in DynamoDB for the new sport
5. Check analysis generation includes the new sport
