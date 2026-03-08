"""Hot/Cold Model - Track recent form and momentum"""

import logging
from typing import Any, Dict, List

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class HotColdModel(BaseModel):
    """Hot/Cold model: Track recent form and momentum"""

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

        home_record = self._get_recent_record(home_team, sport, lookback=10)
        away_record = self._get_recent_record(away_team, sport, lookback=10)

        home_form = self._calculate_form_score(home_record)
        away_form = self._calculate_form_score(away_record)

        form_diff = home_form - away_form

        if abs(form_diff) > 0.3:
            confidence = 0.75
            if form_diff > 0:
                prediction = home_team
                reasoning = f"Strong home form: {home_record['wins']}-{home_record['losses']} last {home_record['games']} games. Away: {away_record['wins']}-{away_record['losses']}."
            else:
                prediction = away_team
                reasoning = f"Strong away form: {away_record['wins']}-{away_record['losses']} last {away_record['games']} games. Home: {home_record['wins']}-{home_record['losses']}."
        elif abs(form_diff) > 0.15:
            confidence = 0.65
            if form_diff > 0:
                prediction = home_team
                reasoning = f"Home team trending up ({home_record['wins']}-{home_record['losses']}), away trending down ({away_record['wins']}-{away_record['losses']})."
            else:
                prediction = away_team
                reasoning = f"Away team trending up ({away_record['wins']}-{away_record['losses']}), home trending down ({home_record['wins']}-{home_record['losses']})."
        else:
            confidence = 0.55
            prediction = home_team
            reasoning = f"Similar recent form. Home: {home_record['wins']}-{home_record['losses']}, Away: {away_record['wins']}-{away_record['losses']}. Slight home edge."

        return AnalysisResult(
            game_id=game_id,
            model="hot_cold",
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

    def _get_recent_record(
        self, team: str, sport: str, lookback: int = 10
    ) -> Dict[str, int]:
        try:
            normalized_team = team.lower().replace(" ", "_")
            response = self.table.query(
                IndexName="TeamOutcomesIndex",
                KeyConditionExpression="team_outcome_pk = :pk",
                ExpressionAttributeValues={
                    ":pk": f"TEAM#{sport}#{normalized_team}",
                },
                Limit=lookback,
                ScanIndexForward=False,
            )

            items = response.get("Items", [])[:lookback]

            if not items:
                return {"wins": 5, "losses": 5, "games": 10}

            wins = 0
            losses = 0

            for item in items:
                winner = item.get("winner")
                if winner == team:
                    wins += 1
                elif winner and winner != "draw":
                    losses += 1

            total_games = wins + losses
            if total_games == 0:
                return {"wins": 5, "losses": 5, "games": 10}

            return {"wins": wins, "losses": losses, "games": total_games}

        except Exception as e:
            logger.error(f"Error querying recent record: {e}", exc_info=True)
            return {"wins": 5, "losses": 5, "games": 10}

    def _calculate_form_score(self, record: Dict[str, int]) -> float:
        games = record["games"]
        if games == 0:
            return 0.5

        win_pct = record["wins"] / games

        if record["wins"] >= games * 0.7:
            return min(win_pct * 1.2, 1.0)
        elif record["losses"] >= games * 0.7:
            return max(win_pct * 0.8, 0.0)
        else:
            return win_pct

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            player_name = prop_item.get("player_name", "Unknown Player")
            sport = prop_item.get("sport")
            market_key = prop_item.get("market_key", "")
            line = prop_item.get("point", 0)

            recent_stats = self._get_recent_player_stats(player_name, sport, market_key)

            if not recent_stats or recent_stats["games"] == 0:
                return None

            avg_stat = recent_stats["average"]
            line_float = float(line)
            
            if avg_stat > line_float * 1.1:
                confidence = 0.75
                prediction = f"Over {line}"
                reasoning = f"{player_name} is HOT: Averaging {avg_stat:.1f} in last {recent_stats['games']} games, well above the {line} line."
            elif avg_stat > line_float:
                confidence = 0.65
                prediction = f"Over {line}"
                reasoning = f"{player_name} playing well: Averaging {avg_stat:.1f} in last {recent_stats['games']} games."
            elif avg_stat < line_float * 0.9:
                confidence = 0.75
                prediction = f"Under {line}"
                reasoning = f"{player_name} is COLD: Averaging {avg_stat:.1f} in last {recent_stats['games']} games, well below the {line} line."
            elif avg_stat < line_float:
                confidence = 0.65
                prediction = f"Under {line}"
                reasoning = f"{player_name} struggling: Averaging {avg_stat:.1f} in last {recent_stats['games']} games"
            else:
                return None

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                model="hot_cold",
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
            logger.error(f"Error analyzing hot/cold prop odds: {e}", exc_info=True)
            return None

    def _get_recent_player_stats(
        self, player_name: str, sport: str, market_key: str, lookback: int = 10
    ) -> Dict[str, Any]:
        try:
            normalized_name = player_name.lower().replace(" ", "_")
            pk = f"PLAYER_STATS#{sport}#{normalized_name}"

            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                Limit=lookback,
                ScanIndexForward=False,
            )

            items = response.get("Items", [])

            if not items:
                return {"games": 0, "average": 0}

            stat_field = self._map_market_to_stat(market_key)
            weighted_sum = 0.0
            total_weight = 0.0
            games_count = 0

            for item in items:
                stats = item.get("stats", {})
                if stat_field in stats:
                    try:
                        value = float(stats[stat_field])
                        minutes = float(stats.get("MIN", 20))
                        weight = min(minutes / 30.0, 1.0) if minutes > 0 else 0.3

                        weighted_sum += value * weight
                        total_weight += weight
                        games_count += 1
                    except (ValueError, TypeError):
                        continue

            if games_count == 0 or total_weight == 0:
                return {"games": 0, "average": 0}

            weighted_avg = weighted_sum / total_weight

            return {"games": games_count, "average": weighted_avg}

        except Exception as e:
            logger.error(f"Error querying player stats: {e}", exc_info=True)
            return {"games": 0, "average": 0}

    def _map_market_to_stat(self, market_key: str) -> str:
        mapping = {
            "player_points": "PTS",
            "player_rebounds": "REB",
            "player_assists": "AST",
            "player_threes": "3PM",
            "player_blocks": "BLK",
            "player_steals": "STL",
            "player_turnovers": "TO",
        }
        return mapping.get(market_key, "PTS")
