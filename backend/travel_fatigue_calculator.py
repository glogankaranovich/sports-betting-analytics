"""
Travel distance and fatigue calculator for teams
"""
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from decimal import Decimal
from math import radians, cos, sin, asin, sqrt

class TravelFatigueCalculator:
    def __init__(self):
        self.table = boto3.resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
        
        # Team home city coordinates (lat, lon)
        self.team_locations = {
            # NFL
            'Arizona Cardinals': (33.5276, -112.2626),
            'Atlanta Falcons': (33.7490, -84.3880),
            'Baltimore Ravens': (39.2904, -76.6122),
            'Buffalo Bills': (42.8864, -78.8784),
            'Carolina Panthers': (35.2271, -80.8431),
            'Chicago Bears': (41.8781, -87.6298),
            'Cincinnati Bengals': (39.1031, -84.5120),
            'Cleveland Browns': (41.4993, -81.6944),
            'Dallas Cowboys': (32.7767, -96.7970),
            'Denver Broncos': (39.7392, -104.9903),
            'Detroit Lions': (42.3314, -83.0458),
            'Green Bay Packers': (44.5133, -88.0133),
            'Houston Texans': (29.7604, -95.3698),
            'Indianapolis Colts': (39.7684, -86.1581),
            'Jacksonville Jaguars': (30.3322, -81.6557),
            'Kansas City Chiefs': (39.0997, -94.5786),
            'Las Vegas Raiders': (36.1699, -115.1398),
            'Los Angeles Chargers': (34.0522, -118.2437),
            'Los Angeles Rams': (34.0522, -118.2437),
            'Miami Dolphins': (25.7617, -80.1918),
            'Minnesota Vikings': (44.9778, -93.2650),
            'New England Patriots': (42.3601, -71.0589),
            'New Orleans Saints': (29.9511, -90.0715),
            'New York Giants': (40.7128, -74.0060),
            'New York Jets': (40.7128, -74.0060),
            'Philadelphia Eagles': (39.9526, -75.1652),
            'Pittsburgh Steelers': (40.4406, -79.9959),
            'San Francisco 49ers': (37.7749, -122.4194),
            'Seattle Seahawks': (47.6062, -122.3321),
            'Tampa Bay Buccaneers': (27.9506, -82.4572),
            'Tennessee Titans': (36.1627, -86.7816),
            'Washington Commanders': (38.9072, -77.0369),
            
            # NBA
            'Atlanta Hawks': (33.7490, -84.3880),
            'Boston Celtics': (42.3601, -71.0589),
            'Brooklyn Nets': (40.7128, -74.0060),
            'Charlotte Hornets': (35.2271, -80.8431),
            'Chicago Bulls': (41.8781, -87.6298),
            'Cleveland Cavaliers': (41.4993, -81.6944),
            'Dallas Mavericks': (32.7767, -96.7970),
            'Denver Nuggets': (39.7392, -104.9903),
            'Detroit Pistons': (42.3314, -83.0458),
            'Golden State Warriors': (37.7749, -122.4194),
            'Houston Rockets': (29.7604, -95.3698),
            'Indiana Pacers': (39.7684, -86.1581),
            'Los Angeles Clippers': (34.0522, -118.2437),
            'Los Angeles Lakers': (34.0522, -118.2437),
            'Memphis Grizzlies': (35.1495, -90.0490),
            'Miami Heat': (25.7617, -80.1918),
            'Milwaukee Bucks': (43.0389, -87.9065),
            'Minnesota Timberwolves': (44.9778, -93.2650),
            'New Orleans Pelicans': (29.9511, -90.0715),
            'New York Knicks': (40.7128, -74.0060),
            'Oklahoma City Thunder': (35.4676, -97.5164),
            'Orlando Magic': (28.5383, -81.3792),
            'Philadelphia 76ers': (39.9526, -75.1652),
            'Phoenix Suns': (33.4484, -112.0740),
            'Portland Trail Blazers': (45.5152, -122.6784),
            'Sacramento Kings': (38.5816, -121.4944),
            'San Antonio Spurs': (29.4241, -98.4936),
            'Toronto Raptors': (43.6532, -79.3832),
            'Utah Jazz': (40.7608, -111.8910),
            'Washington Wizards': (38.9072, -77.0369),
            
            # MLB
            'Arizona Diamondbacks': (33.4484, -112.0740),
            'Atlanta Braves': (33.7490, -84.3880),
            'Baltimore Orioles': (39.2904, -76.6122),
            'Boston Red Sox': (42.3601, -71.0589),
            'Chicago Cubs': (41.8781, -87.6298),
            'Chicago White Sox': (41.8781, -87.6298),
            'Cincinnati Reds': (39.1031, -84.5120),
            'Cleveland Guardians': (41.4993, -81.6944),
            'Colorado Rockies': (39.7392, -104.9903),
            'Detroit Tigers': (42.3314, -83.0458),
            'Houston Astros': (29.7604, -95.3698),
            'Kansas City Royals': (39.0997, -94.5786),
            'Los Angeles Angels': (34.0522, -118.2437),
            'Los Angeles Dodgers': (34.0522, -118.2437),
            'Miami Marlins': (25.7617, -80.1918),
            'Milwaukee Brewers': (43.0389, -87.9065),
            'Minnesota Twins': (44.9778, -93.2650),
            'New York Mets': (40.7128, -74.0060),
            'New York Yankees': (40.7128, -74.0060),
            'Oakland Athletics': (37.7749, -122.4194),
            'Philadelphia Phillies': (39.9526, -75.1652),
            'Pittsburgh Pirates': (40.4406, -79.9959),
            'San Diego Padres': (32.7157, -117.1611),
            'San Francisco Giants': (37.7749, -122.4194),
            'Seattle Mariners': (47.6062, -122.3321),
            'St. Louis Cardinals': (38.6270, -90.1994),
            'Tampa Bay Rays': (27.9506, -82.4572),
            'Texas Rangers': (32.7767, -96.7970),
            'Toronto Blue Jays': (43.6532, -79.3832),
            'Washington Nationals': (38.9072, -77.0369),
            
            # NHL
            'Anaheim Ducks': (33.8075, -117.8765),
            'Boston Bruins': (42.3601, -71.0589),
            'Buffalo Sabres': (42.8864, -78.8784),
            'Calgary Flames': (51.0447, -114.0719),
            'Carolina Hurricanes': (35.8032, -78.7219),
            'Chicago Blackhawks': (41.8781, -87.6298),
            'Colorado Avalanche': (39.7392, -104.9903),
            'Columbus Blue Jackets': (39.9612, -82.9988),
            'Dallas Stars': (32.7767, -96.7970),
            'Detroit Red Wings': (42.3314, -83.0458),
            'Edmonton Oilers': (53.5461, -113.4938),
            'Florida Panthers': (26.1224, -80.1373),
            'Los Angeles Kings': (34.0522, -118.2437),
            'Minnesota Wild': (44.9778, -93.2650),
            'Montreal Canadiens': (45.5017, -73.5673),
            'Nashville Predators': (36.1627, -86.7816),
            'New Jersey Devils': (40.7128, -74.0060),
            'New York Islanders': (40.7128, -74.0060),
            'New York Rangers': (40.7128, -74.0060),
            'Ottawa Senators': (45.4215, -75.6972),
            'Philadelphia Flyers': (39.9526, -75.1652),
            'Pittsburgh Penguins': (40.4406, -79.9959),
            'San Jose Sharks': (37.3382, -121.8863),
            'Seattle Kraken': (47.6062, -122.3321),
            'St. Louis Blues': (38.6270, -90.1994),
            'Tampa Bay Lightning': (27.9506, -82.4572),
            'Toronto Maple Leafs': (43.6532, -79.3832),
            'Vancouver Canucks': (49.2827, -123.1207),
            'Vegas Golden Knights': (36.1699, -115.1398),
            'Washington Capitals': (38.9072, -77.0369),
            'Winnipeg Jets': (49.8951, -97.1384),
            
            # EPL (Soccer)
            'Arsenal': (51.5549, -0.1084),
            'Aston Villa': (52.5097, -1.8848),
            'Bournemouth': (50.7192, -1.8808),
            'Brentford': (51.4907, -0.2889),
            'Brighton': (50.8225, -0.1372),
            'Chelsea': (51.4817, -0.1910),
            'Crystal Palace': (51.3983, -0.0854),
            'Everton': (53.4084, -2.9916),
            'Fulham': (51.4749, -0.2217),
            'Ipswich Town': (52.0595, 1.1557),
            'Leicester City': (52.6369, -1.1398),
            'Liverpool': (53.4084, -2.9916),
            'Manchester City': (53.4808, -2.2426),
            'Manchester United': (53.4808, -2.2426),
            'Newcastle United': (54.9783, -1.6178),
            'Nottingham Forest': (52.9548, -1.1581),
            'Southampton': (50.9097, -1.4044),
            'Tottenham Hotspur': (51.6033, -0.0664),
            'West Ham United': (51.5074, 0.0526),
            'Wolverhampton Wanderers': (52.5897, -2.1301),
        }
    
    def calculate_distance(self, team1: str, team2: str) -> float:
        """Calculate distance between two teams in miles using Haversine formula"""
        loc1 = self.team_locations.get(team1)
        loc2 = self.team_locations.get(team2)
        
        if not loc1 or not loc2:
            return 0.0
        
        lat1, lon1 = loc1
        lat2, lon2 = loc2
        
        # Haversine formula
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        miles = 3956 * c  # Earth radius in miles
        
        return round(miles, 1)
    
    def calculate_fatigue_score(self, team: str, sport: str, game_date: str) -> Dict:
        """Calculate fatigue score based on recent travel and rest"""
        recent_games = self._get_recent_games(team, sport, game_date, lookback_days=14)
        
        if not recent_games:
            return {
                'fatigue_score': 0,
                'total_miles': 0,
                'days_rest': 7,
                'back_to_back': False,
                'impact': 'none'
            }
        
        total_miles = 0
        days_since_last = 7
        back_to_back = False
        road_games = 0
        
        game_dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
        
        for i, game in enumerate(recent_games):
            prev_date = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            
            if i == 0:
                days_since_last = (game_dt - prev_date).days
                if days_since_last <= 1:
                    back_to_back = True
            
            opponent = game.get('away_team') if game.get('home_team') == team else game.get('home_team')
            distance = self.calculate_distance(team, opponent)
            
            weight = 1.0 / (i + 1)
            total_miles += distance * weight
            
            if game.get('away_team') == team:
                road_games += 1
        
        fatigue_score = 0
        
        if total_miles > 5000:
            fatigue_score += 40
        elif total_miles > 3000:
            fatigue_score += 30
        elif total_miles > 1500:
            fatigue_score += 20
        elif total_miles > 500:
            fatigue_score += 10
        
        if days_since_last == 0:
            fatigue_score += 30
        elif days_since_last == 1:
            fatigue_score += 20
        elif days_since_last == 2:
            fatigue_score += 10
        
        if road_games >= 4:
            fatigue_score += 30
        elif road_games >= 3:
            fatigue_score += 20
        elif road_games >= 2:
            fatigue_score += 10
        
        if fatigue_score >= 60:
            impact = 'high'
        elif fatigue_score >= 40:
            impact = 'moderate'
        elif fatigue_score >= 20:
            impact = 'low'
        else:
            impact = 'minimal'
        
        return {
            'fatigue_score': fatigue_score,
            'total_miles': round(total_miles, 1),
            'days_rest': days_since_last,
            'back_to_back': back_to_back,
            'road_games': road_games,
            'impact': impact
        }
    
    def _get_recent_games(self, team: str, sport: str, before_date: str, lookback_days: int = 14) -> List[Dict]:
        """Get team's recent games from DynamoDB"""
        try:
            cutoff = (datetime.fromisoformat(before_date.replace('Z', '+00:00')) - timedelta(days=lookback_days)).isoformat()
            
            response = self.table.query(
                IndexName='ActiveBetsIndexV2',
                KeyConditionExpression='active_bet_pk = :pk AND commence_time BETWEEN :start AND :end',
                ExpressionAttributeValues={
                    ':pk': f'GAME#{sport}',
                    ':start': cutoff,
                    ':end': before_date
                },
                ScanIndexForward=False
            )
            
            team_games = []
            for item in response.get('Items', []):
                if item.get('home_team') == team or item.get('away_team') == team:
                    team_games.append(item)
            
            return team_games[:10]
            
        except Exception as e:
            print(f"Error getting recent games: {e}")
            return []
    
    def store_fatigue_data(self, game_id: str, home_team: str, away_team: str, 
                          sport: str, game_date: str):
        """Calculate and store fatigue data for both teams"""
        home_fatigue = self.calculate_fatigue_score(home_team, sport, game_date)
        away_fatigue = self.calculate_fatigue_score(away_team, sport, game_date)
        
        timestamp = datetime.utcnow().isoformat()
        
        self.table.put_item(Item={
            'pk': f'FATIGUE#{game_id}',
            'sk': timestamp,
            'game_id': game_id,
            'sport': sport,
            'home_team': home_team,
            'away_team': away_team,
            'home_fatigue_score': Decimal(str(home_fatigue['fatigue_score'])),
            'home_total_miles': Decimal(str(home_fatigue['total_miles'])),
            'home_days_rest': home_fatigue['days_rest'],
            'home_back_to_back': home_fatigue['back_to_back'],
            'home_impact': home_fatigue['impact'],
            'away_fatigue_score': Decimal(str(away_fatigue['fatigue_score'])),
            'away_total_miles': Decimal(str(away_fatigue['total_miles'])),
            'away_days_rest': away_fatigue['days_rest'],
            'away_back_to_back': away_fatigue['back_to_back'],
            'away_impact': away_fatigue['impact'],
            'collected_at': timestamp
        })
        
        return {'home': home_fatigue, 'away': away_fatigue}
