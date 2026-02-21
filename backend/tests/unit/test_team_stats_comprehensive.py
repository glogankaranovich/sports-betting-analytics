"""
Comprehensive tests for team stats collector
"""
import os
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone

os.environ["DYNAMODB_TABLE"] = "test-table"

from team_stats_collector import TeamStatsCollector


class TestTeamStatsCollectorComprehensive(unittest.TestCase):

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_collect_stats_for_sport_success(self, mock_requests, mock_boto3):
        """Test successful stats collection"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock completed games query
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
                }
            ]
        }
        
        # Mock ESPN responses
        mock_scoreboard = Mock()
        mock_scoreboard.status_code = 200
        mock_scoreboard.json.return_value = {
            "events": [
                {
                    "id": "401810482",
                    "competitions": [
                        {
                            "competitors": [
                                {"team": {"displayName": "Lakers"}},
                                {"team": {"displayName": "Warriors"}}
                            ]
                        }
                    ]
                }
            ]
        }
        
        mock_stats = Mock()
        mock_stats.status_code = 200
        mock_stats.json.return_value = {
            "boxscore": {
                "teams": [
                    {
                        "team": {"displayName": "Lakers"},
                        "statistics": [
                            {"name": "fieldGoalsMade", "displayValue": "40"}
                        ]
                    }
                ]
            }
        }
        
        mock_requests.get.side_effect = [mock_scoreboard, mock_stats]
        
        collector = TeamStatsCollector()
        count = collector.collect_stats_for_sport("basketball_nba")
        
        self.assertIsInstance(count, int)

    @patch("team_stats_collector.boto3")
    def test_get_completed_games_filters_recent(self, mock_boto3):
        """Test getting completed games filters by time"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        now = datetime.now(timezone.utc)
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": (now - timedelta(hours=3)).isoformat()
                },
                {
                    "pk": "GAME#game123",  # Duplicate
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": (now - timedelta(hours=3)).isoformat()
                }
            ]
        }
        
        collector = TeamStatsCollector()
        games = collector._get_completed_games("basketball_nba")
        
        # Should deduplicate
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "game123")

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_find_espn_game_id_exact_match(self, mock_requests, mock_boto3):
        """Test finding ESPN game ID with exact team match"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {
                    "id": "401810482",
                    "competitions": [
                        {
                            "competitors": [
                                {"team": {"displayName": "Lakers"}},
                                {"team": {"displayName": "Warriors"}}
                            ]
                        }
                    ]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        
        collector = TeamStatsCollector()
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-02-21T19:00:00Z"
        }
        
        espn_id = collector._find_espn_game_id(game, "basketball_nba")
        self.assertEqual(espn_id, "401810482")

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_find_espn_game_id_no_match(self, mock_requests, mock_boto3):
        """Test finding ESPN game ID with no match"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}
        mock_requests.get.return_value = mock_response
        
        collector = TeamStatsCollector()
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-02-21T19:00:00Z"
        }
        
        espn_id = collector._find_espn_game_id(game, "basketball_nba")
        self.assertIsNone(espn_id)

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_fetch_espn_team_stats_success(self, mock_requests, mock_boto3):
        """Test fetching ESPN team stats"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "boxscore": {
                "teams": [
                    {
                        "team": {"displayName": "Lakers"},
                        "statistics": [
                            {"name": "fieldGoalsMade", "displayValue": "40"},
                            {"name": "fieldGoalsAttempted", "displayValue": "85"}
                        ]
                    },
                    {
                        "team": {"displayName": "Warriors"},
                        "statistics": [
                            {"name": "fieldGoalsMade", "displayValue": "38"},
                            {"name": "fieldGoalsAttempted", "displayValue": "82"}
                        ]
                    }
                ]
            }
        }
        mock_requests.get.return_value = mock_response
        
        collector = TeamStatsCollector()
        stats = collector._fetch_espn_team_stats("401810482", "basketball_nba")
        
        self.assertIsInstance(stats, dict)
        self.assertIn("Lakers", stats)
        self.assertIn("Warriors", stats)

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_fetch_espn_team_stats_api_error(self, mock_requests, mock_boto3):
        """Test handling ESPN API error"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found")
        mock_requests.get.return_value = mock_response
        
        collector = TeamStatsCollector()
        stats = collector._fetch_espn_team_stats("invalid_id", "basketball_nba")
        
        self.assertIsNone(stats)

    @patch("team_stats_collector.boto3")
    def test_store_team_stats_creates_items(self, mock_boto3):
        """Test storing team stats creates DynamoDB items"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        collector = TeamStatsCollector()
        team_stats = {
            "Lakers": {
                "fieldGoalsMade": "40",
                "fieldGoalsAttempted": "85"
            },
            "Warriors": {
                "fieldGoalsMade": "38",
                "fieldGoalsAttempted": "82"
            }
        }
        
        collector._store_team_stats("game123", team_stats, "basketball_nba")
        
        # Should call put_item for each team
        self.assertEqual(mock_table.put_item.call_count, 2)

    @patch("team_stats_collector.boto3")
    def test_collect_stats_unsupported_sport(self, mock_boto3):
        """Test collecting stats for unsupported sport"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        collector = TeamStatsCollector()
        count = collector.collect_stats_for_sport("unsupported_sport")
        
        self.assertEqual(count, 0)

    @patch("team_stats_collector.boto3")
    def test_collect_stats_all_sports(self, mock_boto3):
        """Test collecting stats for all supported sports"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}
        
        collector = TeamStatsCollector()
        
        sports = ["basketball_nba", "americanfootball_nfl", "baseball_mlb", 
                  "icehockey_nhl", "soccer_epl"]
        
        for sport in sports:
            count = collector.collect_stats_for_sport(sport)
            self.assertIsInstance(count, int)


if __name__ == "__main__":
    unittest.main()
