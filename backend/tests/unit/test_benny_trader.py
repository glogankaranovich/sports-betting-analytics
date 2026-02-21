"""
Unit tests for Benny autonomous trader
"""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from benny_trader import BennyTrader


@pytest.fixture
def mock_table():
    with patch("benny_trader.table") as mock:
        yield mock


@pytest.fixture
def mock_bedrock():
    with patch("benny_trader.bedrock") as mock:
        yield mock


@pytest.fixture
def trader(mock_table, mock_bedrock):
    mock_table.get_item.return_value = {
        "Item": {
            "amount": Decimal("100.00"),
            "last_reset": datetime.utcnow().isoformat(),
        }
    }
    return BennyTrader()


class TestBennyTrader:
    def test_initial_bankroll(self, trader):
        """Test initial bankroll is $100"""
        assert trader.bankroll == Decimal("100.00")

    def test_weekly_reset(self, mock_table):
        """Test bankroll resets weekly"""
        last_week = (datetime.utcnow() - timedelta(days=8)).isoformat()
        mock_table.get_item.return_value = {
            "Item": {"amount": Decimal("50.00"), "last_reset": last_week}
        }

        trader = BennyTrader()
        assert trader.bankroll == Decimal("100.00")
        mock_table.put_item.assert_called()

    def test_calculate_bet_size_high_confidence(self, trader):
        """Test bet sizing with high confidence"""
        bet_size = trader.calculate_bet_size(0.85)

        assert bet_size > Decimal("5.00")
        assert bet_size <= trader.bankroll * Decimal("0.20")

    def test_calculate_bet_size_low_confidence(self, trader):
        """Test bet sizing with low confidence"""
        bet_size = trader.calculate_bet_size(0.55)

        assert bet_size >= Decimal("5.00")  # Minimum bet
        assert bet_size < trader.bankroll * Decimal("0.10")

    def test_analyze_games_filters_confidence(self, trader, mock_table, mock_bedrock):
        """Test game analysis filters by confidence"""
        # Mock games with odds
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game1",
                    "active_bet_pk": "GAME#basketball_nba",
                    "commence_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "sport": "basketball_nba",
                    "latest": True,
                    "market_key": "h2h",
                    "bookmaker": "draftkings",
                    "outcomes": [
                        {"name": "Lakers", "price": -110},
                        {"name": "Warriors", "price": -110},
                    ],
                },
                {
                    "pk": "GAME#game1",
                    "active_bet_pk": "GAME#basketball_nba",
                    "commence_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "sport": "basketball_nba",
                    "latest": True,
                    "market_key": "h2h",
                    "bookmaker": "fanduel",
                    "outcomes": [
                        {"name": "Lakers", "price": -110},
                        {"name": "Warriors", "price": -110},
                    ],
                },
            ]
        }

        # Mock the helper methods to avoid actual data fetching
        trader._get_team_stats = MagicMock(return_value={})
        trader._get_team_injuries = MagicMock(return_value=[])
        trader._get_head_to_head = MagicMock(return_value=[])
        trader._get_recent_form = MagicMock(return_value=[])
        
        # Mock AI analysis to return high confidence
        trader._ai_analyze_game = MagicMock(
            return_value={
                "prediction": "Lakers",
                "confidence": 0.75,
                "reasoning": "Test reasoning",
                "key_factors": ["Factor 1", "Factor 2"],
            }
        )

        opportunities = trader.analyze_games()

        # Should have at least one opportunity with confidence >= 0.65
        assert len(opportunities) >= 1
        assert all(opp["confidence"] >= 0.65 for opp in opportunities)

    def test_place_bet_success(self, trader, mock_table, mock_bedrock):
        """Test successful bet placement with AI reasoning"""
        # Mock put_item to succeed
        mock_table.put_item.return_value = {}
        
        # Mock team stats query
        mock_table.query.side_effect = [
            {"Items": []},  # Home team stats
            {"Items": []},  # Away team stats
        ]

        # Mock AI reasoning response
        import json

        mock_response_body = type(
            "obj",
            (object,),
            {
                "read": lambda: json.dumps(
                    {
                        "reasoning": "Strong matchup",
                        "confidence_adjustment": 0.05,
                        "key_factors": ["Home advantage"],
                    }
                )
            },
        )()
        mock_bedrock.invoke_model.return_value = {"body": mock_response_body}

        opportunity = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "prediction": "Lakers",
            "confidence": 0.75,
            "commence_time": "2024-01-15T19:00:00Z",
            "market_key": "h2h",
            "reasoning": "Strong matchup",
            "key_factors": ["Home advantage"],
        }

        result = trader.place_bet(opportunity)

        assert result["success"] is True
        assert "bet_id" in result
        assert result["bet_amount"] > 0
        assert "ai_reasoning" in result
        mock_table.put_item.assert_called()

    def test_place_bet_insufficient_bankroll(self, trader):
        """Test bet fails with insufficient bankroll"""
        trader.bankroll = Decimal("1.00")

        opportunity = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "prediction": "Lakers",
            "confidence": 0.95,
            "commence_time": "2024-01-15T19:00:00Z",
            "market_key": "h2h",
        }

        result = trader.place_bet(opportunity)

        assert result["success"] is False
        assert "Insufficient" in result["reason"]

    def test_run_daily_analysis(self, trader, mock_table, mock_bedrock):
        """Test daily analysis run for games and props"""
        # Mock AI analysis for games
        mock_bedrock.invoke_model.return_value = {
            "body": type(
                "obj",
                (object,),
                {
                    "read": lambda: '{"prediction": "Lakers", "confidence": 0.75, "reasoning": "Good bet", "key_factors": ["factor1"]}'
                },
            )()
        }

        # Mock game query
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game1",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": "2024-01-15T19:00:00Z",
                    "market_key": "h2h",
                    "bookmaker": "draftkings",
                    "outcomes": [
                        {"name": "Lakers", "price": -110},
                        {"name": "Warriors", "price": -110},
                    ],
                }
            ]
        }

        result = trader.run_daily_analysis()

        assert "game_opportunities" in result
        assert "game_bets_placed" in result
        assert "prop_opportunities" in result
        assert "prop_bets_placed" in result
        assert "total_bets" in result
        assert "remaining_bankroll" in result

    def test_analyze_props(self, trader, mock_table, mock_bedrock):
        """Test prop analysis"""
        # Mock prop query
        mock_table.query.return_value = {
            "Items": [
                {
                    "player_name": "LeBron James",
                    "market_key": "player_points",
                    "sport": "basketball_nba",
                    "game_id": "game1",
                    "team": "Lakers",
                    "opponent": "Warriors",
                    "commence_time": "2024-01-15T19:00:00Z",
                    "point": 25.5,
                    "bookmaker": "draftkings",
                    "outcomes": [
                        {"name": "Over", "price": -110, "point": 25.5},
                        {"name": "Under", "price": -110, "point": 25.5},
                    ],
                    "latest": True,
                }
            ]
        }

        # Mock AI prop analysis
        mock_bedrock.invoke_model.return_value = {
            "body": type(
                "obj",
                (object,),
                {
                    "read": lambda: '{"prediction": "Over 25.5", "confidence": 0.72, "reasoning": "Hot streak", "key_factors": ["averaging 28 ppg"]}'
                },
            )()
        }

        opportunities = trader.analyze_props()

        assert isinstance(opportunities, list)
        if opportunities:
            assert "player" in opportunities[0]
            assert "market" in opportunities[0]
            assert "confidence" in opportunities[0]

    def test_get_dashboard_data(self, mock_table):
        """Test dashboard data retrieval with performance metrics"""
        mock_table.get_item.return_value = {
            "Item": {
                "amount": Decimal("85.50"),
                "last_reset": datetime.utcnow().isoformat(),
            }
        }

        mock_table.query.return_value = {
            "Items": [
                {
                    "bet_id": "bet1",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "prediction": "Lakers",
                    "ensemble_confidence": Decimal("0.70"),
                    "final_confidence": Decimal("0.75"),
                    "ai_reasoning": "Strong matchup",
                    "ai_key_factors": ["Home advantage"],
                    "bet_amount": Decimal("10.00"),
                    "status": "won",
                    "payout": Decimal("19.00"),
                    "placed_at": "2024-01-15T12:00:00Z",
                    "sport": "basketball_nba",
                }
            ]
        }

        dashboard = BennyTrader.get_dashboard_data()

        assert dashboard["current_bankroll"] == 85.50
        assert dashboard["weekly_budget"] == 100.0
        assert "win_rate" in dashboard
        assert "roi" in dashboard
        assert "sports_performance" in dashboard
        assert "confidence_accuracy" in dashboard
        assert "bankroll_history" in dashboard
        assert len(dashboard["recent_bets"]) > 0
        assert "ai_reasoning" in dashboard["recent_bets"][0]

    def test_get_elo_rating(self, trader, mock_table):
        """Test fetching Elo ratings"""
        mock_table.query.return_value = {
            "Items": [{"rating": Decimal("1650")}]
        }
        
        rating = trader._get_elo_rating("Lakers", "basketball_nba")
        assert rating == 1650.0

    def test_get_elo_rating_default(self, trader, mock_table):
        """Test Elo defaults to 1500 when no data"""
        mock_table.query.return_value = {"Items": []}
        
        rating = trader._get_elo_rating("NewTeam", "basketball_nba")
        assert rating == 1500.0

    def test_get_adjusted_metrics(self, trader, mock_table):
        """Test fetching opponent-adjusted metrics"""
        mock_table.query.return_value = {
            "Items": [{"metrics": {"adjusted_ppg": 110.5, "vs_league_avg": 1.05}}]
        }
        
        metrics = trader._get_adjusted_metrics("Lakers", "basketball_nba")
        assert metrics["adjusted_ppg"] == 110.5
        assert metrics["vs_league_avg"] == 1.05

    def test_get_weather_data(self, trader, mock_table):
        """Test fetching weather data"""
        mock_table.query.return_value = {
            "Items": [{"temp_f": Decimal("45"), "wind_mph": Decimal("15"), "precip_in": Decimal("0.1"), "impact": "moderate"}]
        }
        
        weather = trader._get_weather_data("game123")
        assert weather["temp_f"] == 45.0
        assert weather["wind_mph"] == 15.0
        assert weather["impact"] == "moderate"

    def test_get_fatigue_data(self, trader, mock_table):
        """Test fetching fatigue data"""
        mock_table.query.return_value = {
            "Items": [{
                "home_fatigue_score": Decimal("25"),
                "home_total_miles": Decimal("500"),
                "home_days_rest": 2,
                "away_fatigue_score": Decimal("65"),
                "away_total_miles": Decimal("2500"),
                "away_days_rest": 1,
            }]
        }
        
        fatigue = trader._get_fatigue_data("game123")
        assert fatigue["home_fatigue"] == 25.0
        assert fatigue["away_fatigue"] == 65.0
        assert fatigue["away_miles"] == 2500.0


    def test_max_bet_size_limit(self, trader):
        """Test maximum bet size is enforced"""
        trader.bankroll = Decimal("1000.00")
        
        bet_size = trader.calculate_bet_size(0.95)
        assert bet_size <= Decimal("200.00")  # 20% max

    def test_min_bet_size(self, trader):
        """Test minimum bet size"""
        bet_size = trader.calculate_bet_size(0.50)
        assert bet_size >= Decimal("5.00")  # Minimum bet
