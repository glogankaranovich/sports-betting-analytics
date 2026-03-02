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

Add to `sports` array:
```typescript
const sports = [
  { key: 'basketball_nba', name: 'NBA' },
  // ...
  { key: 'your_new_sport', name: 'YOURSPORT' }
];
```

Add cron schedules (stagger by 5 minutes from other sports):
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

### 5. Add to Analysis Generator

**File:** `infrastructure/lib/analysis-generator-stack.ts`

Add Lambda function property:
```typescript
export class AnalysisGeneratorStack extends cdk.Stack {
  public readonly analysisGeneratorYOURSPORT: lambda.Function;
  // ...
}
```

Create Lambda function:
```typescript
this.analysisGeneratorYOURSPORT = new lambda.Function(this, 'AnalysisGeneratorYOURSPORT', {
  ...functionProps,
  functionName: `analysis-generator-yoursport-${props.environment}`
});
this.analysisGeneratorYOURSPORT.addToRolePolicy(policy);
weatherApiSecret.grantRead(this.analysisGeneratorYOURSPORT);
```

**File:** `infrastructure/lib/analysis-generator-schedule-stack.ts`

Add to interface:
```typescript
export interface AnalysisGeneratorScheduleStackProps extends cdk.StackProps {
  analysisGeneratorYOURSPORT: lambda.IFunction;
  // ...
}
```

Add to sports array:
```typescript
const sports = [
  { name: 'YOURSPORT', lambda: props.analysisGeneratorYOURSPORT }
];
```

Add to sport key mapping:
```typescript
private getSportKey(sportName: string): string {
  const sportMap: Record<string, string> = {
    'YOURSPORT': 'your_new_sport',
    // ...
  };
}
```

### 6. Add to Season Manager

**File:** `backend/season_manager.py`

Add season months:
```python
SPORT_SEASONS = {
    "YOURSPORT": {"start": 8, "end": 5},  # August through May
    # ...
}
```

Note: `start` and `end` are month numbers (1-12). If `start > end`, season wraps around year end.

## Components That Auto-Update

These components automatically pick up new sports from `SUPPORTED_SPORTS` constant:

- **Benny Trader** - Uses `SUPPORTED_SPORTS` for game and prop analysis
- **News Collector** - Uses `SUPPORTED_SPORTS` env var
- **Schedule Collector** - Uses `getSupportedSportsArray()`
- **Weather Collector** - Uses `getSupportedSportsArray()`
- **Season Stats Collector** - Uses `getSupportedSportsArray()`
- **Team Stats Collector** - Uses `SUPPORTED_SPORTS` env var
- **Player Stats Collector** - Uses `SUPPORTED_SPORTS` env var

## Components That Need Manual Updates

- **Odds Collector Schedule** - Hardcoded sports array with cron schedules
- **Analysis Generator** - Requires Lambda function creation for each sport
- **Analysis Generator Schedule** - Requires Lambda function references
- **Season Manager** - Requires season month configuration

## Deployment

After adding a new sport, deploy these stacks:

```bash
cd infrastructure

# Deploy odds collector with new schedule
make deploy-stack STACK=Dev-OddsSchedule

# Deploy data collectors (auto-pick up from constants)
make deploy-stack STACK=Dev-ScheduleCollector
make deploy-stack STACK=Dev-WeatherCollector
make deploy-stack STACK=Dev-SeasonStatsCollector
make deploy-stack STACK=Dev-TeamStatsCollector
make deploy-stack STACK=Dev-PlayerStatsCollector
make deploy-stack STACK=Dev-NewsCollectors

# Deploy analysis generator (creates Lambda functions)
make deploy-stack STACK=Dev-AnalysisGenerator

# Deploy analysis schedule (creates EventBridge rules)
make deploy-stack STACK=Dev-AnalysisSchedule

# Deploy season manager (enables/disables rules by season)
make deploy-stack STACK=Dev-SeasonManager

# Deploy Benny Trader (picks up new sport)
make deploy-stack STACK=Dev-BennyTrader

# Deploy API (updates supported sports list)
make deploy-stack STACK=Dev-BetCollectorApi

# Deploy frontend with new sport options
cd ../frontend
npm run build
# Upload to S3 or deploy via your frontend pipeline
```

## Sport Key Format

Use the format from The Odds API:
- `basketball_nba` - NBA Basketball
- `americanfootball_nfl` - NFL Football
- `baseball_mlb` - MLB Baseball
- `icehockey_nhl` - NHL Hockey
- `soccer_epl` - English Premier League
- `basketball_ncaab` - NCAA Men's Basketball
- `basketball_wncaab` - NCAA Women's Basketball
- `americanfootball_ncaaf` - NCAA Football
- `soccer_usa_mls` - MLS Soccer
- `basketball_wnba` - WNBA Basketball

Check [The Odds API documentation](https://the-odds-api.com/sports-odds-data/sports-apis.html) for available sports.

## Seasonal Coverage

Current sports provide year-round coverage:
- **Jan**: NFL, NBA, NHL, NCAAB, WNCAAB, NCAAF, MLS
- **Feb**: NBA, NHL, MLS
- **Mar**: NBA, NHL, MLB, MLS, NCAAB, WNCAAB
- **Apr**: NBA, NHL, MLB, MLS, NCAAB, WNCAAB
- **May**: MLB, MLS, WNBA, EPL
- **Jun**: MLB, MLS, WNBA
- **Jul**: MLB, MLS, WNBA
- **Aug**: MLB, MLS, WNBA, EPL, NCAAF
- **Sep**: MLB, MLS, WNBA, EPL, NFL, NCAAF
- **Oct**: NBA, NHL, MLB, MLS, WNBA, EPL, NFL
- **Nov**: NBA, NHL, EPL, NFL, NCAAB, WNCAAB
- **Dec**: NBA, NHL, EPL, NFL, NCAAB, WNCAAB, NCAAF

When adding new sports, consider filling gaps or providing alternatives during off-seasons.

## Verification

After deployment:

1. Check frontend Settings dropdown shows new sport
2. Check Model Builder shows new sport
3. Verify odds collection runs (check CloudWatch logs)
4. Verify games appear in DynamoDB for the new sport
5. Check analysis generation includes the new sport
