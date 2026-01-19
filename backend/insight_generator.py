import boto3
import os
from typing import Dict, List
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table_name = os.getenv("DYNAMODB_TABLE")
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    """Generate top insights from analyses"""
    try:
        sport = event.get("sport", "basketball_nba")
        model = event.get("model", "consensus")
        min_confidence = float(event.get("min_confidence", 0.6))
        limit = int(event.get("limit", 10))

        # Get top game analyses
        game_insights = generate_insights_from_analyses(
            sport, model, "game", min_confidence, limit
        )

        # Get top prop analyses
        prop_insights = generate_insights_from_analyses(
            sport, model, "prop", min_confidence, limit
        )

        total_insights = len(game_insights) + len(prop_insights)

        return {
            "statusCode": 200,
            "body": {
                "message": f"Generated {total_insights} insights",
                "game_insights": len(game_insights),
                "prop_insights": len(prop_insights),
            },
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": {"error": str(e)}}


def generate_insights_from_analyses(
    sport: str, model: str, analysis_type: str, min_confidence: float, limit: int
) -> List[Dict]:
    """Generate insights from top analyses"""
    insights = []

    # Query all bookmakers for this sport/model/type
    bookmakers = ["fanduel", "draftkings", "betmgm", "caesars"]

    all_analyses = []
    for bookmaker in bookmakers:
        analysis_time_pk = f"ANALYSIS#{sport}#{bookmaker}#{model}#{analysis_type}"

        response = table.query(
            IndexName="AnalysisTimeGSI",
            KeyConditionExpression="analysis_time_pk = :pk",
            ExpressionAttributeValues={":pk": analysis_time_pk},
            Limit=50,
        )

        all_analyses.extend(response.get("Items", []))

    # Filter by confidence and sort
    high_confidence = [
        a for a in all_analyses if float(a.get("confidence", 0)) >= min_confidence
    ]
    sorted_analyses = sorted(
        high_confidence, key=lambda x: float(x.get("confidence", 0)), reverse=True
    )[:limit]

    # Create insight records
    for analysis in sorted_analyses:
        insight = create_insight_from_analysis(analysis)
        if insight:
            store_insight(insight)
            insights.append(insight)

    return insights


def create_insight_from_analysis(analysis: Dict) -> Dict:
    """Convert analysis to insight record"""
    try:
        insight_id = f"{analysis['game_id']}#{analysis['bookmaker']}#{analysis.get('player_name', 'game')}"

        insight = {
            "pk": f"INSIGHT#{analysis['sport']}#{insight_id}",
            "sk": f"{analysis['model']}#{analysis['analysis_type']}#LATEST",
            "insight_id": insight_id,
            "game_id": analysis["game_id"],
            "sport": analysis["sport"],
            "bookmaker": analysis["bookmaker"],
            "model": analysis["model"],
            "analysis_type": analysis["analysis_type"],
            "prediction": analysis["prediction"],
            "confidence": analysis["confidence"],
            "reasoning": analysis["reasoning"],
            "home_team": analysis.get("home_team"),
            "away_team": analysis.get("away_team"),
            "player_name": analysis.get("player_name"),
            "commence_time": analysis["commence_time"],
            "created_at": datetime.utcnow().isoformat(),
        }

        return insight

    except Exception as e:
        print(f"Error creating insight: {e}")
        return None


def store_insight(insight: Dict):
    """Store insight in DynamoDB"""
    try:
        # Convert floats to Decimal
        if isinstance(insight.get("confidence"), float):
            insight["confidence"] = Decimal(str(insight["confidence"]))

        table.put_item(Item=insight)
        print(f"Stored insight: {insight['pk']} {insight['sk']}")

    except Exception as e:
        print(f"Error storing insight: {e}")
