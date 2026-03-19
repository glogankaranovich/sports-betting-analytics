# Infrastructure (AWS CDK)

> 44 CDK stacks in TypeScript defining all AWS resources.

## Directory
`infrastructure/lib/` (TypeScript source), `infrastructure/bin/infrastructure.ts` (app entry)

## Key Stacks

### Core
| Stack | Purpose |
|-------|---------|
| `dynamodb-stack.ts` | DynamoDB table (`carpool-bets-v2-{env}`) with GSIs |
| `auth-stack.ts` | Cognito user pool and identity pool |
| `pipeline-stack.ts` | CodePipeline CI/CD with Beta stage |
| `carpool-bets-stage.ts` | Stage composition — wires all stacks together |

### Benny Trader
| Stack | Purpose |
|-------|---------|
| `benny-trader-stack.ts` | Benny Trader Lambda function |
| `benny-trader-schedule-stack.ts` | EventBridge schedule (currently DISABLED) |
| `ecs-task-stack.ts` | ECS Fargate task definition for Benny Trader |
| `ecs-cluster-stack.ts` | ECS cluster (`dev-batch-processing`) |
| `ecs-schedule-stack.ts` | ECS scheduled tasks (4x daily) |
| `ecs-alarms-stack.ts` | CloudWatch alarms for ECS tasks |
| `coaching-memo-stack.ts` | Daily coaching memo Lambda (8:30 AM ET) |

### Data Collection
| Stack | Purpose |
|-------|---------|
| `odds-collector-stack.ts` | Odds collector Lambda |
| `odds-collector-schedule-stack.ts` | Odds collection schedules per sport |
| `outcome-collector-stack.ts` | Bet settlement Lambda (every 4h) |
| `player-stats-collector-stack.ts` | Player stats Lambda |
| `team-stats-collector-stack.ts` | Team stats Lambda |
| `season-stats-collector-stack.ts` | Season stats Lambda |
| `schedule-collector-stack.ts` | Game schedule Lambda |
| `injury-collector-stack.ts` | Injury data Lambda |
| `weather-collector-stack.ts` | Weather data Lambda |
| `news-collectors-stack.ts` | News/sentiment Lambda |

### Analysis & Reporting
| Stack | Purpose |
|-------|---------|
| `analysis-generator-stack.ts` | AI analysis Lambda |
| `analysis-generator-schedule-stack.ts` | Analysis schedules per sport/strategy |
| `benny-weekly-reporter-stack.ts` | Weekly/daily reports |
| `benny-ab-reporter-stack.ts` | A/B comparison reports |
| `model-analytics-stack.ts` | Model performance analytics |

### API & Frontend
| Stack | Purpose |
|-------|---------|
| `bet-collector-api-stack.ts` | API Gateway + Lambda for frontend |
| `ai-agent-stack.ts` | AI chat agent Lambda |
| `amplify-stack.ts` | Amplify frontend hosting |

### Other
| Stack | Purpose |
|-------|---------|
| `notification-stack.ts` | SQS + Lambda notification pipeline |
| `compliance-stack.ts` | Compliance logging |
| `monitoring-stack.ts` | CloudWatch dashboards and alarms |
| `email-stack.ts` | SES email configuration |
| `custom-data-stack.ts` | Custom user data Lambda |
| `user-models-stack.ts` | User-defined model execution |
| `season-manager-stack.ts` | Season start/end management |
| `model-comparison-cache-stack.ts` | Model comparison caching |
| `metrics-calculator-stack.ts` | Metrics calculation Lambda |

## Deployment
- **Profile**: `AWS_PROFILE=sports-betting-dev`
- **Region**: `us-east-1`
- **Deploy**: `cd infrastructure && npx cdk deploy <StackName> --profile sports-betting-dev`
- **Makefile**: `infrastructure/Makefile` has convenience targets
