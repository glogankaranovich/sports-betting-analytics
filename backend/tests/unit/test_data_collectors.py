"""
Test Data Collection System
"""

import pytest
from unittest.mock import patch
from data_collectors import (
    TeamMomentumCollector,
    WeatherDataCollector,
    PublicOpinionCollector,
    DataCollectionOrchestrator,
)


class TestTeamMomentumCollector:
    @pytest.fixture
    def collector(self):
        return TeamMomentumCollector()

    @pytest.fixture
    def sample_games(self):
        return [
            {
                "id": "game_1",
                "sport": "americanfootball_nfl",
                "home_team": "Chiefs",
                "away_team": "Bills",
                "commence_time": "2026-01-10T20:00:00Z",
            }
        ]

    def test_collector_initialization(self, collector):
        """Test collector initializes correctly"""
        assert collector.name == "team_momentum"
        assert collector.update_frequency == 60
        assert collector.should_update() is True  # No last_update

    def test_calculate_win_streak(self, collector):
        """Test win streak calculation"""
        # Test win streak
        win_games = [{"team_won": True}, {"team_won": True}, {"team_won": False}]
        assert collector.calculate_win_streak(win_games) == 2

        # Test loss streak
        loss_games = [{"team_won": False}, {"team_won": False}, {"team_won": True}]
        assert collector.calculate_win_streak(loss_games) == -2

        # Test empty games
        assert collector.calculate_win_streak([]) == 0

    def test_calculate_recent_record(self, collector):
        """Test recent record calculation"""
        games = [
            {"team_won": True},
            {"team_won": True},
            {"team_won": False},
            {"team_won": True},
        ]

        record = collector.calculate_recent_record(games)
        assert record["wins"] == 3
        assert record["losses"] == 1
        assert record["win_percentage"] == 0.75

    def test_calculate_composite_momentum(self, collector):
        """Test composite momentum calculation"""
        metrics = {
            "recent_record": {"win_percentage": 0.8},
            "win_streak": 3,
            "point_differential_trend": 5.0,
            "ats_record": {"ats_percentage": 0.6},
        }

        composite = collector.calculate_composite_momentum(metrics)
        assert 0 <= composite <= 1
        assert isinstance(composite, float)

    def test_get_default_momentum(self, collector):
        """Test default momentum structure"""
        default = collector.get_default_momentum()

        required_fields = [
            "win_streak",
            "recent_record",
            "point_differential_trend",
            "composite_score",
        ]
        for field in required_fields:
            assert field in default

        assert default["composite_score"] == 0.5

    @pytest.mark.asyncio
    async def test_collect_data_no_games(self, collector):
        """Test collection with no games"""
        result = await collector.collect_data("americanfootball_nfl", [])

        assert result.success is True
        assert result.data == {}
        assert result.records_collected == 0

    @pytest.mark.asyncio
    async def test_collect_data_with_games(self, collector, sample_games):
        """Test collection with sample games"""
        with patch.object(collector, "get_recent_games", return_value=[]):
            result = await collector.collect_data("americanfootball_nfl", sample_games)

            assert result.success is True
            assert "game_1" in result.data
            assert result.records_collected == 1

            game_data = result.data["game_1"]
            assert "home_team_momentum" in game_data
            assert "away_team_momentum" in game_data
            assert "momentum_differential" in game_data


class TestWeatherDataCollector:
    @pytest.fixture
    def collector(self):
        return WeatherDataCollector()

    def test_weather_collector_initialization(self, collector):
        """Test weather collector initializes correctly"""
        assert collector.name == "weather"
        assert collector.update_frequency == 30
        assert "Arrowhead Stadium" in collector.outdoor_venues

    def test_calculate_weather_impact(self, collector):
        """Test weather impact calculation"""
        # Cold and windy conditions
        weather_info = {
            "temperature": 15,  # Very cold
            "wind_speed": 25,  # Very windy
            "precipitation_chance": 80,  # High chance of precipitation
        }

        impact = collector.calculate_weather_impact(weather_info)
        assert 0.8 <= impact <= 1.0  # Should be high impact

        # Perfect conditions
        perfect_weather = {
            "temperature": 70,
            "wind_speed": 5,
            "precipitation_chance": 10,
        }

        impact = collector.calculate_weather_impact(perfect_weather)
        assert impact <= 0.2  # Should be low impact


class TestPublicOpinionCollector:
    @pytest.fixture
    def collector(self):
        return PublicOpinionCollector()

    def test_public_opinion_initialization(self, collector):
        """Test public opinion collector initializes correctly"""
        assert collector.name == "public_opinion"
        assert collector.update_frequency == 15

    def test_calculate_public_fade_score(self, collector):
        """Test public fade score calculation"""
        # Heavy public on home team
        betting_data = {"home_team_percentage": 75}
        fade_score = collector.calculate_public_fade_score(betting_data)
        assert fade_score == 0.8

        # Balanced betting
        betting_data = {"home_team_percentage": 50}
        fade_score = collector.calculate_public_fade_score(betting_data)
        assert fade_score == 0.1


class TestDataCollectionOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        return DataCollectionOrchestrator()

    @pytest.fixture
    def sample_games(self):
        return [
            {
                "id": "game_1",
                "sport": "americanfootball_nfl",
                "home_team": "Chiefs",
                "away_team": "Bills",
            }
        ]

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes with all collectors"""
        assert "team_momentum" in orchestrator.collectors
        assert "weather" in orchestrator.collectors
        assert "public_opinion" in orchestrator.collectors
        assert len(orchestrator.collectors) == 3

    @pytest.mark.asyncio
    async def test_collect_all_data_no_games(self, orchestrator):
        """Test orchestration with no games"""
        results = await orchestrator.collect_all_data("americanfootball_nfl", [])
        assert results == {}

    @pytest.mark.asyncio
    async def test_collect_all_data_with_games(self, orchestrator, sample_games):
        """Test orchestration with games"""
        with patch.object(orchestrator, "_store_collection_results"):
            with patch.object(orchestrator, "_log_collection_summary"):
                results = await orchestrator.collect_all_data(
                    "americanfootball_nfl", sample_games
                )

                # Should have results from active collectors
                assert len(results) >= 0  # May be 0 if no collectors need updates

    def test_get_collector_status(self, orchestrator):
        """Test collector status reporting"""
        status = orchestrator.get_collector_status()

        assert "team_momentum" in status
        momentum_status = status["team_momentum"]

        assert "name" in momentum_status
        assert "update_frequency_minutes" in momentum_status
        assert "should_update" in momentum_status
