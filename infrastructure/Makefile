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
	@echo "  make workflow-check - Run full quality check (lint + test + build)"
	@echo "  make test        - Run infrastructure unit tests"
	@echo "  make test-backend - Run backend unit tests"
	@echo "  make test-coverage - Run backend tests with coverage report"
	@echo "  make test-coverage-module MODULE=name - Run coverage for specific module"
	@echo "  make test-all    - Run all tests (infrastructure + backend)"
	@echo ""
	@echo "🚀 Deployment:"
	@echo "  make deploy-dev  - Deploy to dev environment (manual)"
	@echo "  make deploy-stack STACK=name - Deploy specific stack to dev"
	@echo "  make deploy-pipeline - Deploy pipeline (auto beta/prod)"
	@echo ""
	@echo "🔍 Monitoring:"
	@echo "  make list-stacks - List stacks in all accounts"
	@echo "  make pipeline-status - Check pipeline status"
	@echo "  make pipeline-history - Show pipeline execution history"
	@echo "  make verify-dev  - Verify dev resources exist (quick smoke test)"
	@echo "  make verify-dev-all - Run all integration tests (comprehensive)"
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

# Full workflow check (lint + test + build)
workflow-check:
	@echo "🔍 Running full workflow check..."
	@echo "1️⃣ Linting backend code..."
	cd ../backend && python3 -m black . --check && python3 -m isort . --check-only
	@echo "2️⃣ Running backend tests..."
	cd ../backend && DYNAMODB_TABLE=test-table python3 -m pytest tests/unit/ -v
	@echo "3️⃣ Building infrastructure..."
	npm run build
	@echo "✅ Workflow check complete!"

# Run unit tests
test: build
	@echo "🧪 Running infrastructure unit tests..."
	npm test -- --passWithNoTests

# Run backend unit tests
test-backend:
	@echo "🧪 Running backend unit tests..."
	cd ../backend && DYNAMODB_TABLE=test-table python3 -m pytest tests/unit/ -v

# Run backend tests with coverage
test-coverage:
	@echo "📊 Running backend tests with coverage..."
	cd ../backend && DYNAMODB_TABLE=test-table python3 -m pytest tests/unit/ --cov=. --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "📈 Coverage report generated in backend/htmlcov/index.html"

# Run coverage for specific module
test-coverage-module:
	@echo "📊 Running coverage for specific module..."
	@echo "Usage: make test-coverage-module MODULE=user_model_executor"
	cd ../backend && DYNAMODB_TABLE=test-table python3 -m pytest tests/unit/test_$(MODULE).py --cov=$(MODULE) --cov-report=term-missing

# Run backend integration tests (requires AWS credentials and network access)
test-backend-integration:
	@echo "🧪 Running backend integration tests..."
	cd ../backend && python3 -m pytest tests/integration/ -v

# Run all tests (infrastructure + backend)
test-all: build test-backend
	@echo "🧪 Running infrastructure unit tests..."
	npm test

# Deploy to dev environment (manual)
deploy-dev: build test
	@echo "🚀 Deploying to dev environment..."
	AWS_PROFILE=sports-betting-dev cdk deploy --context environment=dev --require-approval never --all

# Deploy specific stack to dev environment
deploy-stack: build
	@echo "🚀 Deploying $(STACK) to dev environment..."
	@if [ -z "$(STACK)" ]; then echo "❌ Error: STACK parameter required. Usage: make deploy-stack STACK=Dev-StackName"; exit 1; fi
	AWS_PROFILE=sports-betting-dev cdk deploy --context environment=dev --require-approval never $(STACK)

# Run integration tests against dev environment
verify-dev: 
	@echo "🧪 Running integration tests..."
	cd ../backend && AWS_PROFILE=sports-betting-dev ENVIRONMENT=dev python3 tests/integration/test_integration.py

# Run all integration tests against dev environment
verify-dev-all:
	@echo "🧪 Running all integration tests..."
	cd ../backend && AWS_PROFILE=sports-betting-dev ENVIRONMENT=dev python3 -m pytest tests/integration/ -v

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
