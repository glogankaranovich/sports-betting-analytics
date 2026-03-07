# ECS Migration - Docker Build and Deploy Guide

## Overview

**Dev**: Manual Docker build and push  
**Beta/Prod**: Automated via CodePipeline

## Dev Environment (Manual)

### Prerequisites

1. AWS CLI configured with `sports-betting-dev` profile
2. Docker installed and running
3. ECR repository created (done by CDK)

## Step 1: Deploy ECS Infrastructure

```bash
cd infrastructure
npm run cdk deploy Dev-EcsCluster Dev-EcsTasks Dev-EcsSchedules --profile sports-betting-dev
```

This creates:
- ECS Fargate cluster
- ECR repository
- Task definitions
- EventBridge schedules

## Step 2: Get ECR Repository URI

```bash
aws ecr describe-repositories \
  --repository-names dev-batch-jobs \
  --profile sports-betting-dev \
  --region us-east-1 \
  --query 'repositories[0].repositoryUri' \
  --output text
```

Save this URI (e.g., `123456789.dkr.ecr.us-east-1.amazonaws.com/dev-batch-jobs`)

## Step 3: Authenticate Docker to ECR

```bash
aws ecr get-login-password \
  --region us-east-1 \
  --profile sports-betting-dev | \
docker login \
  --username AWS \
  --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
```

## Step 4: Build Docker Image

```bash
# From project root
docker build -t dev-batch-jobs:latest .
```

## Step 5: Tag Image for ECR

```bash
docker tag dev-batch-jobs:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/dev-batch-jobs:latest
```

## Step 6: Push Image to ECR

```bash
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/dev-batch-jobs:latest
```

## Step 7: Test ECS Tasks Manually

### Test Props Collector
```bash
aws ecs run-task \
  --cluster dev-batch-processing \
  --task-definition Dev-EcsTasks-PropsCollectorTask \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],assignPublicIp=ENABLED}" \
  --profile sports-betting-dev \
  --region us-east-1
```

### Test Analysis Generator (NBA, consensus, games)
```bash
aws ecs run-task \
  --cluster dev-batch-processing \
  --task-definition Dev-EcsTasks-AnalysisGeneratorTask \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],assignPublicIp=ENABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "AnalysisGenerator",
      "environment": [
        {"name": "SPORT", "value": "basketball_nba"},
        {"name": "MODEL", "value": "consensus"},
        {"name": "BET_TYPE", "value": "games"}
      ]
    }]
  }' \
  --profile sports-betting-dev \
  --region us-east-1
```

### Test Benny Trader
```bash
aws ecs run-task \
  --cluster dev-batch-processing \
  --task-definition Dev-EcsTasks-BennyTraderTask \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],assignPublicIp=ENABLED}" \
  --profile sports-betting-dev \
  --region us-east-1
```

## Step 8: Check Logs

```bash
# Get task ARN from run-task output, then:
aws logs tail /aws/ecs/props-collector --follow --profile sports-betting-dev
aws logs tail /aws/ecs/analysis-generator --follow --profile sports-betting-dev
aws logs tail /aws/ecs/benny-trader --follow --profile sports-betting-dev
```

## Step 9: Verify Data in DynamoDB

```bash
# Check for new props
aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --index-name PropsGSI \
  --key-condition-expression "gsi_pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"PROPS#basketball_nba"}}' \
  --limit 5 \
  --profile sports-betting-dev

# Check for new analyses
aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"ANALYSIS#basketball_nba"}}' \
  --limit 5 \
  --profile sports-betting-dev
```

## Troubleshooting

### Image not found
- Ensure image was pushed successfully
- Check ECR repository name matches task definition
- Verify image tag is `latest`

### Task fails to start
- Check CloudWatch logs for errors
- Verify IAM roles have correct permissions
- Ensure secrets exist in Secrets Manager

### Network errors
- Verify subnet has internet access (NAT gateway or public subnet)
- Check security group allows outbound traffic
- Ensure `assignPublicIp=ENABLED` for public subnets

## Quick Deploy Script

Create `scripts/deploy-ecs.sh`:

```bash
#!/bin/bash
set -e

PROFILE="sports-betting-dev"
REGION="us-east-1"
STAGE="dev"

echo "Getting ECR repository URI..."
REPO_URI=$(aws ecr describe-repositories \
  --repository-names ${STAGE}-batch-jobs \
  --profile $PROFILE \
  --region $REGION \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "Repository: $REPO_URI"

echo "Authenticating Docker to ECR..."
aws ecr get-login-password \
  --region $REGION \
  --profile $PROFILE | \
docker login --username AWS --password-stdin $REPO_URI

echo "Building Docker image..."
docker build -t ${STAGE}-batch-jobs:latest .

echo "Tagging image..."
docker tag ${STAGE}-batch-jobs:latest $REPO_URI:latest

echo "Pushing image to ECR..."
docker push $REPO_URI:latest

echo "Done! Image pushed to $REPO_URI:latest"
```

Make executable:
```bash
chmod +x scripts/deploy-ecs.sh
./scripts/deploy-ecs.sh
```

---

## Beta/Prod Environments (Automated via Pipeline)

### How It Works

The CodePipeline automatically builds and pushes Docker images for beta and prod:

1. **Code pushed to `main` branch** → Pipeline triggers
2. **Synth step** → CDK synthesizes infrastructure
3. **Beta pre-deployment** → Builds Docker image, pushes to beta ECR
4. **Beta deployment** → Deploys ECS stacks with new image
5. **Beta post-deployment** → Runs integration tests
6. **Prod pre-deployment** → Builds Docker image, pushes to prod ECR
7. **Prod deployment** → Deploys ECS stacks with new image

### Pipeline Configuration

Each stage has a pre-deployment step that:
- Builds Docker image from Dockerfile
- Authenticates to stage-specific ECR repository
- Tags image with `latest`
- Pushes to ECR (`beta-batch-jobs` or `prod-batch-jobs`)

**Key Points:**
- Each environment has its own ECR repository
- Images are built fresh for each deployment
- No manual Docker commands needed for beta/prod
- Pipeline has privileged mode enabled for Docker builds

### Monitoring Pipeline

```bash
# Check pipeline status
aws codepipeline get-pipeline-state \
  --name CarpoolBetsPipeline \
  --profile sports-betting-dev

# View CodeBuild logs
aws logs tail /aws/codebuild/CarpoolBetsPipeline-BuildDockerImageBeta \
  --follow \
  --profile sports-betting-dev
```

### Manual Override (Emergency)

If you need to manually push to beta/prod ECR:

```bash
# For Beta
export STAGE=beta
export ACCOUNT_ID=<beta-account-id>
export REPO_URI=$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/beta-batch-jobs

aws ecr get-login-password --region us-east-1 --profile sports-betting-beta | \
  docker login --username AWS --password-stdin $REPO_URI

docker build -t beta-batch-jobs:latest .
docker tag beta-batch-jobs:latest $REPO_URI:latest
docker push $REPO_URI:latest
```

---

## Summary

| Environment | Docker Build | Deployment | ECR Repo |
|-------------|--------------|------------|----------|
| **Dev** | Manual (scripts/deploy-ecs.sh) | Manual CDK | dev-batch-jobs |
| **Beta** | Automated (pipeline pre-step) | Automated (pipeline) | beta-batch-jobs |
| **Prod** | Automated (pipeline pre-step) | Automated (pipeline) | prod-batch-jobs |

