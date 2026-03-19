# AGENTS.md

> Project guide for AI agents working on this codebase.

## Project Overview
Sports betting analytics platform ("Benny Trader") with AI-powered betting agents that analyze games, place bets, and learn from outcomes. Built on AWS with Python backend, TypeScript CDK infrastructure, and React frontend.

## Architecture
```
┌─────────────────────────────────────────────────────┐
│                   ECS Fargate (4x daily)             │
│  BennyTrader → V1 Model → Claude Sonnet 4.5         │
│              → V3 Model → Claude Sonnet 4.5         │
├─────────────────────────────────────────────────────┤
│                   Lambda Functions                   │
│  Odds Collector │ Outcome Collector │ Coaching Memo  │
│  Player Stats   │ Team Stats        │ Weekly Report  │
├─────────────────────────────────────────────────────┤
│                   DynamoDB (single table)            │
│  carpool-bets-v2-dev                                │
├─────────────────────────────────────────────────────┤
│                   Frontend (Amplify)                 │
│  React Dashboard │ AI Chat Agent                    │
└─────────────────────────────────────────────────────┘
```

## Component Summaries
See [.agents/summary/INDEX.md](.agents/summary/INDEX.md) for detailed documentation of each component.

## Key Conventions

### AWS
- **Profile**: `AWS_PROFILE=sports-betting-dev`
- **Region**: `us-east-1`
- **Table**: `carpool-bets-v2-dev`
- **Model PKs**: V1=`BENNY`, V3=`BENNY_V3`

### Development
- Python 3.11 (backend)
- TypeScript (CDK infrastructure)
- Do NOT add or modify tests unless explicitly requested
- Do NOT include secret keys in code
- Minimal code changes — absolute minimum needed
- Check `.kiro/steering/development-workflow.md` for workflow processes

### Deployment
- CDK: `cd infrastructure && npx cdk deploy <StackName> --profile sports-betting-dev`
- ECS: Docker image pushed to ECR `dev-batch-jobs:latest`, task def auto-updates
- Makefile targets available in `infrastructure/Makefile`

### Models
- V1 (BENNY): Primary model, Kelly sizing, adaptive thresholds, ~$214 bankroll
- V3 (BENNY_V3): Lean model, flat 5% sizing, fixed 70% threshold, ~$96 bankroll
- V2: Dead — features ported to V1

### Coaching Agent
- Runs daily at 8:30 AM ET as separate Lambda
- Generates LLM coaching memo from 30-day performance data
- Explore/Avoid system with 30-day cooldowns for underperforming markets
- Both V1 and V3 read the memo via `_get_coaching_memo()` (cached per run)

## Keeping Summaries Updated
When making significant changes to the codebase, update the relevant summary file in `.agents/summary/`. A pre-commit hook will remind you if source files changed but summaries weren't updated. Run `scripts/check-summary-freshness.sh` to check manually.
