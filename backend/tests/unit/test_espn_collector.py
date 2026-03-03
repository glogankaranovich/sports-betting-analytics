"""ESPN collector tests"""

from unittest.mock import Mock, patch

import pytest

from espn_collector import ESPNCollector


@pytest.fixture
def collector():
    with patch("espn_collector.boto3"):
        return ESPNCollector()


def test_init(collector):
    """Test init"""
    assert collector.base_url is not None
    assert "basketball_nba" in collector.sport_mappings


def test_collect_news_unsupported_sport(collector):
    """Test unsupported sport"""
    result = collector.collect_news_for_sport("cricket")
    assert result["news_collected"] == 0


def test_sport_mappings(collector):
    """Test sport mappings exist"""
    assert "americanfootball_nfl" in collector.sport_mappings
    assert "baseball_mlb" in collector.sport_mappings
    assert "icehockey_nhl" in collector.sport_mappings


def test_all_sports_supported(collector):
    """Test all 10 sports are supported"""
    expected_sports = [
        "basketball_nba", "basketball_wnba", "basketball_ncaab", "basketball_wncaab",
        "americanfootball_nfl", "americanfootball_ncaaf",
        "baseball_mlb", "icehockey_nhl", "soccer_epl", "soccer_usa_mls"
    ]
    for sport in expected_sports:
        assert sport in collector.sport_mappings


def test_parse_article_high_impact_injury(collector):
    """Test parsing article with injury keyword"""
    article = {
        "headline": "Star Player Out with Injury",
        "description": "Team announces injury to key player",
        "links": {"web": {"href": "http://example.com"}},
        "published": "2026-03-03T10:00:00Z"
    }
    
    result = collector._parse_article(article, "basketball_nba")
    assert result is not None
    assert result["impact"] == "high"
    assert "injury" in result["keywords"]
    assert result["headline"] == "Star Player Out with Injury"


def test_parse_article_high_impact_trade(collector):
    """Test parsing article with trade keyword"""
    article = {
        "headline": "Team Trades Star Player",
        "description": "Major trade announced",
        "links": {"web": {"href": "http://example.com"}},
        "published": "2026-03-03T10:00:00Z"
    }
    
    result = collector._parse_article(article, "basketball_nba")
    assert result["impact"] == "high"
    assert "trade" in result["keywords"]


def test_parse_article_medium_impact(collector):
    """Test parsing article with medium impact keywords"""
    article = {
        "headline": "Player Questionable for Tonight",
        "description": "Starting lineup changes expected",
        "links": {"web": {"href": "http://example.com"}},
        "published": "2026-03-03T10:00:00Z"
    }
    
    result = collector._parse_article(article, "basketball_nba")
    assert result["impact"] == "medium"
    assert "injury" in result["keywords"] or "lineup" in result["keywords"]


def test_parse_article_low_impact(collector):
    """Test parsing article with no special keywords"""
    article = {
        "headline": "Team Prepares for Game",
        "description": "Coach discusses strategy",
        "links": {"web": {"href": "http://example.com"}},
        "published": "2026-03-03T10:00:00Z"
    }
    
    result = collector._parse_article(article, "basketball_nba")
    assert result["impact"] == "low"
    assert len(result["keywords"]) == 0


def test_parse_article_missing_fields(collector):
    """Test parsing article with missing fields"""
    article = {
        "headline": "Test Headline"
        # Missing description, links, published
    }
    
    result = collector._parse_article(article, "basketball_nba")
    assert result is not None
    assert result["headline"] == "Test Headline"
    assert result["description"] == ""
    assert result["url"] == ""


def test_parse_article_error(collector):
    """Test parsing invalid article"""
    result = collector._parse_article(None, "basketball_nba")
    assert result is None


@patch("espn_collector.boto3")
def test_analyze_sentiment_success(mock_boto3, collector):
    """Test sentiment analysis success"""
    mock_comprehend = Mock()
    mock_comprehend.detect_sentiment.return_value = {
        "Sentiment": "POSITIVE",
        "SentimentScore": {
            "Positive": 0.8,
            "Negative": 0.1,
            "Neutral": 0.05,
            "Mixed": 0.05
        }
    }
    collector.comprehend = mock_comprehend
    
    result = collector._analyze_sentiment("Great game today!")
    assert result["sentiment"] == "POSITIVE"
    assert result["positive"] == 0.8


@patch("espn_collector.boto3")
def test_analyze_sentiment_error(mock_boto3, collector):
    """Test sentiment analysis error handling"""
    mock_comprehend = Mock()
    mock_comprehend.detect_sentiment.side_effect = Exception("API Error")
    collector.comprehend = mock_comprehend
    
    result = collector._analyze_sentiment("Test text")
    assert result["sentiment"] == "NEUTRAL"
    assert result["neutral"] == 1.0


@patch("espn_collector.boto3")
def test_get_recent_news(mock_boto3, collector):
    """Test getting recent news"""
    mock_table = Mock()
    mock_table.query.return_value = {
        "Items": [
            {"headline": "News 1", "impact": "high"},
            {"headline": "News 2", "impact": "low"}
        ]
    }
    collector.table = mock_table
    
    result = collector.get_recent_news("basketball_nba", hours=24)
    assert len(result) == 2
    assert mock_table.query.called


@patch("espn_collector.boto3")
def test_get_high_impact_news(mock_boto3, collector):
    """Test getting high impact news only"""
    mock_table = Mock()
    mock_table.query.return_value = {
        "Items": [
            {"headline": "News 1", "impact": "high"},
            {"headline": "News 2", "impact": "low"},
            {"headline": "News 3", "impact": "high"}
        ]
    }
    collector.table = mock_table
    
    result = collector.get_high_impact_news("basketball_nba", hours=24)
    assert len(result) == 2
    assert all(n["impact"] == "high" for n in result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
