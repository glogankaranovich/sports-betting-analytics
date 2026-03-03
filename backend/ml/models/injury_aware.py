"""InjuryAware Model - Adjust predictions based on player injuries"""

import logging
from typing import Dict, List, Optional

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class InjuryAwareModel(BaseModel):
    """Injury-Aware model: Adjust predictions based on player injuries"""

    def __init__(self, dynamodb_table=None):
        import os
        import boto3

        self.table = dynamodb_table
        if not self.table:
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        sport = game_info.get("sport")

        home_injuries = self._get_team_injuries(home_team, sport)
        away_injuries = self._get_team_injuries(away_team, sport)

        home_impact = self._calculate_injury_impact(home_injuries)
        away_impact = self._calculate_injury_impact(away_injuries)

        impact_diff = away_impact - home_impact

        if abs(impact_diff) > 0.3:
            confidence = 0.75
            if impact_diff > 0:
                prediction = home_team
                reasoning = f"{away_team} has {len(away_injuries)} key injuries. {home_team} healthier with {len(home_injuries)} injuries."
            else:
                prediction = away_team
                reasoning = f"{home_team} has {len(home_injuries)} key injuries. {away_team} healthier with {len(away_injuries)} injuries."
        elif abs(impact_diff) > 0.15:
            confidence = 0.65
            if impact_diff > 0:
                prediction = home_team
                reasoning = f"{away_team} dealing with injuries ({len(away_injuries)} out). {home_team} advantage."
            else:
                prediction = away_team
                reasoning = f"{home_team} dealing with injuries ({len(home_injuries)} out). {away_team} advantage."
        else:
            confidence = 0.55
            prediction = home_team
            reasoning = f"Both teams relatively healthy. {home_team}: {len(home_injuries)} injuries, {away_team}: {len(away_injuries)} injuries."

        return AnalysisResult(
            game_id=game_id,
            model="injury_aware",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        try:
            player_name = prop_item.get("player_name", "Unknown Player")
            sport = prop_item.get("sport")
            market_key = prop_item.get("market_key", "")
            line = prop_item.get("point", 0)

            player_injury = self._get_player_injury_status(player_name, sport)

            if player_injury and player_injury.get("status") in ["Out", "Doubtful"]:
                return AnalysisResult(
                    game_id=prop_item.get("event_id", "unknown"),
                    model="injury_aware",
                    analysis_type="prop",
                    sport=sport,
                    home_team=prop_item.get("home_team"),
                    away_team=prop_item.get("away_team"),
                    commence_time=prop_item.get("commence_time"),
                    player_name=player_name,
                    market_key=market_key,
                    prediction=f"Under {line}",
                    confidence=0.9,
                    reasoning=f"{player_name} listed as {player_injury['status']} ({player_injury.get('injury_type', 'injury')}). Likely to underperform or not play.",
                    recommended_odds=-110,
                )

            if player_injury and player_injury.get("status") == "Questionable":
                confidence = 0.65
                prediction = f"Under {line}"
                status_note = f" (listed as Questionable - {player_injury.get('injury_type', 'injury')})"
                reasoning = f"{player_name}{status_note}. May be limited or sit out."
            else:
                confidence = 0.55
                prediction = f"Over {line}"
                reasoning = f"{player_name} healthy. No injury concerns."

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                model="injury_aware",
                analysis_type="prop",
                sport=sport,
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=player_name,
                market_key=market_key,
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
                recommended_odds=-110,
            )

        except Exception as e:
            logger.error(f"Error analyzing injury-aware prop: {e}", exc_info=True)
            return None

    def _get_team_injuries(self, team: str, sport: str) -> List[Dict]:
        try:
            team_id = self._get_team_id(team, sport)
            if not team_id:
                return []

            pk = f"INJURIES#{sport}#{team_id}"
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                Limit=1,
                ScanIndexForward=False,
            )

            items = response.get("Items", [])
            if items:
                return [
                    inj
                    for inj in items[0].get("injuries", [])
                    if inj.get("status") == "Out"
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting team injuries: {e}", exc_info=True)
            return []

    def _get_player_injury_status(self, player_name: str, sport: str) -> Optional[Dict]:
        try:
            normalized_name = player_name.lower().replace(" ", "_")
            pk = f"PLAYER_INJURY#{sport}#{normalized_name}"

            response = self.table.query(
                KeyConditionExpression="pk = :pk AND sk = :sk",
                ExpressionAttributeValues={":pk": pk, ":sk": "LATEST"},
                Limit=1,
            )

            items = response.get("Items", [])
            if items:
                item = items[0]
                return {
                    "status": item.get("status"),
                    "injury_type": item.get("injury_type"),
                    "return_date": item.get("return_date"),
                }

            return None

        except Exception as e:
            logger.error(f"Error checking player injury status: {e}", exc_info=True)
            return None

    def _calculate_injury_impact(self, injuries: List[Dict]) -> float:
        if not injuries:
            return 0.0

        total_impact = 0.0
        for injury in injuries:
            usage_rate = float(injury.get("usage_rate", 20))
            per = float(injury.get("per", 15))
            win_shares = float(injury.get("win_shares", 0))
            avg_minutes = float(injury.get("avg_minutes", 0))
            
            usage_score = min(usage_rate / 35, 1.0)
            per_score = min(max(per - 10, 0) / 20, 1.0)
            ws_score = min(win_shares / 10, 1.0)
            minutes_score = min(avg_minutes / 35, 1.0)
            
            player_value = (usage_score * 0.3 + per_score * 0.3 + 
                          ws_score * 0.2 + minutes_score * 0.2)
            
            status = injury.get("status", "Out")
            if status == "Out":
                severity = 1.0
            elif status == "Doubtful":
                severity = 0.8
            elif status == "Questionable":
                severity = 0.4
            else:
                severity = 0.2
            
            total_impact += player_value * severity

        return min(total_impact, 1.0)

    def _get_team_id(self, team_name: str, sport: str) -> Optional[str]:
        team_mapping = {
            "basketball_nba": {
                "Atlanta Hawks": "1", "Boston Celtics": "2", "Brooklyn Nets": "17",
                "Charlotte Hornets": "30", "Chicago Bulls": "4", "Cleveland Cavaliers": "5",
                "Dallas Mavericks": "6", "Denver Nuggets": "7", "Detroit Pistons": "8",
                "Golden State Warriors": "9", "Houston Rockets": "10", "Indiana Pacers": "11",
                "LA Clippers": "12", "Los Angeles Lakers": "13", "Memphis Grizzlies": "29",
                "Miami Heat": "14", "Milwaukee Bucks": "15", "Minnesota Timberwolves": "16",
                "New Orleans Pelicans": "3", "New York Knicks": "18", "Oklahoma City Thunder": "25",
                "Orlando Magic": "19", "Philadelphia 76ers": "20", "Phoenix Suns": "21",
                "Portland Trail Blazers": "22", "Sacramento Kings": "23", "San Antonio Spurs": "24",
                "Toronto Raptors": "28", "Utah Jazz": "26", "Washington Wizards": "27",
            },
            "basketball_wnba": {
                "Atlanta Dream": "1", "Chicago Sky": "2", "Connecticut Sun": "3",
                "Dallas Wings": "4", "Indiana Fever": "5", "Las Vegas Aces": "6",
                "Los Angeles Sparks": "7", "Minnesota Lynx": "8", "New York Liberty": "9",
                "Phoenix Mercury": "10", "Seattle Storm": "11", "Washington Mystics": "12",
            },
            "americanfootball_nfl": {
                "Arizona Cardinals": "22", "Atlanta Falcons": "1", "Baltimore Ravens": "33",
                "Buffalo Bills": "2", "Carolina Panthers": "29", "Chicago Bears": "3",
                "Cincinnati Bengals": "4", "Cleveland Browns": "5", "Dallas Cowboys": "6",
                "Denver Broncos": "7", "Detroit Lions": "8", "Green Bay Packers": "9",
                "Houston Texans": "34", "Indianapolis Colts": "11", "Jacksonville Jaguars": "30",
                "Kansas City Chiefs": "12", "Las Vegas Raiders": "13", "Los Angeles Chargers": "24",
                "Los Angeles Rams": "14", "Miami Dolphins": "15", "Minnesota Vikings": "16",
                "New England Patriots": "17", "New Orleans Saints": "18", "New York Giants": "19",
                "New York Jets": "20", "Philadelphia Eagles": "21", "Pittsburgh Steelers": "23",
                "San Francisco 49ers": "25", "Seattle Seahawks": "26", "Tampa Bay Buccaneers": "27",
                "Tennessee Titans": "10", "Washington Commanders": "28",
            },
            "baseball_mlb": {
                "Arizona Diamondbacks": "29", "Athletics": "11", "Atlanta Braves": "15",
                "Baltimore Orioles": "1", "Boston Red Sox": "2", "Chicago Cubs": "16",
                "Chicago White Sox": "4", "Cincinnati Reds": "17", "Cleveland Guardians": "5",
                "Colorado Rockies": "27", "Detroit Tigers": "6", "Houston Astros": "18",
                "Kansas City Royals": "7", "Los Angeles Angels": "3", "Los Angeles Dodgers": "19",
                "Miami Marlins": "28", "Milwaukee Brewers": "8", "Minnesota Twins": "9",
                "New York Mets": "21", "New York Yankees": "10", "Philadelphia Phillies": "22",
                "Pittsburgh Pirates": "23", "San Diego Padres": "25", "San Francisco Giants": "26",
                "Seattle Mariners": "12", "St. Louis Cardinals": "24", "Tampa Bay Rays": "30",
                "Texas Rangers": "13", "Toronto Blue Jays": "14", "Washington Nationals": "20",
            },
            "icehockey_nhl": {
                "Anaheim Ducks": "25", "Boston Bruins": "1", "Buffalo Sabres": "2",
                "Calgary Flames": "3", "Carolina Hurricanes": "7", "Chicago Blackhawks": "4",
                "Colorado Avalanche": "17", "Columbus Blue Jackets": "29", "Dallas Stars": "9",
                "Detroit Red Wings": "5", "Edmonton Oilers": "6", "Florida Panthers": "26",
                "Los Angeles Kings": "8", "Minnesota Wild": "30", "Montreal Canadiens": "10",
                "Nashville Predators": "27", "New Jersey Devils": "11", "New York Islanders": "12",
                "New York Rangers": "13", "Ottawa Senators": "14", "Philadelphia Flyers": "15",
                "Pittsburgh Penguins": "16", "San Jose Sharks": "18", "Seattle Kraken": "124292",
                "St. Louis Blues": "19", "Tampa Bay Lightning": "20", "Toronto Maple Leafs": "21",
                "Utah Mammoth": "129764", "Vancouver Canucks": "22", "Vegas Golden Knights": "37",
                "Washington Capitals": "23", "Winnipeg Jets": "28",
            },
            "soccer_epl": {
                "Arsenal": "1", "Aston Villa": "2", "Bournemouth": "91", "Brentford": "337",
                "Brighton": "131", "Chelsea": "4", "Crystal Palace": "6", "Everton": "7",
                "Fulham": "370", "Ipswich Town": "373", "Leicester City": "375", "Liverpool": "10",
                "Manchester City": "11", "Manchester United": "12", "Newcastle United": "13",
                "Nottingham Forest": "393", "Southampton": "20", "Tottenham": "21",
                "West Ham": "25", "Wolves": "38",
            },
            "soccer_usa_mls": {
                "Atlanta United": "1", "Austin FC": "2", "Charlotte FC": "3", "Chicago Fire": "4",
                "Colorado Rapids": "5", "Columbus Crew": "6", "DC United": "7", "FC Cincinnati": "8",
                "FC Dallas": "9", "Houston Dynamo": "10", "Inter Miami": "11", "LA Galaxy": "12",
                "LAFC": "13", "Minnesota United": "14", "Montreal Impact": "15", "Nashville SC": "16",
                "New England Revolution": "17", "New York City FC": "18", "New York Red Bulls": "19",
                "Orlando City": "20", "Philadelphia Union": "21", "Portland Timbers": "22",
                "Real Salt Lake": "23", "San Jose Earthquakes": "24", "Seattle Sounders": "25",
                "Sporting Kansas City": "26", "St. Louis City SC": "27", "Toronto FC": "28",
                "Vancouver Whitecaps": "29",
            },
            "basketball_ncaab": {},
            "basketball_wncaab": {},
            "americanfootball_ncaaf": {},
        }
        return team_mapping.get(sport, {}).get(team_name)
