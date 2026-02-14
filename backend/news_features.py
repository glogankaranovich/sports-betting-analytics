"""
News Feature Extractor

Extracts news sentiment features for prediction models.
Supports both team and player-level sentiment analysis.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List

import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "carpool-bets-v2-dev")
table = dynamodb.Table(TABLE_NAME)


def get_news_sentiment(sport: str, search_terms: List[str], hours: int = 48) -> Dict:
    """Get aggregated news sentiment for team or player"""
    pk = f"NEWS#{sport}"
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    response = table.query(
        KeyConditionExpression="pk = :pk AND sk > :cutoff",
        ExpressionAttributeValues={":pk": pk, ":cutoff": cutoff},
    )

    items = response.get("Items", [])

    # Find news mentioning any of the search terms
    relevant_news = []
    for item in items:
        text = f"{item.get('headline', '')} {item.get('description', '')}".lower()
        if any(term.lower() in text for term in search_terms):
            relevant_news.append(item)

    if not relevant_news:
        return {"sentiment_score": 0.0, "impact_score": 0.0, "news_count": 0}

    # Calculate weighted sentiment score
    impact_weights = {"high": 3.0, "medium": 2.0, "low": 1.0}
    total_weight = 0
    weighted_sentiment = 0

    for news in relevant_news:
        weight = impact_weights.get(news.get("impact", "low"), 1.0)
        sentiment = news.get("sentiment_positive", 0.5) - news.get(
            "sentiment_negative", 0.5
        )
        weighted_sentiment += sentiment * weight
        total_weight += weight

    sentiment_score = weighted_sentiment / total_weight if total_weight > 0 else 0.0
    impact_score = total_weight / len(relevant_news) if relevant_news else 0.0

    return {
        "sentiment_score": round(sentiment_score, 3),
        "impact_score": round(impact_score, 2),
        "news_count": len(relevant_news),
    }


def get_player_sentiment(sport: str, player_name: str, hours: int = 48) -> Dict:
    """Get news sentiment for a specific player"""
    return get_news_sentiment(sport, [player_name], hours)


def get_team_sentiment(sport: str, team_name: str, hours: int = 48) -> Dict:
    """Get news sentiment for a team"""
    return get_news_sentiment(sport, [team_name], hours)
