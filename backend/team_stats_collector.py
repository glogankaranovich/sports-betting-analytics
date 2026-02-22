"""
Team Stats Collector - Fetches actual team statistics from ESPN API
"""

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
import requests


class TeamStatsCollector:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))
        self.espn_base_url = "https://site.web.api.espn.com/apis/site/v2/sports"

    def collect_stats_for_sport(self, sport: str) -> int:
        """Collect team stats for completed games"""
        supported_sports = [
            "basketball_nba",
            "americanfootball_nfl",
            "baseball_mlb",
            "icehockey_nhl",
            "soccer_epl",
        ]

        if sport not in supported_sports:
            print(f"Team stats not supported for {sport}")
            return 0

        # Get completed games from DynamoDB
        completed_games = self._get_completed_games(sport)
        print(f"Found {len(completed_games)} completed games for {sport}")

        games_processed = 0
        for game in completed_games:
            try:
                # Get ESPN game ID by matching teams and date
                espn_game_id = self._find_espn_game_id(game, sport)

                if espn_game_id:
                    # Fetch team stats from ESPN
                    team_stats = self._fetch_espn_team_stats(espn_game_id, sport)

                    if team_stats:
                        # Store stats in DynamoDB
                        self._store_team_stats(game["id"], team_stats, sport)
                        games_processed += 1
                        print(f"Stored team stats for game {game['id']}")
                else:
                    print(f"Could not find ESPN game ID for {game['id']}")

            except Exception as e:
                print(f"Error collecting stats for game {game['id']}: {e}")
                continue

        return games_processed

    def _get_completed_games(self, sport: str) -> List[Dict[str, Any]]:
        """Get completed games that don't have team stats yet"""
        try:
            # Query using GSI to get games by commence_time
            now = datetime.now(timezone.utc)
            two_hours_ago = (now - timedelta(hours=2)).isoformat()

            response = self.table.query(
                IndexName="ActiveBetsIndexV2",
                KeyConditionExpression="active_bet_pk = :pk AND commence_time < :now",
                FilterExpression="contains(sk, :latest) AND attribute_not_exists(team_stats_collected)",
                ExpressionAttributeValues={
                    ":pk": f"GAME#{sport}",
                    ":now": two_hours_ago,
                    ":latest": "LATEST",
                },
                ProjectionExpression="pk, home_team, away_team, commence_time",
            )

            # Deduplicate by game_id (pk)
            seen_games = set()
            games = []
            for item in response.get("Items", []):
                game_id = item["pk"].split("#")[1]
                if game_id not in seen_games:
                    seen_games.add(game_id)
                    games.append(
                        {
                            "id": game_id,
                            "home_team": item.get("home_team"),
                            "away_team": item.get("away_team"),
                            "commence_time": item.get("commence_time"),
                        }
                    )

            return games

        except Exception as e:
            print(f"Error getting completed games: {e}")
            return []

    def _find_espn_game_id(self, game: Dict[str, Any], sport: str) -> Optional[str]:
        """Find ESPN game ID by matching teams and date"""
        try:
            # Convert sport key to ESPN format
            sport_map = {
                "basketball_nba": "basketball/nba",
                "americanfootball_nfl": "football/nfl",
                "baseball_mlb": "baseball/mlb",
                "icehockey_nhl": "hockey/nhl",
                "soccer_epl": "soccer/eng.1",
            }
            espn_sport = sport_map.get(sport, "basketball/nba")

            # Get game date (YYYYMMDD format)
            game_date = datetime.fromisoformat(
                game["commence_time"].replace("Z", "+00:00")
            )
            date_str = game_date.strftime("%Y%m%d")

            # Fetch scoreboard for that date
            url = f"{self.espn_base_url}/{espn_sport}/scoreboard?dates={date_str}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            events = data.get("events", [])

            # Match by team names
            our_teams = {game["home_team"], game["away_team"]}

            for event in events:
                competitions = event.get("competitions", [])
                if not competitions:
                    continue

                competition = competitions[0]
                competitors = competition.get("competitors", [])

                if len(competitors) >= 2:
                    team_names = {
                        c.get("team", {}).get("displayName", "") for c in competitors
                    }

                    # Check if both teams match
                    if team_names == our_teams:
                        return event.get("id")

            # If not found, try previous day (for late night games)
            prev_date = game_date - timedelta(days=1)
            prev_date_str = prev_date.strftime("%Y%m%d")

            url = f"{self.espn_base_url}/{espn_sport}/scoreboard?dates={prev_date_str}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            events = data.get("events", [])

            for event in events:
                competitions = event.get("competitions", [])
                if not competitions:
                    continue

                competition = competitions[0]
                competitors = competition.get("competitors", [])

                if len(competitors) >= 2:
                    team_names = {
                        c.get("team", {}).get("displayName", "") for c in competitors
                    }

                    # Check if both teams match
                    if team_names == our_teams:
                        return event.get("id")

            return None

        except Exception as e:
            print(f"Error finding ESPN game ID: {e}")
            return None

    def _fetch_espn_team_stats(
        self, espn_game_id: str, sport: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch team stats from ESPN API"""
        try:
            sport_map = {
                "basketball_nba": "basketball/nba",
                "americanfootball_nfl": "football/nfl",
                "baseball_mlb": "baseball/mlb",
                "icehockey_nhl": "hockey/nhl",
                "soccer_epl": "soccer/eng.1",
            }
            espn_sport = sport_map.get(sport, "basketball/nba")
            url = f"{self.espn_base_url}/{espn_sport}/summary?event={espn_game_id}"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            boxscore = data.get("boxscore", {})
            teams = boxscore.get("teams", [])

            if not teams:
                return None

            team_stats = {}
            for team in teams:
                team_name = team.get("team", {}).get("displayName", "")
                statistics = team.get("statistics", [])

                stats_dict = {}
                for stat in statistics:
                    label = stat.get("label", "")
                    value = stat.get("displayValue", "")
                    stats_dict[label] = value

                team_stats[team_name] = stats_dict

            return team_stats if team_stats else None

        except Exception as e:
            print(f"Error fetching ESPN team stats: {e}")
            return None

    def _store_team_stats(
        self, game_id: str, team_stats: Dict[str, Any], sport: str
    ) -> None:
        """Store team stats in DynamoDB"""
        try:
            # Convert to Decimal for DynamoDB
            team_stats_decimal = self._convert_to_decimal(team_stats)

            # Store team stats as separate records
            for team_name, stats in team_stats_decimal.items():
                # Normalize team name: lowercase with underscores
                normalized_name = team_name.lower().replace(" ", "_")

                pk = f"TEAM_STATS#{sport}#{normalized_name}"
                sk = datetime.utcnow().isoformat()

                self.table.put_item(
                    Item={
                        "pk": pk,
                        "sk": sk,
                        "game_id": game_id,
                        "game_index_pk": game_id,
                        "game_index_sk": pk,
                        "gsi_pk": f"TEAM_STATS#{sport}",  # For querying all teams by sport
                        "gsi_sk": sk,  # Timestamp for sorting by recency
                        "sport": sport,
                        "team_name": team_name,
                        "stats": stats,
                        "collected_at": sk,
                    }
                )

        except Exception as e:
            print(f"Error storing team stats: {e}")

    def _convert_to_decimal(self, obj):
        """Convert float values to Decimal for DynamoDB"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_decimal(v) for v in obj]
        return obj

    def calculate_opponent_adjusted_metrics(self, sport: str, days: int = 30) -> int:
        """Calculate opponent-adjusted efficiency metrics for all teams in a sport"""
        try:
            # Get recent team stats using ActiveBetsIndexV2 GSI
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            team_stats = []
            last_evaluated_key = None
            
            while True:
                query_kwargs = {
                    "IndexName": "GenericQueryIndex",
                    "KeyConditionExpression": "gsi_pk = :pk AND gsi_sk > :cutoff",
                    "ExpressionAttributeValues": {
                        ":pk": f"TEAM_STATS#{sport}",
                        ":cutoff": cutoff_date
                    }
                }
                
                if last_evaluated_key:
                    query_kwargs["ExclusiveStartKey"] = last_evaluated_key
                
                response = self.table.query(**query_kwargs)
                team_stats.extend(response.get("Items", []))
                
                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
            
            print(f"Found {len(team_stats)} team stat records for {sport}")
            
            if len(team_stats) < 10:
                print(f"Not enough data to calculate opponent-adjusted metrics for {sport}")
                return 0
            
            # Calculate metrics based on sport
            if sport == "basketball_nba":
                return self._calculate_nba_adjusted_metrics(team_stats)
            elif sport == "americanfootball_nfl":
                return self._calculate_nfl_adjusted_metrics(team_stats)
            elif sport == "soccer_epl":
                return self._calculate_soccer_adjusted_metrics(team_stats)
            elif sport == "icehockey_nhl":
                return self._calculate_nhl_adjusted_metrics(team_stats)
            elif sport == "baseball_mlb":
                # ESPN doesn't provide usable boxscore stats for MLB
                print(f"Opponent-adjusted metrics for {sport}: ESPN API doesn't provide boxscore stats")
                return 0
            else:
                print(f"Opponent-adjusted metrics not implemented for {sport}")
                return 0
            
        except Exception as e:
            print(f"Error calculating opponent-adjusted metrics: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _calculate_nba_adjusted_metrics(self, team_stats: List[Dict]) -> int:
        """Calculate NBA opponent-adjusted metrics"""
        # Group by team
        team_games = {}
        for stat in team_stats:
            team_name = stat.get("team_name")
            if team_name not in team_games:
                team_games[team_name] = []
            team_games[team_name].append(stat)
        
        # Calculate league averages
        total_points = sum(self._extract_numeric(s.get("stats", {}).get("Points", "0")) for s in team_stats)
        avg_points = total_points / len(team_stats) if team_stats else 110.0
        
        # Calculate adjusted metrics for each team
        adjusted_count = 0
        for team_name, games in team_games.items():
            metrics = self._calculate_team_metrics_nba(team_name, games, avg_points)
            if metrics:
                self._store_adjusted_metrics(team_name, metrics, "basketball_nba")
                adjusted_count += 1
        
        return adjusted_count
    
    def _calculate_team_metrics_nba(self, team_name: str, games: List[Dict], league_avg: float) -> Optional[Dict]:
        """Calculate metrics for an NBA team"""
        if not games:
            return None
        
        total_points = 0
        total_fg_pct = 0
        total_3pt_pct = 0
        
        for game in games:
            stats = game.get("stats", {})
            total_points += self._extract_numeric(stats.get("Points", "0"))
            total_fg_pct += self._extract_numeric(stats.get("Field Goal %", "0"))
            total_3pt_pct += self._extract_numeric(stats.get("3 Point %", "0"))
        
        count = len(games)
        return {
            "raw_ppg": round(total_points / count, 1),
            "adjusted_ppg": round(total_points / count, 1),  # Simplified - would need opponent data
            "fg_pct": round(total_fg_pct / count, 1),
            "three_pt_pct": round(total_3pt_pct / count, 1),
            "games_analyzed": count,
            "vs_league_avg": round((total_points / count) - league_avg, 1)
        }
    
    def _calculate_nfl_adjusted_metrics(self, team_stats: List[Dict]) -> int:
        """Calculate NFL opponent-adjusted metrics"""
        # Group by team
        team_games = {}
        for stat in team_stats:
            team_name = stat.get("team_name")
            if team_name not in team_games:
                team_games[team_name] = []
            team_games[team_name].append(stat)
        
        # Calculate league averages
        total_yards = sum(self._extract_numeric(s.get("stats", {}).get("Total Yards", "0")) for s in team_stats)
        total_points = sum(self._extract_numeric(s.get("stats", {}).get("Points", "0")) for s in team_stats)
        avg_yards = total_yards / len(team_stats) if team_stats else 350.0
        avg_points = total_points / len(team_stats) if team_stats else 22.0
        
        # Calculate adjusted metrics for each team
        adjusted_count = 0
        for team_name, games in team_games.items():
            metrics = self._calculate_team_metrics_nfl(team_name, games, avg_yards, avg_points)
            if metrics:
                self._store_adjusted_metrics(team_name, metrics, "americanfootball_nfl")
                adjusted_count += 1
        
        return adjusted_count
    
    def _calculate_team_metrics_nfl(self, team_name: str, games: List[Dict], league_avg_yards: float, league_avg_points: float) -> Optional[Dict]:
        """Calculate metrics for an NFL team"""
        if not games:
            return None
        
        total_yards = 0
        total_points = 0
        total_passing = 0
        total_rushing = 0
        
        for game in games:
            stats = game.get("stats", {})
            total_yards += self._extract_numeric(stats.get("Total Yards", "0"))
            total_points += self._extract_numeric(stats.get("Points", "0"))
            total_passing += self._extract_numeric(stats.get("Passing", "0"))
            total_rushing += self._extract_numeric(stats.get("Rushing", "0"))
        
        count = len(games)
        return {
            "raw_yards_per_game": round(total_yards / count, 1),
            "adjusted_yards_per_game": round(total_yards / count, 1),  # Simplified
            "raw_points_per_game": round(total_points / count, 1),
            "passing_yards_per_game": round(total_passing / count, 1),
            "rushing_yards_per_game": round(total_rushing / count, 1),
            "games_analyzed": count,
            "vs_league_avg_yards": round((total_yards / count) - league_avg_yards, 1),
            "vs_league_avg_points": round((total_points / count) - league_avg_points, 1)
        }
    
    def _calculate_nhl_adjusted_metrics(self, team_stats: List[Dict]) -> int:
        """Calculate NHL opponent-adjusted metrics"""
        # Group by team
        team_games = {}
        for stat in team_stats:
            team_name = stat.get("team_name")
            if team_name not in team_games:
                team_games[team_name] = []
            team_games[team_name].append(stat)
        
        # Calculate league averages
        total_shots = sum(self._extract_numeric(s.get("stats", {}).get("Shots", "0")) for s in team_stats)
        total_hits = sum(self._extract_numeric(s.get("stats", {}).get("Hits", "0")) for s in team_stats)
        avg_shots = total_shots / len(team_stats) if team_stats else 30.0
        avg_hits = total_hits / len(team_stats) if team_stats else 20.0
        
        # Calculate adjusted metrics for each team
        adjusted_count = 0
        for team_name, games in team_games.items():
            metrics = self._calculate_team_metrics_nhl(team_name, games, avg_shots, avg_hits)
            if metrics:
                self._store_adjusted_metrics(team_name, metrics, "icehockey_nhl")
                adjusted_count += 1
        
        return adjusted_count
    
    def _calculate_team_metrics_nhl(self, team_name: str, games: List[Dict], league_avg_shots: float, league_avg_hits: float) -> Optional[Dict]:
        """Calculate metrics for an NHL team"""
        if not games:
            return None
        
        total_shots = 0
        total_hits = 0
        total_blocked = 0
        total_takeaways = 0
        total_pp_goals = 0
        
        for game in games:
            stats = game.get("stats", {})
            total_shots += self._extract_numeric(stats.get("Shots", "0"))
            total_hits += self._extract_numeric(stats.get("Hits", "0"))
            total_blocked += self._extract_numeric(stats.get("Blocked Shots", "0"))
            total_takeaways += self._extract_numeric(stats.get("Takeaways", "0"))
            total_pp_goals += self._extract_numeric(stats.get("Power Play Goals", "0"))
        
        count = len(games)
        return {
            "shots_per_game": round(total_shots / count, 1),
            "adjusted_shots_per_game": round(total_shots / count, 1),  # Simplified
            "hits_per_game": round(total_hits / count, 1),
            "blocked_shots_per_game": round(total_blocked / count, 1),
            "takeaways_per_game": round(total_takeaways / count, 1),
            "pp_goals_per_game": round(total_pp_goals / count, 2),
            "games_analyzed": count,
            "vs_league_avg_shots": round((total_shots / count) - league_avg_shots, 1),
            "vs_league_avg_hits": round((total_hits / count) - league_avg_hits, 1)
        }
    
    def _calculate_mlb_adjusted_metrics(self, team_stats: List[Dict]) -> int:
        """Calculate MLB opponent-adjusted metrics"""
        # Group by team
        team_games = {}
        for stat in team_stats:
            team_name = stat.get("team_name")
            if team_name not in team_games:
                team_games[team_name] = []
            team_games[team_name].append(stat)
        
        # Calculate league averages (runs)
        total_runs = sum(self._extract_numeric(s.get("stats", {}).get("Runs", "0")) for s in team_stats)
        avg_runs = total_runs / len(team_stats) if team_stats else 4.5
        
        # Calculate adjusted metrics for each team
        adjusted_count = 0
        for team_name, games in team_games.items():
            metrics = self._calculate_team_metrics_mlb(team_name, games, avg_runs)
            if metrics:
                self._store_adjusted_metrics(team_name, metrics, "baseball_mlb")
                adjusted_count += 1
        
        return adjusted_count
    
    def _calculate_team_metrics_mlb(self, team_name: str, games: List[Dict], league_avg: float) -> Optional[Dict]:
        """Calculate metrics for an MLB team"""
        if not games:
            return None
        
        total_runs = 0
        total_hits = 0
        total_errors = 0
        
        for game in games:
            stats = game.get("stats", {})
            total_runs += self._extract_numeric(stats.get("Runs", "0"))
            total_hits += self._extract_numeric(stats.get("Hits", "0"))
            total_errors += self._extract_numeric(stats.get("Errors", "0"))
        
        count = len(games)
        return {
            "raw_runs_per_game": round(total_runs / count, 2),
            "adjusted_runs_per_game": round(total_runs / count, 2),  # Simplified
            "hits_per_game": round(total_hits / count, 1),
            "errors_per_game": round(total_errors / count, 2),
            "games_analyzed": count,
            "vs_league_avg": round((total_runs / count) - league_avg, 2)
        }
    
    def _calculate_soccer_adjusted_metrics(self, team_stats: List[Dict]) -> int:
        """Calculate Soccer opponent-adjusted metrics"""
        # Group by team
        team_games = {}
        for stat in team_stats:
            team_name = stat.get("team_name")
            if team_name not in team_games:
                team_games[team_name] = []
            team_games[team_name].append(stat)
        
        # Calculate league averages
        total_shots = sum(self._extract_numeric(s.get("stats", {}).get("SHOTS", "0")) for s in team_stats)
        total_possession = sum(self._extract_numeric(s.get("stats", {}).get("Possession", "0")) for s in team_stats)
        avg_shots = total_shots / len(team_stats) if team_stats else 12.0
        avg_possession = total_possession / len(team_stats) if team_stats else 50.0
        
        # Calculate adjusted metrics for each team
        adjusted_count = 0
        for team_name, games in team_games.items():
            metrics = self._calculate_team_metrics_soccer(team_name, games, avg_shots, avg_possession)
            if metrics:
                self._store_adjusted_metrics(team_name, metrics, "soccer_epl")
                adjusted_count += 1
        
        return adjusted_count
    
    def _calculate_team_metrics_soccer(self, team_name: str, games: List[Dict], league_avg_shots: float, league_avg_possession: float) -> Optional[Dict]:
        """Calculate metrics for a Soccer team"""
        if not games:
            return None
        
        total_shots = 0
        total_on_target = 0
        total_possession = 0
        total_passes = 0
        total_accurate_passes = 0
        
        for game in games:
            stats = game.get("stats", {})
            total_shots += self._extract_numeric(stats.get("SHOTS", "0"))
            total_on_target += self._extract_numeric(stats.get("ON GOAL", "0"))
            total_possession += self._extract_numeric(stats.get("Possession", "0"))
            total_passes += self._extract_numeric(stats.get("Passes", "0"))
            total_accurate_passes += self._extract_numeric(stats.get("Accurate Passes", "0"))
        
        count = len(games)
        pass_accuracy = (total_accurate_passes / total_passes * 100) if total_passes > 0 else 0
        shot_accuracy = (total_on_target / total_shots * 100) if total_shots > 0 else 0
        
        return {
            "shots_per_game": round(total_shots / count, 1),
            "adjusted_shots_per_game": round(total_shots / count, 1),  # Simplified
            "shots_on_target_per_game": round(total_on_target / count, 1),
            "shot_accuracy_pct": round(shot_accuracy, 1),
            "avg_possession_pct": round(total_possession / count, 1),
            "pass_accuracy_pct": round(pass_accuracy, 1),
            "games_analyzed": count,
            "vs_league_avg_shots": round((total_shots / count) - league_avg_shots, 1),
            "vs_league_avg_possession": round((total_possession / count) - league_avg_possession, 1)
        }
    
    def _store_adjusted_metrics(self, team_name: str, metrics: Dict, sport: str) -> None:
        """Store opponent-adjusted metrics"""
        normalized_name = team_name.lower().replace(" ", "_")
        pk = f"ADJUSTED_METRICS#{sport}#{normalized_name}"
        sk = datetime.utcnow().isoformat()
        
        self.table.put_item(
            Item={
                "pk": pk,
                "sk": sk,
                "sport": sport,
                "team_name": team_name,
                "metrics": self._convert_to_decimal(metrics),
                "calculated_at": sk,
                "latest": True
            }
        )
    
    def _extract_numeric(self, value: str) -> float:
        """Extract numeric value from string"""
        try:
            return float(str(value).replace(",", "").replace("%", ""))
        except:
            return 0.0


def lambda_handler(event, context):
    """AWS Lambda handler for team stats collection"""
    try:
        collector = TeamStatsCollector()
        sport = event.get("sport", "basketball_nba")

        games_processed = collector.collect_stats_for_sport(sport)

        return {
            "statusCode": 200,
            "body": {
                "message": f"Collected team stats for {games_processed} games",
                "sport": sport,
                "games_processed": games_processed,
            },
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Emit CloudWatch metric
        try:
            import boto3
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.put_metric_data(
                Namespace='SportsAnalytics/TeamStatsCollector',
                MetricData=[{
                    'MetricName': 'CollectionError',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Sport', 'Value': event.get('sport', 'unknown') if event else 'unknown'}
                    ]
                }]
            )
        except:
            pass
        
        return {"statusCode": 500, "body": {"error": str(e)}}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    collector = TeamStatsCollector()
    collector.collect_stats_for_sport("basketball_nba")
