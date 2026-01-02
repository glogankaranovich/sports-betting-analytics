# Carpool Bets - Infrastructure Management
.PHONY: help install build test deploy-dev deploy-pipeline clean

# Default target
help:
	@echo "🎯 Carpool Bets Infrastructure Commands:"
	@echo ""
	@echo "📦 Setup:"
	@echo "  make install     - Install CDK dependencies"
	@echo "  make build       - Build TypeScript"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test        - Run infrastructure unit tests"
	@echo "  make test-backend - Run backend unit tests"
	@echo "  make test-all    - Run all tests (infrastructure + backend)"
	@echo ""
	@echo "🚀 Deployment:"
	@echo "  make deploy-dev  - Deploy to dev environment (manual)"
	@echo "  make deploy-pipeline - Deploy pipeline (auto beta/prod)"
	@echo ""
	@echo "🔍 Monitoring:"
	@echo "  make list-stacks - List stacks in all accounts"
	@echo "  make pipeline-status - Check pipeline status"
	@echo "  make pipeline-history - Show pipeline execution history"
	@echo "  make verify-dev  - Verify dev resources exist"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean       - Clean build artifacts"

# Install dependencies
install:
	@echo "📦 Installing CDK dependencies..."
	npm ci

# Build TypeScript
build:
	@echo "🔨 Building TypeScript..."
	npm run build

# Run unit tests
test: build
	@echo "🧪 Running infrastructure unit tests..."
	npm test

# Run backend unit tests
test-backend:
	@echo "🧪 Running backend unit tests..."
	cd ../backend && DYNAMODB_TABLE=test-table python3 -m unittest test_api_handler test_ml_models test_prediction_tracker test_odds_collector -v

# Run all tests (infrastructure + backend)
test-all: build test-backend
	@echo "🧪 Running infrastructure unit tests..."
	npm test

# Deploy to dev environment (manual)
deploy-dev: build test
	@echo "🚀 Deploying to dev environment..."
	AWS_PROFILE=sports-betting-dev cdk deploy --context environment=dev --require-approval never --all

# Run integration tests against dev environment
verify-dev: 
	@echo "🧪 Running integration tests..."
	cd ../backend && AWS_PROFILE=sports-betting-dev ENVIRONMENT=dev python3 test_integration.py

# Deploy pipeline (for beta/prod automation)
deploy-pipeline: clean build test
	@echo "🚀 Deploying pipeline..."
	AWS_PROFILE=sports-betting-pipeline cdk deploy --context pipeline=true --require-approval never

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf cdk.out/
	rm -rf lib/*.js
	rm -rf lib/*.d.ts
	rm -rf bin/*.js
	rm -rf bin/*.d.ts

# List stacks in all accounts
list-stacks:
	@echo "📋 Dev Account Stacks:"
	@AWS_PROFILE=sports-betting-dev aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[].StackName' --output table
	@echo "📋 Pipeline Account Stacks:"
	@AWS_PROFILE=sports-betting-pipeline aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[].StackName' --output table
	@echo "📋 Staging Account Stacks:"
	@AWS_PROFILE=sports-betting-staging aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[].StackName' --output table
	@echo "📋 Production Account Stacks:"
	@AWS_PROFILE=sports-betting-prod aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[].StackName' --output table

# Check pipeline status
pipeline-status:
	@echo "🔍 Checking pipeline status..."
	@AWS_PROFILE=sports-betting-pipeline aws codepipeline get-pipeline-state --name CarpoolBetsPipeline --query 'stageStates[].{Stage:stageName,Status:latestExecution.status}' --output table
	@echo ""
	@echo "📊 Current execution details:"
	@AWS_PROFILE=sports-betting-pipeline aws codepipeline list-pipeline-executions --pipeline-name CarpoolBetsPipeline --max-items 1 --query 'pipelineExecutionSummaries[0].{Status:status,StartTime:startTime,LastUpdate:lastUpdateTime}' --output table

# Get pipeline execution history
pipeline-history:
	@echo "📜 Pipeline execution history (last 5):"
	@AWS_PROFILE=sports-betting-pipeline aws codepipeline list-pipeline-executions --pipeline-name CarpoolBetsPipeline --max-items 5 --query 'pipelineExecutionSummaries[].{Status:status,StartTime:startTime,ExecutionId:pipelineExecutionId}' --output table
