# System Architecture

## Overview

The Sports Betting Analytics System is a cloud-native ML platform built on AWS with real-time data collection, AI-powered predictions, and a modern React frontend.

## Components

### 1. Data Collection Layer
- **Odds Collector**: Automated collection from The Odds API every 4 hours
- **Lambda Functions**: Serverless data processing and storage
- **Scheduler**: EventBridge rules for periodic execution
- **DynamoDB**: Real-time storage with GSI indexes for efficient querying

### 2. Machine Learning Layer
- **OddsAnalyzer**: Consensus-based prediction algorithms
- **PredictionTracker**: Model training pipeline with clean data separation
- **Scheduled Generation**: ML models run every 6 hours via Lambda
- **Value Bet Detection**: Identifies opportunities where models disagree with market

### 3. API Layer
- **API Gateway**: RESTful endpoints with CORS and rate limiting
- **Lambda Functions**: Serverless API handlers with proper error handling
- **Cognito Authentication**: JWT-based user authentication with protected endpoints
- **Multiple Environments**: Dev, Beta, and Production with separate resources

### 4. Frontend Layer
- **React TypeScript**: Modern web interface with 4-tab navigation
- **AWS Amplify**: Authentication integration and hosting
- **Responsive Design**: Mobile-friendly with glassmorphism styling
- **Real-time Data**: Pagination, filtering, and loading states

### 5. Infrastructure Layer
- **AWS CDK**: Infrastructure as Code with TypeScript
- **CI/CD Pipeline**: Automated deployment with rollback capabilities
- **Multi-Environment**: Separate stacks for dev/beta/prod
- **Monitoring**: CloudWatch logs and metrics

## Data Flow

1. **Collection**: The Odds API → Lambda → DynamoDB (games, odds, player props)
2. **ML Processing**: DynamoDB → PredictionTracker → ML Models → Predictions → DynamoDB
3. **API Serving**: Frontend → API Gateway → Lambda → DynamoDB → Predictions/Data
4. **User Interface**: React → Amplify Auth → Protected APIs → Real-time Display
5. **Scheduling**: EventBridge → Lambda (data collection + ML generation)

## Technology Stack

### Backend
- **Runtime**: Python 3.11 on AWS Lambda
- **Framework**: Native Lambda handlers with boto3
- **ML**: Custom consensus algorithms with statistical analysis
- **Database**: AWS DynamoDB with GSI indexes
- **Authentication**: AWS Cognito User Pools

### Frontend
- **Framework**: React 18 with TypeScript
- **Styling**: Custom CSS with modern design system
- **Authentication**: AWS Amplify SDK
- **State Management**: React hooks and local state
- **Hosting**: AWS Amplify with automatic deployments

### Infrastructure
- **IaC**: AWS CDK with TypeScript
- **Compute**: AWS Lambda (serverless)
- **Storage**: DynamoDB (NoSQL) with GSI indexes
- **API**: API Gateway with Cognito authorizers
- **Scheduling**: EventBridge rules
- **Monitoring**: CloudWatch logs and metrics
- **CI/CD**: AWS CodePipeline with multi-environment deployment

## Current Capabilities

### Data Sources
- **Sports**: NFL, NBA
- **Bookmakers**: 8+ major sportsbooks (BetMGM, BetRivers, Bovada, etc.)
- **Markets**: Moneyline, spreads, totals, player props
- **Update Frequency**: Every 4 hours for odds, every 6 hours for predictions

### ML Features
- **Game Predictions**: Win probabilities using bookmaker consensus
- **Player Props**: Statistical predictions for key metrics
- **Confidence Scoring**: Model certainty ratings
- **Value Bet Detection**: Market inefficiency identification
- **Historical Storage**: Prediction tracking for performance analysis

### User Interface
- **Games Tab**: Live odds from multiple bookmakers
- **Game Predictions**: AI-generated outcome probabilities
- **Prop Predictions**: Player statistical forecasts
- **Player Props**: Raw prop data with filtering
- **Authentication**: Secure login with test users across environments
