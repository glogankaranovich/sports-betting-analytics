# Changelog

All notable changes to the Carpool Bets platform will be documented in this file.

## [Unreleased]

### Added - February 13, 2026
- **Model Comparison Cache**: Pre-computed model comparison data updated every 15 minutes for faster page loads
- **Inverse Accuracy Support**: Ensemble model now automatically inverts predictions for models that perform better when bet against
- **Betting Strategy Indicators**: Leaderboard shows whether to Follow (✓) or Bet Against (⚠️) each model
- **Centralized Constants**: Platform-wide constants (sports, models, bookmakers) managed as environment variables
- **Collapsible Filters**: All analysis pages now have collapsible filter/sort controls
- **Navigation Improvements**: Added breadcrumbs, reorganized sections, simplified footer

### Fixed - February 13, 2026
- **Unit Tests**: Fixed all remaining unit tests - 329 passing (100% pass rate)
  - Fixed backtest_engine tests to mock user_models_table
  - Fixed custom_data tests by removing non-existent allow_benny_access attribute
  - Fixed user_models_api test to return proper mock objects
  - Updated benny_trader test to match current AI-based implementation
- **CloudWatch Alarms**: Alarm periods now match Lambda schedules (24h for daily, 1h for hourly)
- **Benny Trader**: Fixed Float type errors by converting to Decimal for DynamoDB
- **Model Comparison**: Fixed accuracy difference calculation (was showing NaN%)
- **Leaderboard Performance**: Now uses cached data instead of computing on-demand

### Changed - February 13, 2026
- Model leaderboard increased from top 3 to top 5 models
- Sidebar collapse now uses width:0 transition for smoother content expansion
- Main element padding standardized across all pages
- Benny button raised to 60px from bottom for better visibility

## [0.1.0] - 2026-01-15
- Initial beta release
- Core prediction models (consensus, value, momentum, contrarian, etc.)
- User model builder
- Benny AI assistant
- Historical backtesting
- Custom data import
