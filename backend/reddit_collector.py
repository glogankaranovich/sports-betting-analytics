"""
Reddit Sentiment Collector

Collects fan sentiment from sports subreddits.
Uses Reddit API (free, no authentication required for read-only).
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3

from constants import SUPPORTED_SPORTS

dynamodb = boto3.resource("dynamodb")
comprehend = boto3.client("comprehend")
TABLE_NAME = os.environ.get("TABLE_NAME", "carpool-bets-v2-dev")
table = dynamodb.Table(TABLE_NAME)


class RedditCollector:
    """Collects sentiment from sports subreddits"""

    def __init__(self):
        self.base_url = "https://www.reddit.com"

        # Subreddit mappings
        self.sport_subreddits = {
            "basketball_nba": ["nba"],
            "americanfootball_nfl": ["nfl"],
            "icehockey_nhl": ["hockey"],
            "baseball_mlb": ["baseball"],
            "soccer_epl": ["PremierLeague", "soccer"],
        }

        # Team subreddits (major teams)
        self.team_subreddits = {
            "basketball_nba": {
                "LAL": "lakers",
                "GSW": "warriors",
                "BOS": "bostonceltics",
                "MIA": "heat",
            },
            "americanfootball_nfl": {
                "KC": "KansasCityChiefs",
                "SF": "49ers",
                "BUF": "buffalobills",
                "DAL": "cowboys",
            },
            "icehockey_nhl": {
                "TOR": "leafs",
                "BOS": "BostonBruins",
                "COL": "ColoradoAvalanche",
            },
        }

    def collect_sentiment_for_sport(self, sport: str) -> Dict:
        """Collect Reddit sentiment for a specific sport"""
        subreddits = self.sport_subreddits.get(sport, [])
        if not subreddits:
            return {"sport": sport, "posts_collected": 0}

        total_posts = 0

        for subreddit in subreddits:
            posts = self._get_hot_posts(subreddit)
            if posts:
                sentiment_data = self._analyze_posts(posts, sport, subreddit)
                if sentiment_data:
                    self._store_sentiment(sentiment_data)
                    total_posts += len(posts)

        return {"sport": sport, "posts_collected": total_posts}

    def _get_hot_posts(self, subreddit: str, limit: int = 25) -> List[Dict]:
        """Get hot posts from subreddit (no auth required)"""
        import requests

        url = f"{self.base_url}/r/{subreddit}/hot.json"
        headers = {"User-Agent": "SportsAnalytics/1.0"}
        params = {"limit": limit}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            posts = []
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                posts.append(
                    {
                        "title": post.get("title", ""),
                        "text": post.get("selftext", ""),
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                        "created_utc": post.get("created_utc", 0),
                    }
                )

            return posts

        except Exception as e:
            print(f"Error getting Reddit posts from r/{subreddit}: {e}")
            return []

    def _analyze_posts(
        self, posts: List[Dict], sport: str, subreddit: str
    ) -> Optional[Dict]:
        """Analyze sentiment of Reddit posts using AWS Comprehend"""
        if not posts:
            return None

        # Combine titles and text for sentiment analysis
        texts = [f"{p['title']} {p['text']}"[:5000] for p in posts[:25]]

        try:
            response = comprehend.batch_detect_sentiment(
                TextList=texts, LanguageCode="en"
            )

            sentiment_counts = {
                "POSITIVE": 0,
                "NEGATIVE": 0,
                "NEUTRAL": 0,
                "MIXED": 0,
            }

            total_score = 0.0

            for result in response["ResultList"]:
                sentiment = result["Sentiment"]
                sentiment_counts[sentiment] += 1

                # Convert to numeric score
                scores = result["SentimentScore"]
                score = (
                    scores["Positive"] * 1.0
                    + scores["Negative"] * -1.0
                    + scores["Neutral"] * 0.0
                    + scores["Mixed"] * 0.0
                )
                total_score += score

            avg_score = total_score / len(texts) if texts else 0.0

            # Calculate engagement score (upvotes + comments)
            total_engagement = sum(p["score"] + p["num_comments"] for p in posts)

            return {
                "sport": sport,
                "subreddit": subreddit,
                "sentiment_score": round(avg_score, 3),
                "post_count": len(posts),
                "positive_count": sentiment_counts["POSITIVE"],
                "negative_count": sentiment_counts["NEGATIVE"],
                "neutral_count": sentiment_counts["NEUTRAL"],
                "mixed_count": sentiment_counts["MIXED"],
                "engagement_score": total_engagement,
                "top_posts": posts[:5],
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"Error analyzing Reddit sentiment: {e}")
            return None

    def _store_sentiment(self, sentiment_data: Dict):
        """Store Reddit sentiment in DynamoDB"""
        pk = f"REDDIT_SENTIMENT#{sentiment_data['sport']}#{sentiment_data['subreddit']}"
        sk = sentiment_data["timestamp"]

        # Calculate TTL (24 hours from now)
        ttl = int((datetime.utcnow() + timedelta(hours=24)).timestamp())

        item = {
            "pk": pk,
            "sk": sk,
            "sport": sentiment_data["sport"],
            "subreddit": sentiment_data["subreddit"],
            "sentiment_score": sentiment_data["sentiment_score"],
            "post_count": sentiment_data["post_count"],
            "positive_count": sentiment_data["positive_count"],
            "negative_count": sentiment_data["negative_count"],
            "neutral_count": sentiment_data["neutral_count"],
            "mixed_count": sentiment_data["mixed_count"],
            "engagement_score": sentiment_data["engagement_score"],
            "top_posts": sentiment_data["top_posts"],
            "ttl": ttl,
            "updated_at": sentiment_data["timestamp"],
        }

        table.put_item(Item=item)
        print(
            f"Stored Reddit sentiment for r/{sentiment_data['subreddit']}: "
            f"{sentiment_data['sentiment_score']} ({sentiment_data['post_count']} posts)"
        )

    def get_recent_sentiment(
        self, sport: str, subreddit: str, hours: int = 24
    ) -> List[Dict]:
        """Get recent Reddit sentiment"""
        pk = f"REDDIT_SENTIMENT#{sport}#{subreddit}"
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        response = table.query(
            KeyConditionExpression="pk = :pk AND sk > :cutoff",
            ExpressionAttributeValues={":pk": pk, ":cutoff": cutoff_time},
            ScanIndexForward=False,
            Limit=50,
        )

        return response.get("Items", [])


def lambda_handler(event, context):
    """AWS Lambda handler for Reddit sentiment collection"""
    try:
        collector = RedditCollector()

        # Collect for all supported sports
        sports = event.get("sports", SUPPORTED_SPORTS)
        results = {}

        for sport in sports:
            result = collector.collect_sentiment_for_sport(sport)
            results[sport] = result

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Reddit sentiment collection completed",
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
