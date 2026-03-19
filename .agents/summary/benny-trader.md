# Benny Trader

> Main orchestrator for AI-powered sports betting analysis and bet placement.

## File
`backend/benny_trader.py` (~2050 lines)

## Purpose
Central class that runs the full betting pipeline: collects odds, analyzes games/props via LLM, sizes bets, executes them, manages positions, and runs post-analysis learning.

## Key Components

### `BennyTrader` class
- `run_daily_analysis()` — main entry point. Analyzes games, props, builds parlays, manages positions, runs post-run learning.
- `analyze_games()` — iterates sports, fetches odds from DynamoDB, calls LLM for each game via model's `build_game_prompt()`.
- `analyze_props()` — fetches player props, calls LLM via model's `build_prop_prompt()`, calculates EV.
- `_ai_analyze_game()` / `_ai_analyze_prop()` — sends prompts to Claude Sonnet 4.5 via Bedrock, parses JSON responses.
- Uses distributed locking (DynamoDB) to prevent concurrent executions.

### `lambda_handler`
- Entry point for Lambda/ECS. Runs V1 then V3 sequentially.
- Sends consensus email comparing V1/V3 picks.

## Data Flow
```
Odds (DynamoDB) → Game/Prop Analysis (Claude) → Bet Sizing (Model) → Bet Execution (DynamoDB) → Post-Run Learning
```

## Dependencies
- `benny.models.v1.BennyV1`, `benny.models.v3.BennyV3`
- `benny.bet_executor.BetExecutor`
- `benny.parlay_engine.ParlayEngine`
- `benny.position_manager.PositionManager`
- AWS: DynamoDB, Bedrock, SQS (notifications)

## DynamoDB Keys
- Bets: `pk=BENNY|BENNY_V3`, `sk=BET#<timestamp>#<game_id>`
- Lock: `pk=SYSTEM`, `sk=BENNY_LOCK`

## Runtime
- ECS Fargate task (4x daily: 9AM, 1PM, 5PM, 9PM ET)
- Also has a Lambda handler (currently disabled schedule)
