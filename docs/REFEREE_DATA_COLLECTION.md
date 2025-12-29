# Referee Data Collection System

## Overview

The referee data collection system gathers officiating statistics and bias metrics from real sources across 5 major sports. This data is crucial for ML prediction models that account for referee bias - a factor most betting systems ignore.

## Data Sources & Coverage

### ✅ Real Data Sources (135 officials - 99.3%)

#### NBA Basketball (78 referees)
- **Source**: Basketball-Reference.com
- **URL**: `https://www.basketball-reference.com/referees/2025_register.html`
- **Data Quality**: ✅ Real, comprehensive
- **Update Frequency**: Seasonal
- **Metrics**: Games officiated, foul patterns, experience

#### NFL Football (18 referees) 
- **Source**: NFLPenalties.com
- **URL**: `https://www.nflpenalties.com/all-referees.php`
- **Data Quality**: ✅ Real, detailed penalty statistics
- **Update Frequency**: Weekly during season
- **Metrics**: Penalty calls per game, bias patterns

#### NHL Hockey (39 referees)
- **Source**: ScoutingTheRefs.com  
- **URL**: `https://scoutingtherefs.com/2018-19-nhl-referee-stats/`
- **Data Quality**: ✅ Real, historical statistics
- **Update Frequency**: Seasonal
- **Metrics**: Penalty calls, game management style

### ⚠️ Fallback Data (1 official - 0.7%)

#### MLB Baseball (1 umpire)
- **Source**: UmpScores.com (attempted), fallback to sample
- **Status**: Site structure needs debugging
- **Alternative Sources**: UmpScorecards.us, Statcast data

#### Soccer (0 referees)
- **Source**: FootyStats.org (attempted), fallback disabled
- **Status**: Site structure needs debugging  
- **Alternative Sources**: FBRef.com, MyFootballFacts.com

## Data Schema

### RefereeStats Structure
```python
@dataclass
class RefereeStats:
    referee_id: str              # Unique identifier
    name: str                    # Official's name
    sport: str                   # basketball, football, baseball, soccer, hockey
    games_officiated: int        # Total games worked
    home_team_win_rate: float    # Home team win percentage with this official
    total_fouls_per_game: float  # Average fouls/penalties called per game
    technical_fouls_per_game: float  # Technical fouls/cards per game
    ejections_per_game: float    # Ejections/red cards per game
    overtime_games_rate: float   # Percentage of games going to OT
    close_game_call_tendency: str # "home_favoring", "away_favoring", "neutral"
    experience_years: int        # Years of experience
    season: str                  # Current season
    last_updated: datetime       # Data collection timestamp
    source_url: str             # Original data source
```

### DynamoDB Storage
- **Table**: `sports-betting-referees-{stage}`
- **Partition Key**: `referee_id`
- **Sort Key**: `game_date`
- **TTL**: 365 days
- **Data Types**: All floats converted to Decimal for DynamoDB compatibility

## Usage

### Manual Collection
```python
from backend.crawler.referee_crawler import RefereeCrawler

async with RefereeCrawler() as crawler:
    all_referees = await crawler.collect_all_referees()
    print(f"Collected {len(all_referees)} officials")
```

### Lambda Trigger
```python
# Via API Gateway
POST /collect/referees

# Via CloudWatch Event
{
    "collection_type": "referees",
    "source": "cloudwatch-event"
}
```

### Scheduler Integration
```python
from backend.crawler.scheduler import DataCollectionExecutor

executor = DataCollectionExecutor()
result = await executor.collect_referee_data()
```

## Bias Metrics Explained

### Home Team Win Rate
- **Purpose**: Detect home field advantage bias
- **Calculation**: (Home team wins) / (Total games officiated)
- **Typical Range**: 0.45-0.60
- **ML Usage**: Adjust home team probability

### Foul/Penalty Patterns
- **Purpose**: Identify calling tendencies
- **Metrics**: Fouls per game, technical fouls, ejections
- **ML Usage**: Predict game flow and total points

### Close Game Tendency
- **Purpose**: Detect bias in crucial moments
- **Categories**: home_favoring, away_favoring, neutral
- **ML Usage**: Adjust predictions for close games

### Experience Impact
- **Purpose**: Correlate experience with consistency
- **Metrics**: Years of experience, games officiated
- **ML Usage**: Weight referee impact by experience level

## Integration with ML Models

### Referee Bias Model Input Features
```python
referee_features = {
    'home_win_rate_deviation': referee.home_team_win_rate - league_average,
    'foul_rate_tendency': referee.total_fouls_per_game - sport_average,
    'ejection_tendency': referee.ejections_per_game,
    'experience_weight': min(referee.experience_years / 10, 1.0),
    'close_game_bias': bias_encoding[referee.close_game_call_tendency]
}
```

### Model Output
- **Bias-adjusted win probability**
- **Expected total points adjustment**
- **Game flow predictions** (fast/slow pace)
- **Overtime probability adjustment**

## Testing

### Unit Tests (7 tests)
- Individual sport scrapers (NBA, NFL, NHL, MLB, Soccer)
- Data structure validation
- Collection aggregation
- Error handling

### Integration Tests
- End-to-end collection workflow
- DynamoDB storage validation
- Lambda handler routing

### Test Coverage
```bash
# Run referee-specific tests
pytest tests/test_crawler.py::TestRefereeCrawler -v

# Run all tests including referee integration
pytest tests/ -v
```

## Monitoring & Maintenance

### Success Metrics
- **Data Freshness**: Updated within 24 hours of source updates
- **Coverage**: 95%+ of active officials per sport
- **Accuracy**: Real data sources preferred over samples
- **Reliability**: 99%+ successful collection rate

### Error Handling
- **Graceful Degradation**: Continue with available data if some sources fail
- **Retry Logic**: Automatic retries with exponential backoff
- **Logging**: Comprehensive error tracking and source attribution
- **Fallback Strategy**: Sample data only when real sources unavailable

### Maintenance Tasks
- **Quarterly**: Review and update data source URLs
- **Seasonally**: Add new officials and update rosters
- **Annually**: Validate bias metrics against actual outcomes

## Future Enhancements

### Short Term
1. **Debug MLB scraper** - Fix UmpScores.com parsing
2. **Debug soccer scraper** - Fix FootyStats.org parsing
3. **Add more NHL sources** - Expand beyond ScoutingTheRefs

### Long Term
1. **Historical bias tracking** - Multi-season referee performance
2. **Game-specific adjustments** - Playoff vs regular season behavior
3. **Cross-sport analysis** - Officials who work multiple sports
4. **Predictive bias modeling** - Forecast referee impact on specific matchups

## API Endpoints

### Trigger Collection
```
POST /api/v1/collect/referees
Response: {
    "success": true,
    "referees_collected": 135,
    "referees_stored": 135,
    "execution_time_seconds": 12.5
}
```

### Query Referee Data
```
GET /api/v1/referees?sport=basketball&limit=10
Response: [
    {
        "referee_id": "nba_scott_foster_2025",
        "name": "Scott Foster",
        "sport": "basketball",
        "home_team_win_rate": 0.52,
        "bias_metrics": {...}
    }
]
```

This referee data collection system provides a significant competitive advantage by incorporating officiating bias into betting predictions - a factor that traditional models overlook.
