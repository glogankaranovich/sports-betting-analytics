"""Player Stats Model - Simple prop betting using historical averages"""
import logging
import os
from typing import Dict, Optional
import boto3
from boto3.dynamodb.conditions import Key

from ml.models import BaseAnalysisModel, AnalysisResult

logger = logging.getLogger(__name__)


class PlayerStatsModel(BaseAnalysisModel):
    """Prop model that compares line to player historical averages"""
    
    def __init__(self):
        super().__init__()
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = os.getenv('DYNAMODB_TABLE', 'carpool-bets-v2-dev')
        self.table = dynamodb.Table(table_name)
        
        self.market_map = {
            'player_points': 'PTS',
            'player_rebounds': 'REB',
            'player_assists': 'AST',
            'player_threes': '3PM',
            'player_steals': 'STL',
            'player_blocks': 'BLK',
        }
    
    def analyze_game_odds(self, game_id: str, odds_items, game_info: Dict) -> AnalysisResult:
        """Not used - this model only does props"""
        return None
    
    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Compare line to weighted player averages with opponent adjustments"""
        try:
            player_name = prop_item.get('player_name')
            sport = prop_item.get('sport')
            market = prop_item.get('market_key')
            line = float(prop_item.get('point', 0))
            opponent = prop_item.get('away_team') or prop_item.get('home_team')
            
            if not all([player_name, sport, market, line]):
                return None
            
            stats = self._get_player_stats(player_name, sport, market, opponent)
            if not stats or stats['games'] < 5:
                return None
            
            # Get news sentiment for player
            news_boost = self._get_news_boost(player_name, sport)
            
            avg = stats['avg']
            last5 = stats['last5']
            vs_opp = stats.get('vs_opponent_avg')
            avg_pm = stats.get('avg_plus_minus', 0)
            
            if avg == 0:
                return None
            
            # Only bet on hot/cold streaks with positive team impact
            form_diff = abs(last5 - avg) / avg if avg > 0 else 0
            
            # Require strong streak (25%) OR positive +/- with moderate streak (15%)
            if form_diff >= 0.25:
                # Strong streak, don't need +/-
                pass
            elif form_diff >= 0.15 and avg_pm > 2:
                # Moderate streak with strong team performance
                pass
            else:
                return None
            
            # Weight recent form heavily
            weighted_avg = (last5 * 0.75) + (avg * 0.25)
            
            # Add opponent adjustment if available
            has_opponent_data = vs_opp and stats.get('vs_opponent_games', 0) >= 2
            if has_opponent_data:
                weighted_avg = (weighted_avg * 0.7) + (vs_opp * 0.3)
            
            diff_pct = abs(line - weighted_avg) / weighted_avg
            
            # Base confidence
            base_conf = 0.74 if has_opponent_data else 0.71
            base_conf += news_boost  # Add news sentiment boost
            
            # 13.5% threshold
            if line < weighted_avg * 0.865:
                prediction = f"Over {line}"
                confidence = min(0.83, base_conf + diff_pct * 0.08)
                reasoning = f"{player_name} streak: L5 {last5:.1f} vs {avg:.1f}"
            elif line > weighted_avg * 1.135:
                prediction = f"Under {line}"
                confidence = min(0.83, base_conf + diff_pct * 0.08)
                reasoning = f"{player_name} streak: L5 {last5:.1f} vs {avg:.1f}"
            else:
                return None
            
            return AnalysisResult(
                game_id=prop_item.get('event_id', 'unknown'),
                model='player_stats',
                analysis_type='prop',
                sport=sport,
                home_team=prop_item.get('home_team'),
                away_team=prop_item.get('away_team'),
                commence_time=prop_item.get('commence_time'),
                player_name=player_name,
                market_key=market,
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
                bookmaker=prop_item.get('bookmaker', 'fanduel'),
                recommended_odds=-110,
            )
        except Exception as e:
            logger.error(f"Error in player_stats prop analysis: {e}")
            return None
    
    def _get_player_stats(self, player_name: str, sport: str, market: str, opponent: str = None) -> Optional[Dict]:
        """Get player averages with opponent-specific data and minutes filter"""
        try:
            stat_key = self.market_map.get(market)
            if not stat_key:
                return None
            
            normalized = player_name.lower().replace(' ', '_')
            response = self.table.query(
                KeyConditionExpression=Key('pk').eq(f'PLAYER_STATS#{sport}#{normalized}'),
                ScanIndexForward=False,
                Limit=20
            )
            
            games = response.get('Items', [])
            values = []
            vs_opponent_values = []
            recent_plus_minus = []
            
            for game in games:
                stats = game.get('stats', {})
                
                # Filter out games with low minutes (< 20 min)
                try:
                    minutes = float(stats.get('MIN', 0))
                    if minutes < 20:
                        continue
                except:
                    pass
                
                val = stats.get(stat_key)
                if val:
                    try:
                        if '-' in str(val):
                            val = val.split('-')[0]
                        val_float = float(val)
                        values.append(val_float)
                        
                        # Track +/- for last 5 games
                        if len(recent_plus_minus) < 5:
                            try:
                                pm = float(stats.get('+/-', 0))
                                recent_plus_minus.append(pm)
                            except:
                                pass
                        
                        # Track opponent-specific performance
                        if opponent and stats.get('opponent') == opponent:
                            vs_opponent_values.append(val_float)
                    except:
                        pass
            
            if len(values) < 5:
                return None
            
            result = {
                'avg': sum(values) / len(values),
                'last5': sum(values[:5]) / min(5, len(values)),
                'games': len(values)
            }
            
            # Add plus/minus indicator
            if recent_plus_minus:
                result['avg_plus_minus'] = sum(recent_plus_minus) / len(recent_plus_minus)
            
            if vs_opponent_values:
                result['vs_opponent_avg'] = sum(vs_opponent_values) / len(vs_opponent_values)
                result['vs_opponent_games'] = len(vs_opponent_values)
            
            return result
        except Exception as e:
            logger.error(f"Error getting player stats: {e}")
            return None
    
    def _get_news_boost(self, player_name: str, sport: str) -> float:
        """Get confidence boost from recent news sentiment"""
        try:
            from news_features import get_player_sentiment
            
            sentiment = get_player_sentiment(sport, player_name, hours=48)
            
            # Boost confidence if positive news with high impact
            if sentiment['news_count'] > 0:
                score = sentiment['sentiment_score']
                impact = sentiment['impact_score']
                
                # Positive news with high impact = boost confidence
                if score > 0.3 and impact > 1.5:
                    return 0.02
                elif score < -0.3 and impact > 1.5:
                    # Negative news = reduce confidence
                    return -0.02
            
            return 0.0
        except Exception as e:
            logger.error(f"Error getting news sentiment: {e}")
            return 0.0
