"""Reddit crawler for sports betting insights and discussions."""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
import json

logger = logging.getLogger(__name__)

@dataclass
class RedditPost:
    """Reddit post data structure."""
    id: str
    title: str
    content: str
    author: str
    score: int
    num_comments: int
    created_utc: float
    subreddit: str
    url: str
    flair: Optional[str] = None

@dataclass
class BettingInsight:
    """Extracted betting insight from Reddit."""
    post_id: str
    sport: str
    teams: List[str]
    bet_type: str  # "spread", "moneyline", "over_under", "prop"
    confidence: float  # 0-1 score
    reasoning: str
    source_url: str
    created_at: datetime

class RedditCrawler:
    """Crawler for Reddit sports betting discussions."""
    
    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.subreddits = [
            "sportsbook",
            "sportsbetting", 
            "DraftKings",
            "fanduel",
            "nfl",
            "nba",
            "mlb",
            "nhl"
        ]
        
        # Betting keywords for filtering
        self.bet_keywords = [
            "bet", "wager", "pick", "lock", "play", "odds", "line",
            "spread", "moneyline", "over", "under", "prop", "parlay"
        ]
        
        # Team name patterns (simplified - would need full team lists)
        self.team_patterns = {
            "nfl": ["chiefs", "bills", "cowboys", "patriots", "packers"],
            "nba": ["lakers", "warriors", "celtics", "heat", "nets"],
            "mlb": ["yankees", "dodgers", "astros", "braves", "red sox"],
            "nhl": ["rangers", "bruins", "lightning", "avalanche", "kings"]
        }
    
    async def fetch_subreddit_posts(self, subreddit: str, limit: int = 25) -> List[RedditPost]:
        """Fetch recent posts from a subreddit."""
        url = f"{self.base_url}/r/{subreddit}/hot.json?limit={limit}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers={"User-Agent": "SportsAnalytics/1.0"}) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = []
                        
                        for post_data in data["data"]["children"]:
                            post = post_data["data"]
                            
                            # Filter for betting-related posts
                            if self._is_betting_related(post["title"], post.get("selftext", "")):
                                reddit_post = RedditPost(
                                    id=post["id"],
                                    title=post["title"],
                                    content=post.get("selftext", ""),
                                    author=post["author"],
                                    score=post["score"],
                                    num_comments=post["num_comments"],
                                    created_utc=post["created_utc"],
                                    subreddit=subreddit,
                                    url=f"{self.base_url}{post['permalink']}",
                                    flair=post.get("link_flair_text")
                                )
                                posts.append(reddit_post)
                        
                        logger.info(f"Fetched {len(posts)} betting posts from r/{subreddit}")
                        return posts
                        
                    else:
                        logger.error(f"Failed to fetch r/{subreddit}: {response.status}")
                        return []
                        
            except Exception as e:
                logger.error(f"Error fetching r/{subreddit}: {e}")
                return []
    
    def _is_betting_related(self, title: str, content: str) -> bool:
        """Check if post is betting-related."""
        text = f"{title} {content}".lower()
        return any(keyword in text for keyword in self.bet_keywords)
    
    def extract_betting_insights(self, posts: List[RedditPost]) -> List[BettingInsight]:
        """Extract structured betting insights from posts."""
        insights = []
        
        for post in posts:
            text = f"{post.title} {post.content}".lower()
            
            # Extract sport
            sport = self._extract_sport(post.subreddit, text)
            if not sport:
                continue
            
            # Extract teams
            teams = self._extract_teams(sport, text)
            if not teams:
                continue
            
            # Extract bet type and confidence
            bet_type = self._extract_bet_type(text)
            confidence = self._calculate_confidence(post, text)
            
            insight = BettingInsight(
                post_id=post.id,
                sport=sport,
                teams=teams,
                bet_type=bet_type,
                confidence=confidence,
                reasoning=post.title[:200],  # Truncated reasoning
                source_url=post.url,
                created_at=datetime.fromtimestamp(post.created_utc)
            )
            
            insights.append(insight)
        
        return insights
    
    def _extract_sport(self, subreddit: str, text: str) -> Optional[str]:
        """Extract sport from subreddit or text."""
        sport_mapping = {
            "nfl": "american_football",
            "nba": "basketball", 
            "mlb": "baseball",
            "nhl": "icehockey"
        }
        
        if subreddit in sport_mapping:
            return sport_mapping[subreddit]
        
        # Check text for sport mentions
        for sport_key, sport_name in sport_mapping.items():
            if sport_key in text or sport_name in text:
                return sport_name
        
        return "american_football"  # Default
    
    def _extract_teams(self, sport: str, text: str) -> List[str]:
        """Extract team names from text."""
        teams = []
        sport_key = {"american_football": "nfl", "basketball": "nba", 
                    "baseball": "mlb", "icehockey": "nhl"}.get(sport, "nfl")
        
        if sport_key in self.team_patterns:
            for team in self.team_patterns[sport_key]:
                if team in text:
                    teams.append(team.title())
        
        return teams[:2]  # Max 2 teams
    
    def _extract_bet_type(self, text: str) -> str:
        """Extract bet type from text."""
        if "spread" in text or "point" in text:
            return "spread"
        elif "moneyline" in text or "ml" in text:
            return "moneyline"
        elif "over" in text or "under" in text or "total" in text:
            return "over_under"
        elif "prop" in text:
            return "prop"
        else:
            return "moneyline"  # Default
    
    def _calculate_confidence(self, post: RedditPost, text: str) -> float:
        """Calculate confidence score based on post metrics and language."""
        confidence = 0.5  # Base confidence
        
        # Adjust based on post score
        if post.score > 10:
            confidence += 0.2
        elif post.score > 5:
            confidence += 0.1
        
        # Adjust based on comments (engagement)
        if post.num_comments > 20:
            confidence += 0.1
        
        # Adjust based on confident language
        confident_words = ["lock", "sure", "confident", "guarantee", "easy"]
        if any(word in text for word in confident_words):
            confidence += 0.1
        
        # Adjust based on uncertain language
        uncertain_words = ["maybe", "might", "possibly", "unsure"]
        if any(word in text for word in uncertain_words):
            confidence -= 0.1
        
        return min(max(confidence, 0.1), 0.9)  # Clamp between 0.1-0.9
    
    async def crawl_betting_insights(self) -> List[BettingInsight]:
        """Crawl all subreddits for betting insights."""
        all_insights = []
        
        for subreddit in self.subreddits:
            posts = await self.fetch_subreddit_posts(subreddit)
            insights = self.extract_betting_insights(posts)
            all_insights.extend(insights)
            
            # Rate limiting
            await asyncio.sleep(1)
        
        logger.info(f"Extracted {len(all_insights)} betting insights from Reddit")
        return all_insights

# Usage example
async def main():
    crawler = RedditCrawler()
    insights = await crawler.crawl_betting_insights()
    
    for insight in insights[:5]:  # Show first 5
        print(f"Sport: {insight.sport}")
        print(f"Teams: {', '.join(insight.teams)}")
        print(f"Bet Type: {insight.bet_type}")
        print(f"Confidence: {insight.confidence:.2f}")
        print(f"Reasoning: {insight.reasoning}")
        print("---")

if __name__ == "__main__":
    asyncio.run(main())
