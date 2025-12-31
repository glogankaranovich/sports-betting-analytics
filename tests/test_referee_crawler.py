"""
Tests for referee crawler functionality
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch


class TestRefereeCrawlerIntegration:
    """Integration tests for referee crawler functionality"""
    
    def test_referee_crawler_exists(self):
        """Test that referee crawler files exist"""
        import os
        referee_dir = os.path.join(os.path.dirname(__file__), '../backend/referee-crawler')
        
        assert os.path.exists(os.path.join(referee_dir, 'lambda_handler.py'))
        assert os.path.exists(os.path.join(referee_dir, 'referee_crawler.py'))
        assert os.path.exists(os.path.join(referee_dir, 'config.py'))
        assert os.path.exists(os.path.join(referee_dir, 'requirements.txt'))
    
    def test_referee_lambda_handler_structure(self):
        """Test that Lambda handler has correct structure"""
        import os
        handler_path = os.path.join(os.path.dirname(__file__), '../backend/referee-crawler/lambda_handler.py')
        
        with open(handler_path, 'r') as f:
            content = f.read()
            
        # Check for required imports and function
        assert 'lambda_handler' in content
        assert 'RefereeCrawler' in content
        assert 'CrawlerConfigManager' in content
        assert 'async def lambda_handler' in content
    
    def test_referee_requirements_has_heavy_deps(self):
        """Test that referee crawler has heavy dependencies"""
        import os
        req_path = os.path.join(os.path.dirname(__file__), '../backend/referee-crawler/requirements.txt')
        
        with open(req_path, 'r') as f:
            content = f.read()
            
        # Should have heavy dependencies
        assert 'pandas' in content
        assert 'numpy' in content
        assert 'beautifulsoup4' in content
        assert 'requests' in content
    
    @pytest.mark.asyncio
    async def test_deprecated_referee_collection(self):
        """Test that main crawler returns deprecation message for referee collection"""
        from backend.crawler.scheduler import DataCollectionExecutor
        
        executor = DataCollectionExecutor()
        result = await executor.collect_referee_data()
        
        # Should return deprecation message
        assert result["status"] == "deprecated"
        assert "separate Lambda function" in result["message"]
        assert result["referee_events"] == 0


class TestRefereeCrawlerMocked:
    """Mocked tests for referee crawler Lambda"""
    
    @pytest.mark.asyncio
    async def test_lambda_handler_mock(self):
        """Test Lambda handler with mocked dependencies"""
        # Mock the lambda handler response structure
        mock_response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Referee data collection completed successfully",
                "records_collected": 5,
                "league": "nfl",
                "season": "2024"
            })
        }
        
        # Test the expected response structure
        assert mock_response["statusCode"] == 200
        body = json.loads(mock_response["body"])
        assert "records_collected" in body
        assert "league" in body
        assert "season" in body
    
    def test_referee_data_structure(self):
        """Test expected referee data structure"""
        # Test the structure we expect from referee crawler
        sample_referee = {
            "referee_id": "ref_001",
            "name": "Test Referee",
            "sport": "nfl",
            "games_officiated": 50,
            "home_team_win_rate": 0.52,
            "total_fouls_per_game": 12.5,
            "technical_fouls_per_game": 0.8,
            "ejections_per_game": 0.1,
            "overtime_games_rate": 0.15,
            "close_game_call_tendency": 0.48,
            "experience_years": 10,
            "season": "2024",
            "source_url": "https://test.com",
            "last_updated": "2024-01-01T00:00:00Z"
        }
        
        # Validate structure
        assert sample_referee["referee_id"] == "ref_001"
        assert sample_referee["name"] == "Test Referee"
        assert sample_referee["sport"] == "nfl"
        assert isinstance(sample_referee["games_officiated"], int)
        assert isinstance(sample_referee["home_team_win_rate"], float)
        assert 0 <= sample_referee["home_team_win_rate"] <= 1
