# DynamoDB Query Reference

Quick reference for querying the carpool-bets-v2 table.

## ⚠️ CRITICAL: Always Query, Never Scan

**NEVER use `scan`** - it reads the entire table and is slow/expensive.

**ALWAYS use `query`** with a partition key (pk) or GSI.

If you need to find records across multiple partition keys, query each pk separately or use a GSI.

## Table Structure

**Primary Key**: `pk` (partition key), `sk` (sort key)

**GSIs**:
- `AnalysisTimeGSI`: `analysis_time_pk`, `analysis_time_sk`
- `VerifiedAnalysisGSI`: `verified_analysis_pk`, `verified_analysis_sk`
- `GameIndex`: `game_index_pk`, `game_index_sk`
- `ActiveBetsIndexV2`: `active_bets_pk`, `active_bets_sk`

## Common Queries

### Team Stats
```bash
# Get team stats for a sport
AWS_PROFILE=sports-betting-dev aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"TEAM_STATS#basketball_nba#boston_celtics"}}' \
  --output json | jq -r '.Items[0].stats.M'
```

**PK Format**: `TEAM_STATS#{sport}#{team_normalized}`

### Game Outcomes
```bash
# Get outcome for a specific game
AWS_PROFILE=sports-betting-dev aws dynamodb get-item \
  --table-name carpool-bets-v2-dev \
  --key '{"pk":{"S":"OUTCOME#basketball_nba#abc123"},"sk":{"S":"RESULT"}}' \
  --output json | jq -r '.Item | {home_team: .home_team.S, away_team: .away_team.S, home_score: .home_score.N, away_score: .away_score.N, winner: .winner.S}'
```

**PK Format**: `OUTCOME#{sport}#{game_id}`  
**SK**: `RESULT`

### Team Outcomes (by team)
```bash
# Get recent outcomes for a team
AWS_PROFILE=sports-betting-dev aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"TEAM_OUTCOME#basketball_wncaab#providence_friars"}}' \
  --limit 5 \
  --output json | jq -r '.Items[] | {opponent: .opponent.S, team_score: .team_score.N, opponent_score: .opponent_score.N, winner: .winner.S, game_id: .game_id.S}'
```

**PK Format**: `TEAM_OUTCOME#{sport}#{team_normalized}`

### Predictions (Analyses)
```bash
# Get predictions for a specific game
AWS_PROFILE=sports-betting-dev aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --index-name AnalysisTimeGSI \
  --key-condition-expression "analysis_time_pk = :pk" \
  --filter-expression "game_id = :gid" \
  --expression-attribute-values '{":pk":{"S":"ANALYSIS#basketball_nba#draftkings#rest_schedule#game"}, ":gid":{"S":"abc123"}}' \
  --output json | jq -r '.Items[] | {prediction: .prediction.S, home_team: .home_team.S, away_team: .away_team.S, analysis_correct: .analysis_correct.BOOL}'
```

**AnalysisTimeGSI PK Format**: `ANALYSIS#{sport}#{bookmaker}#{model}#{bet_type}`  
**SK in item**: `{model}#{bet_type}#LATEST` or `{model}#{bet_type}#INVERSE`

### Verified Predictions
```bash
# Get verified predictions for a model
AWS_PROFILE=sports-betting-dev aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --index-name VerifiedAnalysisGSI \
  --key-condition-expression "verified_analysis_pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"VERIFIED#rest_schedule#basketball_nba#game"}}' \
  --limit 10 \
  --output json | jq -r '.Items[] | {prediction: .prediction.S, home_team: .home_team.S, away_team: .away_team.S, analysis_correct: .analysis_correct.BOOL}'
```

**VerifiedAnalysisGSI PK Format**: 
- Original: `VERIFIED#{model}#{sport}#game`
- Inverse: `VERIFIED#{model}#{sport}#game#inverse`

### Player Stats
```bash
# Get player stats for a game
AWS_PROFILE=sports-betting-dev aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --index-name GameIndex \
  --key-condition-expression "game_index_pk = :gid" \
  --expression-attribute-values '{":gid":{"S":"abc123"}}' \
  --output json | jq -r '.Items[] | select(.pk | startswith("PLAYER_STATS")) | {player: .player_name.S, stats: .stats.M}'
```

**PK Format**: `PLAYER_STATS#{sport}#{player_normalized}`  
**GameIndex PK**: `game_id`

## Field Types

DynamoDB stores typed values. Common patterns:

- **String**: `.S` - e.g., `"home_team": {"S": "Boston Celtics"}`
- **Number**: `.N` - e.g., `"home_score": {"N": "110"}`
- **Boolean**: `.BOOL` - e.g., `"analysis_correct": {"BOOL": true}`
- **Map**: `.M` - e.g., `"stats": {"M": {...}}`
- **List**: `.L` - e.g., `"items": {"L": [...]}`

When using `jq`, access with `.field.S`, `.field.N`, `.field.BOOL`, etc.

## Counting Records

```bash
# Count verified predictions for a model
AWS_PROFILE=sports-betting-dev aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --index-name VerifiedAnalysisGSI \
  --key-condition-expression "verified_analysis_pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"VERIFIED#rest_schedule#basketball_nba#game"}}' \
  --select COUNT \
  --output json | jq -r '.Count'
```

## Filtering Results

```bash
# Get only correct predictions
AWS_PROFILE=sports-betting-dev aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --index-name VerifiedAnalysisGSI \
  --key-condition-expression "verified_analysis_pk = :pk" \
  --filter-expression "analysis_correct = :correct" \
  --expression-attribute-values '{":pk":{"S":"VERIFIED#rest_schedule#basketball_nba#game"}, ":correct":{"BOOL":true}}' \
  --output json | jq -r '.Count'
```

## Sports List

Current supported sports:
- `basketball_nba`
- `icehockey_nhl`
- `americanfootball_nfl`
- `baseball_mlb`
- `soccer_epl`
- `soccer_usa_mls`
- `basketball_ncaab` (men's NCAA)
- `basketball_wncaab` (women's NCAA)
- `americanfootball_ncaaf`
- `basketball_wnba`

## Models List

System models:
- `consensus`
- `value`
- `momentum`
- `contrarian`
- `hot_cold`
- `rest_schedule`
- `matchup`
- `injury_aware`
- `news`
- `ensemble`
- `fundamentals`
