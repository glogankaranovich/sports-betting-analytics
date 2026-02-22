"""Lambda handler for collecting team season stats from ESPN API"""
import json
import os
from team_season_stats_collector import TeamSeasonStatsCollector

# ESPN team abbreviations by sport
TEAM_ABBRS = {
    'basketball_nba': [
        'atl', 'bos', 'bkn', 'cha', 'chi', 'cle', 'dal', 'den', 'det', 'gs',
        'hou', 'ind', 'lac', 'lal', 'mem', 'mia', 'mil', 'min', 'no', 'ny',
        'okc', 'orl', 'phi', 'phx', 'por', 'sac', 'sa', 'tor', 'utah', 'wsh'
    ],
    'americanfootball_nfl': [
        'ari', 'atl', 'bal', 'buf', 'car', 'chi', 'cin', 'cle', 'dal', 'den',
        'det', 'gb', 'hou', 'ind', 'jax', 'kc', 'lv', 'lac', 'lar', 'mia',
        'min', 'ne', 'no', 'nyg', 'nyj', 'phi', 'pit', 'sf', 'sea', 'tb',
        'ten', 'wsh'
    ],
    'icehockey_nhl': [
        'ana', 'ari', 'bos', 'buf', 'car', 'cbj', 'cgy', 'chi', 'col', 'dal',
        'det', 'edm', 'fla', 'la', 'min', 'mtl', 'nj', 'nsh', 'nyi', 'nyr',
        'ott', 'phi', 'pit', 'sj', 'sea', 'stl', 'tb', 'tor', 'van', 'vgk',
        'wpg', 'wsh'
    ],
    'baseball_mlb': [
        'ari', 'atl', 'bal', 'bos', 'chc', 'chw', 'cin', 'cle', 'col', 'det',
        'hou', 'kc', 'laa', 'lad', 'mia', 'mil', 'min', 'nym', 'nyy', 'oak',
        'phi', 'pit', 'sd', 'sf', 'sea', 'stl', 'tb', 'tex', 'tor', 'wsh'
    ]
}


def lambda_handler(event, context):
    """Collect team season stats for specified sport(s)"""
    try:
        # Support both single sport and multiple sports
        sports = event.get('sports', [event.get('sport')]) if event.get('sport') else event.get('sports', [])
        
        if not sports:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'sport or sports parameter required'})
            }
        
        collector = TeamSeasonStatsCollector()
        all_results = {}
        
        for sport in sports:
            if sport not in TEAM_ABBRS:
                all_results[sport] = {'error': f'Unsupported sport: {sport}'}
                continue
            
            results = {'collected': 0, 'failed': 0, 'errors': []}
            
            for team_abbr in TEAM_ABBRS[sport]:
                try:
                    stats = collector.collect_team_stats(sport, team_abbr)
                    if stats:
                        results['collected'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f'{team_abbr}: No stats returned')
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f'{team_abbr}: {str(e)}')
            
            all_results[sport] = results
        
        return {
            'statusCode': 200,
            'body': json.dumps({'results': all_results})
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        import traceback
        traceback.print_exc()
        
        # Emit CloudWatch metric
        try:
            import boto3
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.put_metric_data(
                Namespace='SportsAnalytics/SeasonStatsCollector',
                MetricData=[{
                    'MetricName': 'CollectionError',
                    'Value': 1,
                    'Unit': 'Count'
                }]
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
