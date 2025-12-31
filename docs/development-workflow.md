# Sports Betting Analytics - Development Workflow

## 🎯 Daily Development Process

### Step-by-Step Workflow
1. **Identify Task**: Review PROJECT_STATUS.md and select next task
2. **Update Status**: Mark task as "In Progress" in PROJECT_STATUS.md
3. **Implement**: Write code for the task
4. **Test**: Create unit tests and integration tests as needed
5. **Build Check**: Run `make workflow-check` to verify everything works
6. **Fix Issues**: Address any linting, test, or build failures
7. **Deploy Dev** (if CDK changes): Deploy to dev stack and verify
8. **Update Docs**: Mark task complete in PROJECT_STATUS.md
9. **Log Learnings**: Add insights to TROUBLESHOOTING_AND_LESSONS.md
10. **Commit & Push**: Commit changes and push to trigger pipeline
11. **Monitor Pipeline**: Check deployment status asynchronously

### Quality Gates
- **All tests pass** before committing
- **High test coverage** maintained
- **Code automatically linted** and fixed
- **Build succeeds** on all components
- **Dev deployment works** (for infrastructure changes)

## 📝 Task Management

### PROJECT_STATUS.md Format
Tasks should be tracked with these statuses:
- **⏳ Not Started** - Task identified but not begun
- **🚧 In Progress** - Currently working on this task
- **✅ Complete** - Task finished and tested
- **🔄 Testing** - Implementation done, testing in progress
- **🚀 Deploying** - Deployed to dev, verifying functionality

### Status Update Commands
```bash
# Quick status check
make status-check

# Update task status (interactive)
make update-task-status
```

## 🧪 Testing & Quality Assurance

### Automated Quality Checks
```bash
# Run full workflow check (linting, tests, build)
make workflow-check

# Individual components
make lint-fix      # Auto-fix linting issues
make test         # Run all tests
make build        # Build all components
```

### Test Coverage Requirements
- **Unit tests** for all new code
- **Integration tests** for API endpoints and data flows
- **High coverage** maintained (aim for >90%)
- **All tests pass** before any commit

### Code Quality Standards
- **Automatic linting** with auto-fix enabled
- **Python**: black + flake8 + isort
- **TypeScript**: ESLint + Prettier
- **Consistent formatting** across all files

## 🚀 Deployment & Pipeline Monitoring

### Development Environment
```bash
# Deploy to dev (manual only)
make deploy-dev

# Verify dev deployment
make verify-dev

# Check dev resources
make check-dev-status
```

### Pipeline Monitoring
```bash
# Check pipeline status
make check-pipeline

# Get pipeline logs (if failed)
make pipeline-logs

# Monitor deployment progress
make monitor-deployment
```

### Environment Strategy
- **Dev**: Manual deployment for testing with real AWS resources
- **Staging/Prod**: Automatic deployment through pipeline only
- **Pipeline**: Triggers on push to main branch

## 🔄 Example Development Session

1. **Start**: Review current status and recent lessons
2. **Plan**: "Add NBA API integration for game data"
3. **Test**: Write tests for API client and data parsing
4. **Implement**: FastAPI endpoints and data models
5. **Verify**: Deploy to Dev, test API endpoints
6. **Document**: Update status with completed work
7. **Capture**: Log decision rationale and any challenges
8. **Commit**: "feat: Add NBA API integration for game data"
9. **Push**: Immediate push to GitHub
10. **Update**: Status document and lessons learned

### Session End Checklist
- [ ] All tests passing
- [ ] Code committed and pushed
- [ ] Status document updated
- [ ] Lessons learned captured
- [ ] Next step clearly defined
- [ ] Architecture decisions documented

## 🏗️ Project-Specific Patterns

### Python Development
- Use **virtual environments** for dependency isolation
- Follow **PEP 8** style guidelines
- Use **type hints** for better code documentation
- **pytest** for testing framework

### FastAPI Patterns
- **Dependency injection** for database connections
- **Pydantic models** for request/response validation
- **Async/await** for I/O operations
- **Background tasks** for long-running operations

### ML Pipeline
- **Data validation** at ingestion points
- **Model versioning** for reproducibility
- **Feature engineering** documentation
- **Performance monitoring** for model drift

### Sports Data Integration
- **Rate limiting** for API calls
- **Data caching** to reduce API usage
- **Error handling** for API failures
- **Data quality checks** for incoming data

---

*Created: 2025-12-28*  
*Status: Development Workflow Defined*  
*Next: Apply this workflow to current development phase*
