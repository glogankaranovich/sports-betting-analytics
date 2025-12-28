# System Architecture

## Overview

The Sports Betting Analytics System is designed as a microservices architecture with the following components:

## Components

### 1. Data Collection Layer
- **Web Crawler**: Scrapes sports statistics from various sources
- **API Integrations**: Connects to sports data APIs
- **Scheduler**: Manages periodic data collection tasks

### 2. Data Storage Layer
- **DynamoDB**: Stores structured data (bets, predictions, outcomes)
- **S3**: Stores raw data files and historical datasets
- **Redis**: Caching layer for frequently accessed data

### 3. Processing Layer
- **ML Engine**: Generates predictions with probability scores
- **Data Processor**: Cleans and transforms raw data
- **Feedback Loop**: Updates models based on bet outcomes

### 4. API Layer
- **FastAPI**: RESTful API for all system interactions
- **Authentication**: JWT-based user authentication
- **Rate Limiting**: Prevents API abuse

### 5. Frontend Layer
- **React App**: Web interface for users
- **Real-time Updates**: WebSocket connections for live data
- **Responsive Design**: Mobile-friendly interface

## Data Flow

1. **Collection**: Crawler gathers sports data → S3 (raw) → Processing
2. **Processing**: Raw data → ML Engine → Predictions → DynamoDB
3. **Betting**: User creates bet → API → DynamoDB
4. **Feedback**: Bet outcome → ML Engine → Model update
5. **Display**: Frontend → API → Processed data → User interface

## Technology Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **ML**: scikit-learn, pandas, numpy
- **Database**: AWS DynamoDB, Redis
- **Storage**: AWS S3
- **Frontend**: React, TypeScript, Material-UI
- **Infrastructure**: AWS CDK, Docker
- **Monitoring**: CloudWatch, Prometheus
