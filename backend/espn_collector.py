"""
ESPN API News Collector

Collects official news, injury reports, and updates from ESPN API.
Completely free - no API key required.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3

from constants import SUPPORTED_SPORTS

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "carpool-bets-v2-dev")
table = dynamodb.Table(TABLE_NAME)


class ESPNCollector:
    """Collects news and injury data from ESPN API"""

    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports"

        # ESPN sport mappings
        self.sport_mappings = {
            "basketball_nba": {"league": "nba", "path": "basketball/nba"},
            "americanfootball_nfl": {"league": "nfl", "path": "football/nfl"},
            "icehockey_nhl": {"league": "nhl", "path": "hockey/nhl"},
            "baseball_mlb": {"league": "mlb", "path": "baseball/mlb"},
            "soccer_epl": {"league": "eng.1", "path": "soccer/eng.1"},
        }

    def collect_news_for_sport(self, sport: str) -> Dict:
        """Collect ESPN news for a specific sport"""
        import requests

        mapping = self.sport_mappings.get(sport)
        if not mapping:
            return {"sport": sport, "news_collected": 0}

        # Get news from ESPN
        news_url = f"{self.base_url}/{mapping['path']}/news"

        try:
            response = requests.get(news_url)
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            news_stored = 0

            for article in articles[:20]:  # Limit to 20 most recent
                news_data = self._parse_article(article, sport)
                if news_data:
                    self._store_news(news_data)
                    news_stored += 1

            return {"sport": sport, "news_collected": news_stored}

        except Exception as e:
            print(f"Error collecting ESPN news for {sport}: {e}")
            return {"sport": sport, "news_collected": 0, "error": str(e)}

    def _parse_article(self, article: Dict, sport: str) -> Optional[Dict]:
        """Parse ESPN article into our format"""
        try:
            # Categorize by keywords
            headline = article.get("headline", "").lower()
            description = article.get("description", "").lower()
            text = f"{headline} {description}"

            impact = "low"
            keywords = []

            # High impact keywords
            if any(
                word in text
                for word in ["injury", "out", "suspended", "traded", "fired"]
            ):
                impact = "high"
                if "injury" in text or "out" in text:
                    keywords.append("injury")
                if "suspended" in text:
                    keywords.append("suspension")
                if "traded" in text or "trade" in text:
                    keywords.append("trade")
                if "fired" in text or "hired" in text:
                    keywords.append("coaching")

            # Medium impact keywords
            elif any(
                word in text
                for word in ["questionable", "doubtful", "lineup", "starting"]
            ):
                impact = "medium"
                if "questionable" in text or "doubtful" in text:
                    keywords.append("injury")
                if "lineup" in text or "starting" in text:
                    keywords.append("lineup")

            return {
                "sport": sport,
                "headline": article.get("headline", ""),
                "description": article.get("description", ""),
                "url": article.get("links", {}).get("web", {}).get("href", ""),
                "published": article.get("published", datetime.utcnow().isoformat()),
                "impact": impact,
                "keywords": keywords,
                "source": "ESPN",
            }

        except Exception as e:
            print(f"Error parsing article: {e}")
            return None

    def _store_news(self, news_data: Dict):
        """Store news in DynamoDB"""
        pk = f"NEWS#{news_data['sport']}"
        sk = news_data["published"]

        # Calculate TTL (7 days from now)
        ttl = int((datetime.utcnow() + timedelta(days=7)).timestamp())

        item = {
            "pk": pk,
            "sk": sk,
            "sport": news_data["sport"],
            "headline": news_data["headline"],
            "description": news_data["description"],
            "url": news_data["url"],
            "impact": news_data["impact"],
            "keywords": news_data["keywords"],
            "source": news_data["source"],
            "ttl": ttl,
            "updated_at": datetime.utcnow().isoformat(),
        }

        table.put_item(Item=item)
        print(
            f"Stored ESPN news: {news_data['headline'][:50]}... (impact: {news_data['impact']})"
        )

    def get_recent_news(self, sport: str, hours: int = 24) -> List[Dict]:
        """Get recent news for a sport"""
        pk = f"NEWS#{sport}"
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        response = table.query(
            KeyConditionExpression="pk = :pk AND sk > :cutoff",
            ExpressionAttributeValues={":pk": pk, ":cutoff": cutoff_time},
            ScanIndexForward=False,
            Limit=50,
        )

        return response.get("Items", [])

    def get_high_impact_news(self, sport: str, hours: int = 24) -> List[Dict]:
        """Get high impact news only"""
        all_news = self.get_recent_news(sport, hours)
        return [n for n in all_news if n.get("impact") == "high"]


def lambda_handler(event, context):
    """AWS Lambda handler for ESPN news collection"""
    try:
        collector = ESPNCollector()

        # Collect for all supported sports
        sports = event.get("sports", SUPPORTED_SPORTS)
        results = {}

        for sport in sports:
            result = collector.collect_news_for_sport(sport)
            results[sport] = result

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "ESPN news collection completed",
                    "results": results,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
            ),
        }
