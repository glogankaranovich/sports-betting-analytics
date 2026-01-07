# System Architecture

## Overview

The Sports Betting Analytics System is a cloud-native ML platform built on AWS with real-time data collection, AI-powered analysis models, and a modern React frontend.

## Components

### 1. Data Collection Layer
- **Odds Collector**: Smart updating system with parallel processing (3 concurrent workers)
- **Lambda Functions**: Serverless data processing with optimized storage logic
- **Scheduler**: Sport-specific EventBridge rules (NBA/NFL twice daily)
- **DynamoDB**: Real-time storage with GSI indexes and smart deduplication

### 2. Machine Learning Analysis Layer
- **12 Specialized Models**: Management, momentum, stats, weather, sentiment, referee, etc.
- **Dynamic Weighting System**: Performance-based model importance adjustment
- **Outcome Verification**: Continuous learning from actual results
- **Value Bet Detection**: Identifies opportunities through ensemble analysis

### 3. Insight Generation Layer
- **Ensemble Analysis**: Combines weighted model outputs for comprehensive insights
- **Confidence Scoring**: Statistical confidence in analysis results
- **ROI Calculation**: Expected value and return estimation
- **Top Picks Selection**: Highest confidence × ROI opportunities

### 4. API Layer
- **API Gateway**: RESTful endpoints with CORS and rate limiting
- **Lambda Functions**: Serverless API handlers with proper error handling
- **Cognito Authentication**: JWT-based user authentication with protected endpoints
- **Multiple Environments**: Dev, Beta, and Production with separate resources

### 5. Frontend Layer
- **React TypeScript**: Modern web interface displaying analysis insights
- **AWS Amplify**: Authentication integration and hosting
- **Responsive Design**: Mobile-friendly with glassmorphism styling
- **Real-time Data**: Analysis results, confidence scores, and insight tracking

### 6. Infrastructure Layer
- **AWS CDK**: Infrastructure as Code with TypeScript
- **CI/CD Pipeline**: Automated deployment with rollback capabilities
- **Multi-Environment**: Separate stacks for dev/beta/prod
- **Monitoring**: CloudWatch logs and metrics

## Data Flow

1. **Collection**: The Odds API → Lambda (parallel processing) → Smart updating → DynamoDB
2. **ML Processing**: DynamoDB → PredictionTracker → ML Models → Predictions → DynamoDB
3. **API Serving**: Frontend → API Gateway → Lambda → DynamoDB → Predictions/Data
4. **User Interface**: React → Amplify Auth → Protected APIs → Real-time Display
5. **Scheduling**: EventBridge (sport-specific) → Lambda (staggered collection)

## Performance Optimizations

### Smart Updating System
- **Change Detection**: Compares existing vs new odds data before storage
- **Historical Snapshots**: Only creates records when odds actually change
- **Storage Efficiency**: Reduces data volume by ~75% compared to naive collection
- **DynamoDB Operations**: Uses GetItem for comparison, PutItem only when needed

### Parallel Processing
- **Concurrent Workers**: ThreadPoolExecutor with 3 concurrent API calls
- **Reduced Latency**: Props collection time reduced from 300+ seconds to manageable duration
- **Lambda Optimization**: Stays within timeout limits while maximizing throughput
- **Error Handling**: Graceful degradation when individual API calls fail

### Intelligent Scheduling
- **Sport-Specific Rules**: NBA/NFL collected separately with staggered timing
- **Frequency Optimization**: Reduced from every 4 hours to twice daily
- **Resource Distribution**: Spreads API load across different time windows
- **7-Day Filtering**: Only processes games within next 7 days to reduce data volume

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
- **Sports**: NFL, NBA with sport-specific scheduling
- **Bookmakers**: 8+ major sportsbooks (BetMGM, BetRivers, Bovada, etc.)
- **Markets**: Moneyline, spreads, totals, player props
- **Update Frequency**: NBA/NFL twice daily (8AM/8PM odds, 10AM/10PM props)
- **Smart Storage**: Only creates records when odds actually change

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
