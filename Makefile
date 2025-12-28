# Sports Betting Analytics - Makefile
.PHONY: help install test build deploy clean dev test-api test-infra

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
	@echo "  make deploy          - Deploy infrastructure to AWS"
	@echo "  make destroy         - Destroy AWS infrastructure"
	@echo "  make diff            - Show infrastructure changes"
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
test: test-api test-infra
	@echo "✅ All tests passed!"

test-api:
	@echo "🧪 Running API tests..."
	cd backend && source venv/bin/activate && cd .. && python -m pytest tests/ -v

test-infra:
	@echo "🧪 Running infrastructure tests..."
	cd infrastructure && npm test

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
deploy: test-infra build
	@echo "☁️  Deploying infrastructure..."
	@aws sts get-caller-identity --query 'Account' --output text | xargs -I {} echo "📋 Deploying to AWS Account: {}"
	cd infrastructure && npx cdk bootstrap
	cd infrastructure && npx cdk deploy --require-approval never
	@echo "✅ Infrastructure deployed!"
	@echo "📋 Don't forget to update backend/.env with output values"

destroy:
	@echo "🗑️  Destroying infrastructure..."
	@read -p "Are you sure you want to destroy all AWS resources? (y/N): " confirm && [ "$$confirm" = "y" ]
	cd infrastructure && npx cdk destroy --force

diff:
	@echo "📊 Showing infrastructure changes..."
	cd infrastructure && npx cdk diff

synth:
	@echo "📄 Generating CloudFormation template..."
	cd infrastructure && npx cdk synth

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
