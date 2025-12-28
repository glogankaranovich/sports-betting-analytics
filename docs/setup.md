# Development Setup Guide

## Prerequisites

- Python 3.9+
- Node.js 16+
- AWS CLI configured
- Git

## Backend Setup

1. **Create virtual environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment variables**:
   Create `.env` file in backend directory:
   ```env
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   DYNAMODB_TABLE_PREFIX=sports-betting
   S3_BUCKET_RAW=sports-betting-raw-data
   S3_BUCKET_ASSETS=sports-betting-assets
   JWT_SECRET_KEY=your_jwt_secret
   REDIS_URL=redis://localhost:6379
   ```

4. **Start development server**:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

## Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Environment variables**:
   Create `.env` file in frontend directory:
   ```env
   REACT_APP_API_URL=http://localhost:8000
   REACT_APP_WS_URL=ws://localhost:8000/ws
   ```

3. **Start development server**:
   ```bash
   npm start
   ```

## AWS Infrastructure Setup

1. **Install AWS CDK**:
   ```bash
   npm install -g aws-cdk
   ```

2. **Deploy infrastructure**:
   ```bash
   cd infrastructure
   npm install
   cdk bootstrap
   cdk deploy
   ```

## Database Setup

1. **Create DynamoDB tables** (via CDK or manually):
   - sports-betting-bets
   - sports-betting-predictions
   - sports-betting-data
   - sports-betting-users

2. **Create S3 buckets**:
   - sports-betting-raw-data
   - sports-betting-assets

## Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
cd tests/integration
python -m pytest
```

## Development Workflow

1. **Feature Development**:
   - Create feature branch: `git checkout -b feature/your-feature`
   - Make changes and commit
   - Push and create pull request

2. **Code Quality**:
   - Run linting: `flake8 backend/` and `npm run lint` in frontend
   - Run tests before committing
   - Follow conventional commit messages

3. **Local Testing**:
   - Test API endpoints with Postman or curl
   - Test frontend functionality
   - Verify AWS integrations

## Troubleshooting

### Common Issues:

1. **AWS Credentials**: Ensure AWS CLI is configured with proper permissions
2. **Port Conflicts**: Change ports in environment variables if needed
3. **Dependencies**: Clear node_modules and reinstall if issues persist
4. **Database**: Verify DynamoDB tables exist and have correct permissions

### Useful Commands:

```bash
# Check API health
curl http://localhost:8000/health

# View DynamoDB tables
aws dynamodb list-tables

# Check S3 buckets
aws s3 ls

# View application logs
tail -f backend/logs/app.log
```
