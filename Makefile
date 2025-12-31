# Sports Betting Analytics - Makefile
.PHONY: help install test build deploy clean dev test-api test-infra bootstrap-dev deploy-dev deploy-pipeline

# Default target
help:
	@echo "🎯 Sports Betting Analytics - Available Commands:"
	@echo ""
	@echo "📦 Setup & Installation:"
	@echo "  make install          - Install all dependencies (backend + infrastructure)"
	@echo "  make install-backend  - Install backend Python dependencies"
	@echo "  make install-infra    - Install infrastructure CDK dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test            - Run all tests (API + Infrastructure)"
	@echo "  make test-api        - Run backend API tests"
	@echo "  make test-infra      - Run CDK infrastructure tests"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make dev             - Start API development server"
	@echo "  make build           - Build all components"
	@echo ""
	@echo "☁️  Infrastructure:"
	@echo "  make bootstrap-dev   - Bootstrap CDK in dev account"
	@echo "  make deploy-dev      - Deploy to dev environment"
	@echo "  make deploy-pipeline - Deploy pipeline (staging/prod automation)"
	@echo "  make destroy-dev     - Destroy dev infrastructure"
	@echo "  make diff-dev        - Show dev infrastructure changes"
	@echo "  make synth           - Generate CloudFormation template"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean           - Clean build artifacts"

# Installation targets
install: install-backend install-infra
	@echo "✅ All dependencies installed!"

install-backend:
	@echo "📦 Installing backend dependencies..."
	cd backend && python3 -m venv venv
	cd backend && source venv/bin/activate && pip install -r requirements.txt && pip install -r requirements-test.txt

install-infra:
	@echo "📦 Installing infrastructure dependencies..."
	cd infrastructure && npm install

# Testing targets
test: test-crawler test-integration test-referee test-infra
	@echo "✅ All tests passed!"

test-unit:
	@echo "🧪 Running unit tests..."
	@if [ -n "$$(find tests/unit -name '*.py' 2>/dev/null)" ]; then \
		cd backend && source venv/bin/activate && cd .. && python -m pytest tests/unit/ -v; \
	else \
		echo "No unit tests found in tests/unit/ - using main test file instead"; \
		cd backend && source venv/bin/activate && cd .. && python -m pytest tests/test_crawler.py -v; \
	fi

test-integration:
	@echo "🧪 Running integration tests..."
	cd backend && source venv/bin/activate && cd .. && python -m pytest tests/integration/ -v

test-crawler:
	@echo "🧪 Running crawler tests..."
	cd backend && source venv/bin/activate && cd .. && python -m pytest tests/test_crawler.py -v

test-referee:
	@echo "🧪 Running referee crawler tests..."
	cd backend && source venv/bin/activate && cd .. && python -m pytest tests/test_referee_crawler.py -v

test-api: test-crawler test-integration test-referee
	@echo "✅ API tests completed!"

test-infra:
	@echo "🧪 Running infrastructure tests..."
	cd infrastructure && npx jest --forceExit

workflow-check: test build
	@echo "✅ Workflow check completed successfully!"

# Development targets
dev:
	@echo "🚀 Starting development server..."
	@echo "📖 API docs: http://localhost:8000/docs"
	@echo "🔍 Health check: http://localhost:8000/health"
	cd backend && source venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

build:
	@echo "🔨 Building all components..."
	cd infrastructure && npm run build

# Infrastructure targets
bootstrap-dev:
	@echo "🔧 Bootstrapping CDK in dev account..."
	@aws sts get-caller-identity --profile sports-betting-dev --query 'Account' --output text | xargs -I {} echo "📋 Bootstrapping dev account: {}"
	cd infrastructure && npx cdk bootstrap aws://540477485595/us-east-1 --profile sports-betting-dev

deploy-dev: test-infra build
	@echo "☁️  Deploying to dev environment..."
	@aws sts get-caller-identity --profile sports-betting-dev --query 'Account' --output text | xargs -I {} echo "📋 Deploying to dev account: {}"
	cd infrastructure && npx cdk deploy dev/Infrastructure --app "npx ts-node bin/dev.ts" --profile sports-betting-dev --require-approval never
	@echo "✅ Dev infrastructure deployed!"
	@echo "📋 Verifying resources..."
	@make verify-dev

deploy-pipeline: test-infra build
	@echo "☁️  Deploying pipeline (staging/prod automation)..."
	@aws sts get-caller-identity --profile sports-betting-pipeline --query 'Account' --output text | xargs -I {} echo "📋 Deploying to pipeline account: {}"
	@echo "🔧 Bootstrapping staging account..."
	@aws sts get-caller-identity --profile sports-betting-staging --query 'Account' --output text | xargs -I {} echo "📋 Bootstrapping staging account: {}"
	cd infrastructure && npx cdk bootstrap aws://352312075009/us-east-1 --profile sports-betting-staging --trust 083314012659 --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess
	@echo "🔧 Bootstrapping prod account..."
	@aws sts get-caller-identity --profile sports-betting-prod --query 'Account' --output text | xargs -I {} echo "📋 Bootstrapping prod account: {}"
	cd infrastructure && npx cdk bootstrap aws://198784968537/us-east-1 --profile sports-betting-prod --trust 083314012659 --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess
	@echo "🚀 Deploying pipeline..."
	cd infrastructure && npx cdk deploy --profile sports-betting-pipeline --require-approval never
	@echo "✅ Pipeline deployed!"

destroy-dev:
	@echo "🗑️  Destroying dev infrastructure..."
	@read -p "Are you sure you want to destroy dev AWS resources? (y/N): " confirm && [ "$$confirm" = "y" ]
	cd infrastructure && npx cdk destroy --app "npx ts-node bin/dev.ts" --profile sports-betting-dev --force

diff-dev:
	@echo "📊 Showing dev infrastructure changes..."
	cd infrastructure && npx cdk diff --app "npx ts-node bin/dev.ts" --profile sports-betting-dev

synth:
	@echo "📄 Generating CloudFormation template..."
	cd infrastructure && npx cdk synth

verify-dev:
	@echo "🔍 Verifying dev resources..."
	@aws dynamodb list-tables --profile sports-betting-dev --query 'TableNames[?contains(@, `sports-betting`) && contains(@, `dev`)]' --output table
	@aws s3 ls --profile sports-betting-dev | grep sports-betting | grep dev

# Utility targets
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf backend/venv
	rm -rf infrastructure/node_modules
	rm -rf infrastructure/cdk.out
	rm -rf backend/__pycache__
	rm -rf tests/__pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

# Quick commands for common workflows
quick-test: test-api
	@echo "✅ Quick API test completed!"

setup: install test
	@echo "🎉 Project setup complete! Run 'make dev' to start development."

# Check prerequisites
check-aws:
	@aws sts get-caller-identity > /dev/null || (echo "❌ AWS credentials not configured. Run 'aws configure' first." && exit 1)

check-python:
	@python3 --version > /dev/null || (echo "❌ Python 3 not found. Please install Python 3.9+." && exit 1)

check-node:
	@node --version > /dev/null || (echo "❌ Node.js not found. Please install Node.js 16+." && exit 1)

check-deps: check-python check-node check-aws
	@echo "✅ All prerequisites satisfied!"
