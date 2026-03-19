# Benny Models

> AI betting model implementations with different strategies.

## Files
- `backend/benny/models/base.py` — Abstract base class
- `backend/benny/models/v1.py` — Primary model (Kelly sizing, adaptive thresholds)
- `backend/benny/models/v3.py` — Lean model (flat sizing, variance-aware)
- `backend/benny/models/v2.py` — Dead/killed. Features ported to V1.

## Base Model (`BennyModelBase`)
Abstract class defining the interface:
- `build_game_prompt()` / `build_prop_prompt()` — construct LLM prompts
- `calculate_bet_size()` — sizing strategy
- `should_bet()` — bet qualification logic
- `get_threshold()` — confidence threshold per sport/market
- `post_run()` — post-analysis learning updates

## V1 (`BennyV1`) — Primary Model
- **Sizing**: Kelly Criterion with fractional multiplier
- **Thresholds**: Adaptive per sport/market via `ThresholdOptimizer`
- **Prompts**: Include coaching memo, performance warnings, Elo ratings
- **Post-run**: Updates learning params, runs `OutcomeAnalyzer`, `ThresholdOptimizer`
- **Min bet**: $1 | **Max bet**: 15% of bankroll
- **DynamoDB PK**: `BENNY`
- **Bankroll**: ~$213 (as of Mar 2026)

## V3 (`BennyV3`) — Lean Model
- **Sizing**: Flat 5% of bankroll (no Kelly)
- **Thresholds**: Fixed 70% confidence minimum
- **Bet criteria**: Confidence ≥ 70%, EV ≥ 5%, market disagreement ≥ 5%
- **Prompts**: Minimal, include coaching memo as conditional block
- **Min bet**: $5 | **Max bet**: 10% of bankroll
- **DynamoDB PK**: `BENNY_V3`
- **Bankroll**: ~$96 (as of Mar 2026)

## Coaching Memo Integration
Both models call `_get_coaching_memo()` (cached per run) to inject a pre-computed coaching memo into game and prop prompts. Replaces V1's old 8-helper self-reflection system.

## Dependencies
- `benny.learning_engine.LearningEngine`
- `benny.bankroll_manager.BankrollManager`
- `benny.coaching_agent.CoachingAgent`
- `benny.outcome_analyzer.OutcomeAnalyzer` (V1 post_run)
- `benny.threshold_optimizer.ThresholdOptimizer` (V1 post_run)
