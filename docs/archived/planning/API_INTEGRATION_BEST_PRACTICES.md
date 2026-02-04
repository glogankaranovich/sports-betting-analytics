# API Integration Best Practices

## Secure API Key Management

### Pattern: Environment Variable → Secrets Manager
```python
def get_api_key() -> Optional[str]:
    """Get API key from environment or Secrets Manager."""
    # Local development
    if os.getenv('API_KEY'):
        return os.getenv('API_KEY')
    
    # Production (Lambda)
    secret_arn = os.getenv('API_SECRET_ARN')
    if secret_arn:
        return get_secret_value(secret_arn)
    
    return None
```

### Infrastructure Integration
```typescript
// 1. Reference secret
const apiSecret = secretsmanager.Secret.fromSecretNameV2(
  this, 'ApiSecret', 'app/api-key'
);

// 2. Add to Lambda environment
environment: {
  API_SECRET_ARN: apiSecret.secretArn,
}

// 3. Grant permissions
apiSecret.grantRead(lambdaFunction);
```

### ❌ Never Do
- Hardcode API keys in code
- Store keys in environment files committed to git
- Use different patterns for different APIs

### ✅ Always Do
- Use AWS Secrets Manager for production
- Follow consistent patterns across all APIs
- Grant minimal required permissions

## Testing Async External APIs

### ❌ Wrong: Complex Async Mocking
```python
# Brittle - mocks implementation details
mock_session.get.return_value.__aenter__.return_value = mock_response
```

### ✅ Right: Mock at Abstraction Level
```python
# Clean - mocks public interface
with patch.object(APIClient, '_make_request') as mock_request:
    mock_request.return_value = expected_data
    result = await client.get_data()
```

### Testing Strategy
- **Unit Tests**: Mock external calls
- **Integration Tests**: Use real APIs (separate test suite)
- **Mock public methods**: Not implementation details
- **Test error handling**: Network failures, invalid responses

## Free API Research Strategy

### Verification Checklist
- [ ] Actually free or has hidden costs?
- [ ] Rate limits acceptable?
- [ ] Official API or unofficial/hidden?
- [ ] Long-term reliability?
- [ ] Data quality sufficient?

### Reliability Tiers
1. **Tier 1**: Official APIs with SLAs
2. **Tier 2**: Stable community APIs/libraries
3. **Tier 3**: Unofficial APIs (use as backup only)

### Cost Optimization
- Research free alternatives before paying
- Hybrid approaches often work better
- Keep working systems while adding enhancements
- Document trade-offs (reliability vs cost)

## Infrastructure Patterns

### Incremental API Addition
1. Add secret reference (don't break existing)
2. Add environment variable to Lambda
3. Grant read permissions
4. Update config function
5. Test in isolation before integration

### Environment Parity
- Same pattern for dev/staging/prod
- Use stage-specific secret names when needed
- Consistent permission models
- Infrastructure as code for all environments

## Error Handling

### Graceful Degradation
```python
async def get_data_with_fallback(self):
    try:
        return await self.primary_api.get_data()
    except Exception:
        logger.warning("Primary API failed, using fallback")
        return await self.fallback_api.get_data()
```

### Circuit Breaker Pattern
- Track failure rates
- Temporarily disable failing APIs
- Automatic recovery attempts
- Monitoring and alerting

## Documentation Requirements

### For Each API Integration
- [ ] Authentication method
- [ ] Rate limits and costs
- [ ] Error handling strategy
- [ ] Fallback options
- [ ] Monitoring approach
- [ ] Test coverage

### Infrastructure Changes
- [ ] Secret management approach
- [ ] Permission model
- [ ] Environment variables
- [ ] Deployment considerations

These patterns ensure secure, reliable, and maintainable API integrations.
