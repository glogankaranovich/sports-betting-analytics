# Benny Trader Runbook

## Overview
Benny is an AI-powered sports betting trader that runs daily at 10 AM ET via ECS. This runbook covers common operations, investigations, and troubleshooting.

## Architecture
- **ECS Task**: `Dev-EcsTasks-BennyTraderTask` (runs daily 10 AM ET)
- **Lambda**: `Dev-BennyTrader-BennyTrader` (manual invocation only)
- **DynamoDB Table**: `Dev-SportsData`
- **Lock Key**: `BENNY#LOCK`

## Common Operations

### Manual Invocation
```bash
# Via Lambda (recommended for testing)
aws lambda invoke --function-name Dev-BennyTrader-BennyTrader \
  --cli-binary-format raw-in-base64-out \
  --payload '{"test_mode": true}' \
  --profile sports-betting-dev --region us-east-1 \
  response.json

# Via ECS (production-like)
aws ecs run-task \
  --cluster Dev-EcsTasks-BennyCluster \
  --task-definition Dev-EcsTasks-BennyTraderTask \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --profile sports-betting-dev --region us-east-1
```

### Check Recent Logs
```bash
# Last 30 minutes
aws logs tail /ecs/dev-benny-trader --since 30m \
  --profile sports-betting-dev --region us-east-1 --follow

# Last run (no follow)
aws logs tail /ecs/dev-benny-trader --since 2h \
  --profile sports-betting-dev --region us-east-1 | tail -100
```

### Check Lock Status
```bash
# See if lock exists
aws dynamodb get-item \
  --table-name Dev-SportsData \
  --key '{"pk":{"S":"BENNY"},"sk":{"S":"LOCK"}}' \
  --profile sports-betting-dev --region us-east-1

# Manually release stuck lock (emergency only)
aws dynamodb delete-item \
  --table-name Dev-SportsData \
  --key '{"pk":{"S":"BENNY"},"sk":{"S":"LOCK"}}' \
  --profile sports-betting-dev --region us-east-1
```

## Investigation Queries

### Recent Bets
```bash
# Get last 10 bets
aws dynamodb query \
  --table-name Dev-SportsData \
  --key-condition-expression "pk = :pk AND begins_with(sk, :sk)" \
  --expression-attribute-values '{":pk":{"S":"BENNY"},":sk":{"S":"BET#"}}' \
  --scan-index-forward false \
  --limit 10 \
  --profile sports-betting-dev --region us-east-1
```

### Bankroll History
```bash
# Get last 30 snapshots
aws dynamodb query \
  --table-name Dev-SportsData \
  --key-condition-expression "pk = :pk AND begins_with(sk, :sk)" \
  --expression-attribute-values '{":pk":{"S":"BENNY"},":sk":{"S":"SNAPSHOT#"}}' \
  --scan-index-forward false \
  --limit 30 \
  --profile sports-betting-dev --region us-east-1
```

### Learning Parameters
```bash
# Current learning state
aws dynamodb get-item \
  --table-name Dev-SportsData \
  --key '{"pk":{"S":"BENNY"},"sk":{"S":"LEARNING_PARAMS"}}' \
  --profile sports-betting-dev --region us-east-1
```

### Performance by Market
```bash
# Get settled bets from last 30 days, group by market
aws dynamodb query \
  --table-name Dev-SportsData \
  --key-condition-expression "pk = :pk AND begins_with(sk, :sk)" \
  --filter-expression "#status IN (:won, :lost)" \
  --expression-attribute-names '{"#status":"status"}' \
  --expression-attribute-values '{":pk":{"S":"BENNY"},":sk":{"S":"BET#"},":won":{"S":"won"},":lost":{"S":"lost"}}' \
  --profile sports-betting-dev --region us-east-1 \
  | jq -r '.Items[] | [.market_key.S, .status.S] | @tsv' \
  | sort | uniq -c
```

### Props vs Games Performance
```bash
# Count wins/losses for props (player_* markets)
aws dynamodb query \
  --table-name Dev-SportsData \
  --key-condition-expression "pk = :pk AND begins_with(sk, :sk)" \
  --filter-expression "#status IN (:won, :lost) AND begins_with(market_key, :player)" \
  --expression-attribute-names '{"#status":"status"}' \
  --expression-attribute-values '{":pk":{"S":"BENNY"},":sk":{"S":"BET#"},":won":{"S":"won"},":lost":{"S":"lost"},":player":{"S":"player_"}}' \
  --profile sports-betting-dev --region us-east-1 \
  | jq '[.Items[] | .status.S] | group_by(.) | map({status: .[0], count: length})'

# Count wins/losses for games (h2h, spreads, totals)
aws dynamodb query \
  --table-name Dev-SportsData \
  --key-condition-expression "pk = :pk AND begins_with(sk, :sk)" \
  --filter-expression "#status IN (:won, :lost) AND (market_key = :h2h OR market_key = :spreads OR market_key = :totals)" \
  --expression-attribute-names '{"#status":"status"}' \
  --expression-attribute-values '{":pk":{"S":"BENNY"},":sk":{"S":"BET#"},":won":{"S":"won"},":lost":{"S":"lost"},":h2h":{"S":"h2h"},":spreads":{"S":"spreads"},":totals":{"S":"totals"}}' \
  --profile sports-betting-dev --region us-east-1 \
  | jq '[.Items[] | .status.S] | group_by(.) | map({status: .[0], count: length})'
```

## Troubleshooting

### Benny Not Placing Bets
1. Check if lock is stuck: `aws dynamodb get-item ...` (see above)
2. Check logs for errors: `aws logs tail ...`
3. Verify opportunities exist: Check analysis records for today's games
4. Check bankroll: Ensure sufficient funds

### Lock Not Releasing
- Verify ECS task role has `dynamodb:DeleteItem` permission
- Check that `sys.exit()` is AFTER the finally block in `benny_trader.py`
- Manually release if stuck (see above)

### Props Not Being Considered
- Verify props collector is running: `aws events list-rules --query 'Rules[?contains(Name, "PropsCollector")]'`
- Check props exist in DB for today's games
- Verify prop parsing logic handles `outcome` field (not `outcomes` array)

### Type Errors in Kelly Calculation
- All values in `bankroll_manager.py` Kelly calculation must be `Decimal` type
- Check line 63 for proper `Decimal()` conversions

## Deployment

### Deploy Code Changes
```bash
# Build and push Docker image
cd /Users/glkaranovich/workplace/sports-betting-analytics
docker build -t dev-batch-jobs .
aws ecr get-login-password --region us-east-1 --profile sports-betting-dev | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag dev-batch-jobs:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/dev-batch-jobs:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/dev-batch-jobs:latest

# Deploy ECS task (picks up new image)
cd infrastructure
make deploy-benny

# Deploy Lambda (for manual testing)
cd infrastructure
make deploy-stack STACK=Dev-BennyTrader
```

## Monitoring

### Key Metrics to Watch
- **Win Rate**: Should be >52% long-term (check learning params)
- **ROI**: Should be positive (check bankroll snapshots)
- **Bet Volume**: Should place 3-8 bets per day during season
- **Lock Duration**: Should release within 5 minutes

### Weekly Report
Benny sends weekly performance reports every Monday at 9 AM ET to glogankaranovich@gmail.com.

### Dashboard
View real-time performance at: https://carpoolbets.com/benny-dashboard
