"""
Unit tests for season_manager module
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

from season_manager import SPORT_SEASONS, is_in_season, lambda_handler


class TestIsInSeason:
    """Test is_in_season function"""

    def test_nba_in_season_october(self):
        # NBA: Oct (10) - Jun (6)
        assert is_in_season("NBA", 10) is True

    def test_nba_in_season_december(self):
        assert is_in_season("NBA", 12) is True

    def test_nba_in_season_february(self):
        assert is_in_season("NBA", 2) is True

    def test_nba_in_season_june(self):
        assert is_in_season("NBA", 6) is True

    def test_nba_out_of_season_july(self):
        assert is_in_season("NBA", 7) is False

    def test_nba_out_of_season_august(self):
        assert is_in_season("NBA", 8) is False

    def test_nfl_in_season_september(self):
        # NFL: Sep (9) - Feb (2)
        assert is_in_season("NFL", 9) is True

    def test_nfl_in_season_january(self):
        assert is_in_season("NFL", 1) is True

    def test_nfl_in_season_february(self):
        assert is_in_season("NFL", 2) is True

    def test_nfl_out_of_season_march(self):
        assert is_in_season("NFL", 3) is False

    def test_nfl_out_of_season_august(self):
        assert is_in_season("NFL", 8) is False

    def test_mlb_in_season_march(self):
        # MLB: Mar (3) - Oct (10)
        assert is_in_season("MLB", 3) is True

    def test_mlb_in_season_july(self):
        assert is_in_season("MLB", 7) is True

    def test_mlb_in_season_october(self):
        assert is_in_season("MLB", 10) is True

    def test_mlb_out_of_season_november(self):
        assert is_in_season("MLB", 11) is False

    def test_mlb_out_of_season_february(self):
        assert is_in_season("MLB", 2) is False

    def test_nhl_in_season_october(self):
        # NHL: Oct (10) - Jun (6)
        assert is_in_season("NHL", 10) is True

    def test_nhl_in_season_march(self):
        assert is_in_season("NHL", 3) is True

    def test_nhl_out_of_season_july(self):
        assert is_in_season("NHL", 7) is False

    def test_epl_in_season_august(self):
        # EPL: Aug (8) - May (5)
        assert is_in_season("EPL", 8) is True

    def test_epl_in_season_december(self):
        assert is_in_season("EPL", 12) is True

    def test_epl_in_season_may(self):
        assert is_in_season("EPL", 5) is True

    def test_epl_out_of_season_june(self):
        assert is_in_season("EPL", 6) is False

    def test_epl_out_of_season_july(self):
        assert is_in_season("EPL", 7) is False

    def test_unknown_sport(self):
        assert is_in_season("UNKNOWN", 1) is False

    def test_all_months_covered(self):
        # Verify logic works for all 12 months
        for month in range(1, 13):
            for sport in SPORT_SEASONS.keys():
                result = is_in_season(sport, month)
                assert isinstance(result, bool)


class TestLambdaHandler:
    """Test lambda_handler function"""

    @patch("season_manager.events_client")
    @patch("season_manager.datetime")
    @patch.dict("os.environ", {"ENVIRONMENT": "dev"})
    def test_lambda_handler_enable_rule(self, mock_datetime, mock_events):
        # Set current month to October (NBA in season)
        mock_datetime.now.return_value = datetime(2026, 10, 1)

        # Mock paginator
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Rules": [
                    {
                        "Name": "Dev-NBA-OddsCollector",
                        "State": "DISABLED",
                    }
                ]
            }
        ]
        mock_events.get_paginator.return_value = mock_paginator

        result = lambda_handler({}, {})

        assert result["statusCode"] == 200
        assert len(result["body"]["updated_rules"]) == 1
        assert result["body"]["updated_rules"][0]["sport"] == "NBA"
        assert result["body"]["updated_rules"][0]["to"] == "ENABLED"
        mock_events.enable_rule.assert_called_once_with(Name="Dev-NBA-OddsCollector")

    @patch("season_manager.events_client")
    @patch("season_manager.datetime")
    @patch.dict("os.environ", {"ENVIRONMENT": "dev"})
    def test_lambda_handler_disable_rule(self, mock_datetime, mock_events):
        # Set current month to July (NBA out of season)
        mock_datetime.now.return_value = datetime(2026, 7, 1)

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Rules": [
                    {
                        "Name": "Dev-NBA-OddsCollector",
                        "State": "ENABLED",
                    }
                ]
            }
        ]
        mock_events.get_paginator.return_value = mock_paginator

        result = lambda_handler({}, {})

        assert result["statusCode"] == 200
        assert len(result["body"]["updated_rules"]) == 1
        assert result["body"]["updated_rules"][0]["to"] == "DISABLED"
        mock_events.disable_rule.assert_called_once_with(Name="Dev-NBA-OddsCollector")

    @patch("season_manager.events_client")
    @patch("season_manager.datetime")
    @patch.dict("os.environ", {"ENVIRONMENT": "dev"})
    def test_lambda_handler_no_changes(self, mock_datetime, mock_events):
        # Set current month to October (NBA in season)
        mock_datetime.now.return_value = datetime(2026, 10, 1)

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Rules": [
                    {
                        "Name": "Dev-NBA-OddsCollector",
                        "State": "ENABLED",  # Already in correct state
                    }
                ]
            }
        ]
        mock_events.get_paginator.return_value = mock_paginator

        result = lambda_handler({}, {})

        assert result["statusCode"] == 200
        assert len(result["body"]["updated_rules"]) == 0
        mock_events.enable_rule.assert_not_called()
        mock_events.disable_rule.assert_not_called()

    @patch("season_manager.events_client")
    @patch("season_manager.datetime")
    @patch.dict("os.environ", {"ENVIRONMENT": "prod"})
    def test_lambda_handler_prod_environment(self, mock_datetime, mock_events):
        mock_datetime.now.return_value = datetime(2026, 10, 1)

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Rules": [
                    {
                        "Name": "Prod-NBA-OddsCollector",
                        "State": "DISABLED",
                    }
                ]
            }
        ]
        mock_events.get_paginator.return_value = mock_paginator

        result = lambda_handler({}, {})

        assert result["statusCode"] == 200
        mock_events.enable_rule.assert_called_once_with(Name="Prod-NBA-OddsCollector")

    @patch("season_manager.events_client")
    @patch("season_manager.datetime")
    @patch.dict("os.environ", {"ENVIRONMENT": "dev"})
    def test_lambda_handler_multiple_sports(self, mock_datetime, mock_events):
        # October: NBA and NHL in season, MLB ending, NFL in season
        mock_datetime.now.return_value = datetime(2026, 10, 1)

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Rules": [
                    {"Name": "Dev-NBA-OddsCollector", "State": "DISABLED"},
                    {"Name": "Dev-NFL-OddsCollector", "State": "DISABLED"},
                    {"Name": "Dev-MLB-OddsCollector", "State": "DISABLED"},
                ]
            }
        ]
        mock_events.get_paginator.return_value = mock_paginator

        result = lambda_handler({}, {})

        assert result["statusCode"] == 200
        assert len(result["body"]["updated_rules"]) == 3
        assert mock_events.enable_rule.call_count == 3

    @patch("season_manager.events_client")
    @patch("season_manager.datetime")
    @patch.dict("os.environ", {"ENVIRONMENT": "dev"})
    def test_lambda_handler_non_sport_rules_ignored(self, mock_datetime, mock_events):
        mock_datetime.now.return_value = datetime(2026, 10, 1)

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Rules": [
                    {"Name": "Dev-SomeOtherRule", "State": "ENABLED"},
                    {"Name": "Dev-NBA-OddsCollector", "State": "DISABLED"},
                ]
            }
        ]
        mock_events.get_paginator.return_value = mock_paginator

        result = lambda_handler({}, {})

        # Only NBA rule should be updated
        assert len(result["body"]["updated_rules"]) == 1
        assert result["body"]["updated_rules"][0]["sport"] == "NBA"
