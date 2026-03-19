# Data Collectors

> Lambda functions that collect external data on schedules.

## Files (all in `backend/`)

### `odds_collector.py` — Sports Odds Collection
- Fetches odds from The Odds API for all supported sports
- Stores in DynamoDB with market keys (h2h, spreads, totals)
- Runs every 4 hours per sport via EventBridge schedules

### `outcome_collector.py` — Bet Settlement
- Settles pending bets by checking game results via The Odds API
- Handles game bets, prop bets, and parlay settlement
- Updates bet status (won/lost), calculates profit, updates bankroll
- Runs every 4 hours via EventBridge

### `player_stats_collector.py` — Player Statistics
- Collects player stats from ESPN API for prop bet analysis
- Paginates DynamoDB results, uses BETWEEN time window for completed games
- Stores per-player stats: PTS, REB, AST averages and last-5 trends

### `team_stats_collector.py` — Team Statistics
- Collects team-level stats from ESPN
- Offensive/defensive ratings, pace, recent form

### `team_season_stats_collector.py` — Season Aggregates
- Collects full-season team statistics

### `espn_collector.py` — ESPN Data Fetcher
- Shared ESPN API client used by stats collectors
- Handles rate limiting, retries

### `schedule_collector.py` — Game Schedules
- Collects upcoming game schedules per sport
- Used for travel fatigue and rest day calculations

### `injury_collector.py` — Injury Reports
- Collects injury data from ESPN
- Stores player injury status (out, doubtful, questionable)

### `weather_collector.py` — Weather Data
- Collects weather for outdoor sports venues
- Temperature, wind, precipitation

## Supported Sports
NBA, NHL, NFL, MLB, NCAAB, WNCAAB, EPL, MLS, NCAAF, WNBA
