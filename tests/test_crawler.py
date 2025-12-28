"""Tests for crawler components."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.crawler.reddit_crawler import RedditCrawler, RedditPost, BettingInsight
from backend.crawler.scheduler import DataCollectionExecutor


class TestRedditCrawler:
    """Test Reddit crawler functionality."""
    
    @pytest.fixture
    def crawler(self):
        return RedditCrawler()
    
    @pytest.fixture
    def sample_post(self):
        return RedditPost(
            id="test123",
            title="Chiefs vs Bills spread pick",
            content="Taking Chiefs -3.5, they look strong",
            author="testuser",
            score=15,
            num_comments=8,
            created_utc=1640995200.0,
            subreddit="sportsbook",
            url="https://reddit.com/r/sportsbook/test123"
        )
    
    def test_is_betting_related(self, crawler):
        """Test betting content detection."""
        assert crawler._is_betting_related("Chiefs spread pick", "Taking -3.5")
        assert crawler._is_betting_related("NBA over/under", "Total points 220")
        assert not crawler._is_betting_related("Game highlights", "Amazing touchdown")
    
    def test_extract_sport(self, crawler):
        """Test sport extraction."""
        assert crawler._extract_sport("nfl", "chiefs bills") == "american_football"
        assert crawler._extract_sport("nba", "lakers warriors") == "basketball"
        assert crawler._extract_sport("sportsbook", "nfl game") == "american_football"
    
    def test_extract_teams(self, crawler):
        """Test team extraction."""
        teams = crawler._extract_teams("american_football", "chiefs vs bills game")
        assert "Chiefs" in teams
        assert "Bills" in teams
    
    def test_extract_bet_type(self, crawler):
        """Test bet type extraction."""
        assert crawler._extract_bet_type("spread -3.5") == "spread"
        assert crawler._extract_bet_type("moneyline pick") == "moneyline"
        assert crawler._extract_bet_type("over 45.5 total") == "over_under"
        assert crawler._extract_bet_type("prop bet") == "prop"
    
    def test_calculate_confidence(self, crawler, sample_post):
        """Test confidence scoring."""
        confidence = crawler._calculate_confidence(sample_post, "this is a lock bet")
        assert 0.1 <= confidence <= 0.9
        assert confidence > 0.5  # Should be higher due to "lock" keyword
    
    def test_extract_betting_insights(self, crawler, sample_post):
        """Test insight extraction."""
        insights = crawler.extract_betting_insights([sample_post])
        
        assert len(insights) == 1
        insight = insights[0]
        assert insight.post_id == "test123"
        assert insight.sport == "american_football"
        assert len(insight.teams) >= 1
        assert insight.bet_type in ["spread", "moneyline", "over_under", "prop"]
        assert 0.1 <= insight.confidence <= 0.9


class TestDataCollectionExecutor:
    """Test data collection execution logic."""
    
    @pytest.fixture
    def executor(self):
        with patch('backend.crawler.scheduler.SportsCrawlerService'), \
             patch('backend.crawler.scheduler.create_data_processor'), \
             patch('backend.crawler.scheduler.RedditCrawler'):
            return DataCollectionExecutor()
    
    @pytest.mark.asyncio
    async def test_timeout_protection(self, executor):
        """Test Lambda timeout protection."""
        # Mock slow crawler service
        executor.crawler_service.collect_sports_data = AsyncMock()
        executor.crawler_service.collect_sports_data.side_effect = asyncio.TimeoutError()
        
        result = await executor.collect_sports(["nfl"])
        
        assert result["success"] is False
        assert "timed out" in result["error"]
        assert "timeout_limit_seconds" not in result  # Only in timeout summary
    
    @pytest.mark.asyncio
    async def test_successful_collection(self, executor):
        """Test successful data collection."""
        # Mock successful collection
        mock_events = [{"id": "test1", "sport": "nfl"}]
        executor.crawler_service.collect_sports_data = AsyncMock(return_value={"nfl": mock_events})
        
        mock_stats = Mock()
        mock_stats.stored_events = 1
        executor.data_processor.process_and_store = AsyncMock(return_value=mock_stats)
        executor.data_processor.get_processing_summary = Mock(return_value={"stored": 1})
        
        result = await executor.collect_sports(["nfl"])
        
        assert result["success"] is True
        assert result["total_events_stored"] == 1
        assert result["sports_processed"] == 1
        assert "execution_time_seconds" in result
    
    @pytest.mark.asyncio
    async def test_reddit_collection(self, executor):
        """Test Reddit insights collection."""
        # Mock Reddit crawler
        mock_insights = [
            Mock(
                post_id="test1",
                sport="american_football", 
                teams=["Chiefs"],
                bet_type="spread",
                confidence=0.7,
                reasoning="Good pick",
                source_url="https://reddit.com/test1",
                created_at=datetime.now()
            )
        ]
        executor.reddit_crawler.crawl_betting_insights = AsyncMock(return_value=mock_insights)
        
        mock_stats = Mock()
        mock_stats.stored_events = 1
        executor.data_processor.process_and_store = AsyncMock(return_value=mock_stats)
        
        result = await executor.collect_reddit_insights()
        
        assert result["success"] is True
        assert result["insights_collected"] == 1
        assert result["insights_stored"] == 1


@pytest.mark.asyncio
async def test_lambda_handler():
    """Test Lambda handler routing."""
    from backend.crawler.scheduler import lambda_handler
    
    with patch('backend.crawler.scheduler.DataCollectionExecutor') as mock_executor_class:
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        
        # Test sports collection
        mock_executor.collect_all_sports = AsyncMock(return_value={"success": True})
        
        context = Mock()
        context.aws_request_id = "test-request-123"
        
        result = await lambda_handler({"collection_type": "sports"}, context)
        
        assert result["success"] is True
        assert result["lambda_request_id"] == "test-request-123"
        assert result["collection_type"] == "sports"
        
        # Test Reddit collection
        mock_executor.collect_reddit_insights = AsyncMock(return_value={"success": True})
        
        result = await lambda_handler({"collection_type": "reddit"}, context)
        
        assert result["success"] is True
        assert result["collection_type"] == "reddit"
        
        # Test unknown collection type
        result = await lambda_handler({"collection_type": "unknown"}, context)
        
        assert result["success"] is False
        assert "Unknown collection type" in result["error"]
