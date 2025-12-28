# Testing Strategy

## Testing Approach

### 1. Local Development Testing
- **Manual API Testing**: Use curl/Postman to test endpoints
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints with mock data
- **Health Checks**: Verify services are running

### 2. Testing Layers

#### Unit Tests (`tests/unit/`)
- Test individual functions in isolation
- Mock external dependencies (AWS, databases)
- Fast execution, no external services needed

#### Integration Tests (`tests/integration/`)
- Test API endpoints end-to-end
- Use test databases/mock AWS services
- Verify data flow between components

#### Manual Testing
- Postman collection for API testing
- Simple test scripts for quick verification

### 3. Test Data Strategy
- Use mock data for unit tests
- Test fixtures for integration tests
- Separate test environment for AWS resources

## Implementation Plan

1. **Start Simple**: Basic health check and endpoint testing
2. **Add Unit Tests**: Test core business logic
3. **Integration Tests**: Full API workflow testing
4. **Automated Testing**: CI/CD pipeline integration

## Quick Verification Methods

### Health Check
```bash
curl http://localhost:8000/health
```

### API Endpoint Testing
```bash
# Test bet creation
curl -X POST http://localhost:8000/api/v1/bets \
  -H "Content-Type: application/json" \
  -d '{"sport":"football","event":"Test Game","bet_type":"moneyline","selection":"Team A","odds":1.5,"amount":100}'
```

### Run Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# All tests
pytest
```
