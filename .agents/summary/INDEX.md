# Summary Index

> Quick reference to all component summaries. See [AGENTS.md](../../AGENTS.md) for project overview.

| Summary | Description | Key Files |
|---------|-------------|-----------|
| [benny-trader](benny-trader.md) | Main orchestrator — game/prop analysis, bet placement | `backend/benny_trader.py` |
| [benny-models](benny-models.md) | V1/V3 model implementations, prompts, sizing | `backend/benny/models/` |
| [benny-engines](benny-engines.md) | Learning, bankroll, coaching, execution engines | `backend/benny/` |
| [data-collectors](data-collectors.md) | Odds, outcomes, player/team stats, injuries, weather | `backend/*_collector.py` |
| [backend-services](backend-services.md) | Lambda handlers, APIs, utilities | `backend/` |
| [infrastructure](infrastructure.md) | 44 CDK stacks — all AWS resources | `infrastructure/lib/` |
| [dynamodb-schema](dynamodb-schema.md) | Single-table DynamoDB key patterns | `carpool-bets-v2-{env}` |
| [frontend](frontend.md) | React/Amplify dashboard | `frontend/src/` |

## Last Updated
2026-03-18
