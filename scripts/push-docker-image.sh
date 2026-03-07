#!/bin/bash
set -e

PROFILE="sports-betting-dev"
REGION="us-east-1"
STAGE="dev"

echo "📦 Getting ECR repository URI..."
REPO_URI=$(aws ecr describe-repositories \
  --repository-names ${STAGE}-batch-jobs \
  --profile $PROFILE \
  --region $REGION \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "Repository: $REPO_URI"

echo ""
echo "🔐 Authenticating Docker to ECR..."
aws ecr get-login-password \
  --region $REGION \
  --profile $PROFILE | \
docker login --username AWS --password-stdin $REPO_URI

echo ""
echo "🐳 Building Docker image..."
docker build --platform linux/amd64 -t ${STAGE}-batch-jobs:latest .

echo ""
echo "🏷️  Tagging image..."
docker tag ${STAGE}-batch-jobs:latest $REPO_URI:latest

echo ""
echo "⬆️  Pushing image to ECR..."
docker push $REPO_URI:latest

echo ""
echo "✅ Done! Image pushed to $REPO_URI:latest"
