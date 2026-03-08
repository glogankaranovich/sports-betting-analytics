"""
Season Manager Lambda
Enables/disables EventBridge rules based on sport seasons
"""
import os
from datetime import datetime

import boto3

events_client = boto3.client("events")

SPORT_SEASONS = {
    "NBA": {"start": 10, "end": 6},
    "NFL": {"start": 9, "end": 2},
    "MLB": {"start": 3, "end": 10},
    "NHL": {"start": 10, "end": 6},
    "EPL": {"start": 8, "end": 5},
    "NCAAB": {"start": 11, "end": 4},
    "WNCAAB": {"start": 11, "end": 4},
    "NCAAF": {"start": 8, "end": 1},
    "MLS": {"start": 2, "end": 10},
    "WNBA": {"start": 5, "end": 10},
}


def is_in_season(sport: str, current_month: int) -> bool:
    """Check if current month is within sport season"""
    season = SPORT_SEASONS.get(sport)
    if not season:
        return False

    start, end = season["start"], season["end"]

    if start <= end:
        return start <= current_month <= end
    else:
        return current_month >= start or current_month <= end


def lambda_handler(event, context):
    """Enable/disable EventBridge rules based on current season"""
    try:
        current_month = datetime.now().month
        environment = os.environ.get("ENVIRONMENT", "dev")

        print(f"Running season manager for {environment} (month: {current_month})")

        paginator = events_client.get_paginator("list_rules")
        updated_rules = []

        # List all rules (no prefix filter since CDK generates complex names)
        for page in paginator.paginate():
            for rule in page["Rules"]:
                rule_name = rule["Name"]
                
                # Skip old Lambda-based rules (migrated to ECS)
                if "AnalysisSchedule-AnalysisRule" in rule_name or "PropsRule" in rule_name:
                    continue

                # Check if this is a sport-specific rule
                for sport in SPORT_SEASONS.keys():
                    # Match ECS-based rule patterns:
                    # - Dev-EcsTasks-AnalysisGenbasketballnba... (ECS analysis generators)
                    # - Dev-EcsTasks-PropsCollectorSchedule... (ECS props collector)
                    # - DailyNba... (stats/injury collectors)
                    # - DailyNBA... (schedule collectors)
                    sport_patterns = [
                        f"AnalysisGen{sport.lower()}",  # ECS analysis generators
                        f"PropsCollector",  # ECS props collector (sport-agnostic)
                        f"Daily{sport}",
                        f"Daily{sport.capitalize()}",
                        f"{sport}Stats",
                        f"{sport}Injury",
                        f"{sport}Schedule"
                    ]
                    
                    if any(pattern in rule_name for pattern in sport_patterns):
                        in_season = is_in_season(sport, current_month)
                        current_state = rule["State"]
                        desired_state = "ENABLED" if in_season else "DISABLED"

                        if current_state != desired_state:
                            if desired_state == "DISABLED":
                                events_client.disable_rule(Name=rule_name)
                            else:
                                events_client.enable_rule(Name=rule_name)

                            updated_rules.append(
                                {
                                    "rule": rule_name,
                                    "sport": sport,
                                    "from": current_state,
                                    "to": desired_state,
                                }
                            )
                            print(
                                f"Updated {rule_name}: {current_state} -> {desired_state}"
                            )
                        break

        return {
            "statusCode": 200,
            "body": {
                "message": f"Season manager completed for month {current_month}",
                "updated_rules": updated_rules,
                "total_updated": len(updated_rules)
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
                Namespace='SportsAnalytics/SeasonManager',
                MetricData=[{
                    'MetricName': 'ManagementError',
                    'Value': 1,
                    'Unit': 'Count'
                }]
            )
        except:
            pass
        
        return {"statusCode": 500, "body": {"error": str(e)}}
