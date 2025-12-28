#!/bin/bash

echo "🏗️  Sports Betting Analytics - Infrastructure Deployment"

# Check if we're in the right directory
if [ ! -f "infrastructure/cdk.json" ]; then
    echo "❌ Error: Run this from the project root directory"
    exit 1
fi

cd infrastructure

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing CDK dependencies..."
    npm install
fi

# Run tests first
echo "🧪 Running CDK unit tests..."
npm test

if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Fix issues before deploying."
    exit 1
fi

# Build the project
echo "🔨 Building CDK project..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

echo "☁️  Current AWS Account:"
aws sts get-caller-identity --query 'Account' --output text

# Bootstrap CDK if needed (only needs to be done once per account/region)
echo "🚀 Bootstrapping CDK (if needed)..."
npx cdk bootstrap

# Deploy the stack
echo "🚀 Deploying infrastructure..."
npx cdk deploy --require-approval never

if [ $? -eq 0 ]; then
    echo "✅ Infrastructure deployed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Update backend/.env with the output values"
    echo "2. Test API with real AWS resources"
    echo "3. Run integration tests"
else
    echo "❌ Deployment failed!"
    exit 1
fi
