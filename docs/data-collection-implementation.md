# Data Collection Pipeline Implementation

## Overview
Implementation of data collectors for all 12 ML models in the sports betting analysis system. Each collector is designed to gather specific data types while maintaining data quality, consistency, and real-time updates.

## Core Collection Framework

### 1. Base Data Collector
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import asyncio
import aiohttp
from datetime import datetime, timedelta
import boto3
from dataclasses import dataclass

@dataclass
class CollectionResult:
    success: bool
    data: Optional[Dict]
    error: Optional[str]
    timestamp: datetime
    source: str
    data_quality_score: float

class BaseDataCollector(ABC):
    def __init__(self, name: str, update_frequency_minutes: int):
        self.name = name
        self.update_frequency = update_frequency_minutes
        self.last_update = None
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('sports-analytics-data')
        
    @abstractmethod
    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect data for specified games"""
        pass
    
    @abstractmethod
    def validate_data(self, data: Dict) -> float:
        """Validate data quality (0-1 score)"""
        pass
    
    def should_update(self) -> bool:
        """Check if data should be updated based on frequency"""
        if not self.last_update:
            return True
        
        time_since_update = datetime.utcnow() - self.last_update
        return time_since_update.total_seconds() >= (self.update_frequency * 60)
    
    async def store_data(self, data: Dict, game_id: str, sport: str):
        """Store collected data in DynamoDB"""
        item = {
            'PK': f'DATA#{game_id}',
            'SK': f'{self.name.upper()}#{datetime.utcnow().isoformat()}',
            'GSI1PK': f'COLLECTOR#{self.name}',
            'GSI1SK': f'SPORT#{sport}#{datetime.utcnow().isoformat()}',
            'collector_name': self.name,
            'sport': sport,
            'game_id': game_id,
            'data': data,
            'collected_at': datetime.utcnow().isoformat(),
            'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
        }
        
        self.table.put_item(Item=item)
```

### 2. Management Data Collector
```python
class ManagementDataCollector(BaseDataCollector):
    def __init__(self):
        super().__init__('management', update_frequency_minutes=360)  # 6 hours
        self.espn_api = ESPNCoachingAPI()
        self.sports_reference = SportsReferenceAPI()
        
    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect coaching and management data"""
        try:
            management_data = {}
            
            for game in games:
                home_team = game['home_team']
                away_team = game['away_team']
                
                # Collect coaching data
                home_coach_data = await self.collect_coach_data(home_team, sport)
                away_coach_data = await self.collect_coach_data(away_team, sport)
                
                # Collect situational management data
                situational_data = await self.collect_situational_data(game, sport)
                
                management_data[game['id']] = {
                    'home_coach': home_coach_data,
                    'away_coach': away_coach_data,
                    'situational': situational_data,
                    'game_context': self.analyze_game_context(game)
                }
            
            quality_score = self.validate_data(management_data)
            
            return CollectionResult(
                success=True,
                data=management_data,
                error=None,
                timestamp=datetime.utcnow(),
                source='management_collector',
                data_quality_score=quality_score
            )
            
        except Exception as e:
            return CollectionResult(
                success=False,
                data=None,
                error=str(e),
                timestamp=datetime.utcnow(),
                source='management_collector',
                data_quality_score=0.0
            )
    
    async def collect_coach_data(self, team: str, sport: str) -> Dict:
        """Collect coaching statistics and tendencies"""
        coach_data = {
            'name': await self.get_head_coach(team, sport),
            'experience_years': await self.get_coach_experience(team, sport),
            'win_percentage': await self.get_coach_win_rate(team, sport),
            'playoff_record': await self.get_playoff_record(team, sport),
            'timeout_usage': await self.get_timeout_patterns(team, sport),
            'fourth_down_aggression': await self.get_fourth_down_stats(team, sport) if sport == 'nfl' else None,
            'rotation_patterns': await self.get_rotation_data(team, sport) if sport == 'nba' else None,
            'late_game_management': await self.get_late_game_stats(team, sport)
        }
        
        return coach_data
    
    def validate_data(self, data: Dict) -> float:
        """Validate management data quality"""
        total_fields = 0
        complete_fields = 0
        
        for game_data in data.values():
            for coach_type in ['home_coach', 'away_coach']:
                coach_data = game_data[coach_type]
                for field, value in coach_data.items():
                    total_fields += 1
                    if value is not None:
                        complete_fields += 1
        
        return complete_fields / total_fields if total_fields > 0 else 0.0
```

### 3. Team Momentum Collector
```python
class TeamMomentumCollector(BaseDataCollector):
    def __init__(self):
        super().__init__('team_momentum', update_frequency_minutes=60)  # 1 hour
        
    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect team momentum and recent performance data"""
        try:
            momentum_data = {}
            
            for game in games:
                home_team = game['home_team']
                away_team = game['away_team']
                
                # Get recent game results
                home_momentum = await self.calculate_team_momentum(home_team, sport)
                away_momentum = await self.calculate_team_momentum(away_team, sport)
                
                momentum_data[game['id']] = {
                    'home_team_momentum': home_momentum,
                    'away_team_momentum': away_momentum,
                    'momentum_differential': home_momentum['composite_score'] - away_momentum['composite_score']
                }
            
            quality_score = self.validate_data(momentum_data)
            
            return CollectionResult(
                success=True,
                data=momentum_data,
                error=None,
                timestamp=datetime.utcnow(),
                source='momentum_collector',
                data_quality_score=quality_score
            )
            
        except Exception as e:
            return CollectionResult(
                success=False,
                data=None,
                error=str(e),
                timestamp=datetime.utcnow(),
                source='momentum_collector',
                data_quality_score=0.0
            )
    
    async def calculate_team_momentum(self, team: str, sport: str) -> Dict:
        """Calculate comprehensive team momentum metrics"""
        
        # Get recent games (last 10 for NBA, last 4 for NFL)
        lookback_games = 10 if sport == 'nba' else 4
        recent_games = await self.get_recent_games(team, sport, lookback_games)
        
        momentum_metrics = {
            'win_streak': self.calculate_win_streak(recent_games),
            'recent_record': self.calculate_recent_record(recent_games),
            'point_differential_trend': self.calculate_point_diff_trend(recent_games),
            'ats_record': self.calculate_ats_record(recent_games),
            'home_away_splits': await self.get_home_away_performance(team, sport),
            'rest_advantage': await self.calculate_rest_advantage(team, sport),
            'travel_factor': await self.calculate_travel_impact(team, sport),
            'composite_score': 0.0  # Will be calculated
        }
        
        # Calculate composite momentum score
        momentum_metrics['composite_score'] = self.calculate_composite_momentum(momentum_metrics)
        
        return momentum_metrics
    
    def validate_data(self, data: Dict) -> float:
        """Validate momentum data completeness"""
        required_fields = ['win_streak', 'recent_record', 'point_differential_trend', 'composite_score']
        
        total_checks = 0
        passed_checks = 0
        
        for game_data in data.values():
            for team_type in ['home_team_momentum', 'away_team_momentum']:
                team_data = game_data[team_type]
                for field in required_fields:
                    total_checks += 1
                    if field in team_data and team_data[field] is not None:
                        passed_checks += 1
        
        return passed_checks / total_checks if total_checks > 0 else 0.0
```

### 4. Weather Data Collector
```python
class WeatherDataCollector(BaseDataCollector):
    def __init__(self):
        super().__init__('weather', update_frequency_minutes=30)  # 30 minutes
        self.weather_api_key = self.get_weather_api_key()
        
    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect weather data for outdoor games"""
        try:
            weather_data = {}
            
            for game in games:
                # Only collect weather for outdoor venues
                venue_info = await self.get_venue_info(game['venue'])
                
                if venue_info['type'] == 'outdoor' and sport == 'nfl':
                    weather_info = await self.get_weather_forecast(
                        venue_info['latitude'],
                        venue_info['longitude'],
                        game['commence_time']
                    )
                    
                    weather_data[game['id']] = {
                        'venue_type': 'outdoor',
                        'temperature': weather_info['temperature'],
                        'wind_speed': weather_info['wind_speed'],
                        'wind_direction': weather_info['wind_direction'],
                        'precipitation_chance': weather_info['precipitation_chance'],
                        'humidity': weather_info['humidity'],
                        'weather_impact_score': self.calculate_weather_impact(weather_info)
                    }
                else:
                    # Indoor venue or NBA game
                    weather_data[game['id']] = {
                        'venue_type': 'indoor',
                        'weather_impact_score': 0.0  # No weather impact
                    }
            
            quality_score = self.validate_data(weather_data)
            
            return CollectionResult(
                success=True,
                data=weather_data,
                error=None,
                timestamp=datetime.utcnow(),
                source='weather_collector',
                data_quality_score=quality_score
            )
            
        except Exception as e:
            return CollectionResult(
                success=False,
                data=None,
                error=str(e),
                timestamp=datetime.utcnow(),
                source='weather_collector',
                data_quality_score=0.0
            )
    
    async def get_weather_forecast(self, lat: float, lon: float, game_time: str) -> Dict:
        """Get weather forecast for game location and time"""
        async with aiohttp.ClientSession() as session:
            url = f"https://api.openweathermap.org/data/2.5/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.weather_api_key,
                'units': 'imperial'
            }
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                # Find forecast closest to game time
                game_datetime = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                closest_forecast = self.find_closest_forecast(data['list'], game_datetime)
                
                return {
                    'temperature': closest_forecast['main']['temp'],
                    'wind_speed': closest_forecast['wind']['speed'],
                    'wind_direction': closest_forecast['wind']['deg'],
                    'precipitation_chance': closest_forecast.get('pop', 0) * 100,
                    'humidity': closest_forecast['main']['humidity'],
                    'conditions': closest_forecast['weather'][0]['description']
                }
    
    def validate_data(self, data: Dict) -> float:
        """Validate weather data quality"""
        total_games = len(data)
        valid_games = 0
        
        for game_data in data.values():
            if game_data['venue_type'] == 'indoor':
                valid_games += 1  # Indoor venues are always valid
            elif all(key in game_data for key in ['temperature', 'wind_speed', 'precipitation_chance']):
                valid_games += 1
        
        return valid_games / total_games if total_games > 0 else 0.0
```

### 5. Public Opinion Collector (Multi-Platform)
```python
class PublicOpinionCollector(BaseDataCollector):
    def __init__(self):
        super().__init__('public_opinion', update_frequency_minutes=15)  # 15 minutes
        self.reddit_client = RedditAPI()
        self.twitter_client = TwitterAPI()
        self.discord_client = DiscordAPI()
        
    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect multi-platform public sentiment data"""
        try:
            opinion_data = {}
            
            for game in games:
                # Collect from multiple platforms
                reddit_sentiment = await self.collect_reddit_sentiment(game, sport)
                twitter_sentiment = await self.collect_twitter_sentiment(game, sport)
                discord_sentiment = await self.collect_discord_sentiment(game, sport)
                betting_public = await self.collect_betting_percentages(game)
                
                # Aggregate sentiment
                aggregated_sentiment = self.aggregate_sentiment({
                    'reddit': reddit_sentiment,
                    'twitter': twitter_sentiment,
                    'discord': discord_sentiment,
                    'betting_public': betting_public
                })
                
                opinion_data[game['id']] = aggregated_sentiment
            
            quality_score = self.validate_data(opinion_data)
            
            return CollectionResult(
                success=True,
                data=opinion_data,
                error=None,
                timestamp=datetime.utcnow(),
                source='public_opinion_collector',
                data_quality_score=quality_score
            )
            
        except Exception as e:
            return CollectionResult(
                success=False,
                data=None,
                error=str(e),
                timestamp=datetime.utcnow(),
                source='public_opinion_collector',
                data_quality_score=0.0
            )
    
    async def collect_reddit_sentiment(self, game: Dict, sport: str) -> Dict:
        """Collect sentiment from Reddit"""
        subreddits = ['sportsbook', f'{sport}', game['home_team'].lower(), game['away_team'].lower()]
        
        sentiment_data = {
            'posts_analyzed': 0,
            'home_team_sentiment': 0.0,
            'away_team_sentiment': 0.0,
            'betting_sentiment': 0.0,
            'volume_score': 0.0
        }
        
        for subreddit in subreddits:
            try:
                posts = await self.reddit_client.search_posts(
                    subreddit=subreddit,
                    query=f"{game['home_team']} {game['away_team']}",
                    time_filter='day',
                    limit=50
                )
                
                for post in posts:
                    sentiment = self.analyze_text_sentiment(post['title'] + ' ' + post['selftext'])
                    sentiment_data['posts_analyzed'] += 1
                    
                    # Classify sentiment by team
                    if game['home_team'].lower() in post['title'].lower():
                        sentiment_data['home_team_sentiment'] += sentiment
                    if game['away_team'].lower() in post['title'].lower():
                        sentiment_data['away_team_sentiment'] += sentiment
                        
            except Exception as e:
                continue  # Skip failed subreddits
        
        # Normalize sentiment scores
        if sentiment_data['posts_analyzed'] > 0:
            sentiment_data['home_team_sentiment'] /= sentiment_data['posts_analyzed']
            sentiment_data['away_team_sentiment'] /= sentiment_data['posts_analyzed']
            sentiment_data['volume_score'] = min(1.0, sentiment_data['posts_analyzed'] / 100)
        
        return sentiment_data
    
    def validate_data(self, data: Dict) -> float:
        """Validate public opinion data quality"""
        total_platforms = 4  # Reddit, Twitter, Discord, Betting Public
        
        quality_scores = []
        for game_data in data.values():
            platform_scores = []
            
            for platform in ['reddit', 'twitter', 'discord', 'betting_public']:
                if platform in game_data and game_data[platform]['posts_analyzed'] > 0:
                    platform_scores.append(1.0)
                else:
                    platform_scores.append(0.0)
            
            quality_scores.append(sum(platform_scores) / total_platforms)
        
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
```

### 6. Data Collection Orchestrator
```python
class DataCollectionOrchestrator:
    def __init__(self):
        self.collectors = {
            'management': ManagementDataCollector(),
            'team_momentum': TeamMomentumCollector(),
            'team_stats': TeamStatsCollector(),
            'player_stats': PlayerStatsCollector(),
            'weather': WeatherDataCollector(),
            'player_life_events': PlayerLifeEventsCollector(),
            'public_opinion': PublicOpinionCollector(),
            'market_inefficiency': MarketInefficiencyCollector(),
            'referee_bias': RefereeBiasCollector(),
            'referee_decision': RefereeDecisionCollector(),
            'referee_life_events': RefereeLifeEventsCollector(),
            'historical_performance': HistoricalPerformanceCollector()
        }
        
    async def collect_all_data(self, sport: str, games: List[Dict]) -> Dict[str, CollectionResult]:
        """Orchestrate data collection from all collectors"""
        
        # Determine which collectors need updates
        active_collectors = {
            name: collector for name, collector in self.collectors.items()
            if collector.should_update()
        }
        
        if not active_collectors:
            return {}
        
        # Run collectors in parallel
        tasks = []
        for name, collector in active_collectors.items():
            task = asyncio.create_task(
                collector.collect_data(sport, games),
                name=f"collect_{name}"
            )
            tasks.append((name, task))
        
        # Wait for all collections to complete
        results = {}
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
                
                # Store successful collections
                if result.success:
                    for game in games:
                        await self.collectors[name].store_data(
                            result.data.get(game['id'], {}),
                            game['id'],
                            sport
                        )
                        
            except Exception as e:
                results[name] = CollectionResult(
                    success=False,
                    data=None,
                    error=str(e),
                    timestamp=datetime.utcnow(),
                    source=name,
                    data_quality_score=0.0
                )
        
        # Log collection summary
        await self.log_collection_summary(sport, results)
        
        return results
    
    async def log_collection_summary(self, sport: str, results: Dict[str, CollectionResult]):
        """Log summary of data collection run"""
        summary = {
            'sport': sport,
            'collection_timestamp': datetime.utcnow().isoformat(),
            'collectors_run': len(results),
            'successful_collections': sum(1 for r in results.values() if r.success),
            'failed_collections': sum(1 for r in results.values() if not r.success),
            'avg_data_quality': sum(r.data_quality_score for r in results.values()) / len(results) if results else 0,
            'individual_results': {
                name: {
                    'success': result.success,
                    'data_quality_score': result.data_quality_score,
                    'error': result.error
                }
                for name, result in results.items()
            }
        }
        
        # Store in DynamoDB for monitoring
        table = boto3.resource('dynamodb').Table('collection-logs')
        table.put_item(Item=summary)
```

### 7. Lambda Handler for Scheduled Collection
```python
import json
import asyncio
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler for scheduled data collection"""
    
    try:
        # Parse event
        sport = event.get('sport', 'nfl')
        collection_type = event.get('collection_type', 'all')
        
        # Get upcoming games
        games = get_upcoming_games(sport)
        
        if not games:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'No upcoming {sport} games found',
                    'collections_run': 0
                })
            }
        
        # Run data collection
        orchestrator = DataCollectionOrchestrator()
        
        # Use asyncio.run for Lambda
        results = asyncio.run(orchestrator.collect_all_data(sport, games))
        
        # Prepare response
        successful_collections = sum(1 for r in results.values() if r.success)
        total_collections = len(results)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data collection completed',
                'sport': sport,
                'games_processed': len(games),
                'collections_run': total_collections,
                'successful_collections': successful_collections,
                'avg_data_quality': sum(r.data_quality_score for r in results.values()) / total_collections if total_collections > 0 else 0
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Data collection failed'
            })
        }

def get_upcoming_games(sport: str) -> List[Dict]:
    """Get upcoming games from existing odds data"""
    # Implementation to fetch games from DynamoDB
    # This would integrate with existing odds collection system
    pass
```

## Implementation Schedule

### Week 1: Core Framework
- [ ] Implement base data collector class
- [ ] Create data storage schema
- [ ] Build collection orchestrator
- [ ] Set up Lambda infrastructure

### Week 2: Primary Collectors
- [ ] Management data collector
- [ ] Team momentum collector  
- [ ] Weather data collector
- [ ] Team/player stats collectors

### Week 3: Advanced Collectors
- [ ] Public opinion collector (multi-platform)
- [ ] Market inefficiency collector
- [ ] Referee data collectors
- [ ] Historical performance collector

### Week 4: Integration & Testing
- [ ] Integration with existing system
- [ ] Data quality monitoring
- [ ] Performance optimization
- [ ] Error handling and alerts

## Success Metrics

### Data Quality
- **Completeness**: >90% data availability for active games
- **Freshness**: Data updated within specified frequencies
- **Accuracy**: >95% data validation success rate
- **Coverage**: All 12 model types collecting data

### System Performance
- **Collection Speed**: <5 minutes for full data collection cycle
- **Error Rate**: <5% collection failures
- **Storage Efficiency**: Optimized DynamoDB usage
- **Cost Management**: Stay within AWS budget limits

This comprehensive data collection system provides the foundation for feeding our 12-model ML analysis system with high-quality, real-time data from diverse sources.
