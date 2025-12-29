# Sports Data APIs Research

## Comprehensive Team/Player Data Sources

### 1. **SportsData.io** ⭐ RECOMMENDED
**Coverage:** NFL, NBA, MLB, NHL, Soccer, College Sports
**Free Tier:** Unlimited API calls with scrambled data for testing
**Real Data:** Paid tiers starting ~$50/month
**Features:**
- Complete player rosters and statistics
- Injury reports and player status
- Team performance metrics
- Historical data and trends
- Real-time game data
- Weather conditions (outdoor sports)
- Coaching staff information

**Endpoints we need:**
- `/teams` - Team information and rosters
- `/players` - Player statistics and profiles  
- `/injuries` - Current injury reports
- `/games` - Game details with weather
- `/standings` - Team performance metrics

### 2. **API-Sports.io** 
**Coverage:** Basketball, Football (Soccer), American Football, Baseball, Hockey
**Free Tier:** 100 requests/day per sport
**Features:**
- Team statistics and standings
- Player profiles and stats
- Live scores and fixtures
- Historical data
- Odds integration

### 3. **TheSportsDB.com**
**Coverage:** All major sports
**Free Tier:** Basic data access
**Features:**
- Team information and logos
- Player profiles
- League standings
- Historical results
- Equipment and venue data

### 4. **Sports Reference (Unofficial)**
**Coverage:** NBA, NFL, MLB, NHL, College
**Free Tier:** Web scraping (rate limited)
**Features:**
- Comprehensive historical statistics
- Advanced metrics
- Player and team profiles
- Game logs and splits

### 5. **ESPN Hidden API**
**Coverage:** All ESPN covered sports
**Free Tier:** Unofficial/undocumented
**Features:**
- Real-time scores and stats
- Player information
- Team data
- News and updates

## Recommended Implementation Strategy

### Phase 1: Core Team Data
1. **SportsData.io Free Trial** - Test with scrambled data
2. **Sports Reference Scraping** - Historical team/player stats
3. **TheSportsDB** - Team metadata and basic info

### Phase 2: Enhanced Data (Paid)
1. **SportsData.io Production** - Real injury reports, weather
2. **API-Sports.io** - Cross-validation and additional metrics

## Data We Can Collect

### Team Performance Metrics
- Win/loss records and streaks
- Home/away performance splits
- Points scored/allowed averages
- Recent form (last 5-10 games)
- Head-to-head historical records
- Strength of schedule

### Player Data
- Active rosters and depth charts
- Key player statistics and trends
- Injury status and probable/questionable players
- Player matchup advantages
- Historical performance vs opponents

### Environmental Factors
- Weather conditions (temperature, wind, precipitation)
- Venue information (indoor/outdoor, altitude)
- Travel schedules and rest days
- Coaching changes and staff updates

### Advanced Metrics
- Offensive/defensive efficiency ratings
- Pace of play and style metrics
- Clutch performance indicators
- Momentum and psychological factors

## Integration Plan

### 1. Extend Current SportEvent Schema
```python
@dataclass
class EnhancedSportEvent:
    # Existing fields
    event_id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker_odds: List[Dict[str, Any]]
    
    # New team data
    home_team_stats: TeamStats
    away_team_stats: TeamStats
    
    # New player data
    home_roster: List[Player]
    away_roster: List[Player]
    injury_report: List[InjuryReport]
    
    # Environmental data
    weather: Optional[WeatherConditions]
    venue: VenueInfo
```

### 2. Create New Crawler Modules
- `team_stats_crawler.py` - Team performance data
- `player_data_crawler.py` - Roster and player stats
- `injury_crawler.py` - Injury reports and player status
- `weather_crawler.py` - Game conditions

### 3. Data Storage Enhancement
- New DynamoDB tables: `team-stats`, `player-data`, `injuries`
- Enhanced sports-data table with richer context
- S3 storage for historical team/player datasets

## Cost Estimation
- **Development Phase**: Free tiers and scraping
- **Production Phase**: ~$100-200/month for comprehensive data
- **ROI**: Enhanced prediction accuracy should offset costs

## Next Steps
1. Set up SportsData.io free trial account
2. Implement basic team stats crawler
3. Test data quality and coverage
4. Integrate with existing ML model architecture
