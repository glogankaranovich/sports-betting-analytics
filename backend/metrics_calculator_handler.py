"""
Lambda handler for opponent-adjusted metrics calculation
"""
import json
import os
from team_stats_collector import TeamStatsCollector

def lambda_handler(event, context):
    """Calculate opponent-adjusted metrics for all sports"""
    collector = TeamStatsCollector()
    
    sports = ['basketball_nba', 'americanfootball_nfl', 'soccer_epl', 'icehockey_nhl']
    results = {}
    
    for sport in sports:
        try:
            metrics_count = collector.calculate_opponent_adjusted_metrics(sport)
            results[sport] = metrics_count
            print(f"Calculated {metrics_count} opponent-adjusted metrics for {sport}")
        except Exception as e:
            print(f"Error calculating metrics for {sport}: {e}")
            results[sport] = 0
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'metrics_calculated': results,
            'total': sum(results.values())
        })
    }
