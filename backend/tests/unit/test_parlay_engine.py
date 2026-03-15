"""Tests for ParlayEngine and parlay settlement in outcome collector."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from benny.parlay_engine import ParlayEngine


def _make_leg(game_id, player, confidence=0.80, odds=-110, sport="basketball_nba"):
    return {
        "game_id": game_id,
        "sport": sport,
        "player": player,
        "market": "player_points",
        "market_key": "player_points",
        "prediction": f"{player} Over 20.5",
        "confidence": confidence,
        "reasoning": "test",
        "key_factors": [],
        "odds": odds,
        "commence_time": "2026-03-15T00:00:00Z",
    }


class TestParlayEngine:
    def setup_method(self):
        self.engine = ParlayEngine()

    def test_build_2leg_parlay(self):
        opps = [
            _make_leg("g1", "Player A", 0.80),
            _make_leg("g2", "Player B", 0.75),
        ]
        parlays = self.engine.build_parlays(opps)
        assert len(parlays) == 1
        assert parlays[0]["num_legs"] == 2
        assert parlays[0]["bet_type"] == "parlay"

    def test_build_3leg_parlay(self):
        opps = [
            _make_leg("g1", "Player A", 0.85),
            _make_leg("g2", "Player B", 0.80),
            _make_leg("g3", "Player C", 0.75),
        ]
        parlays = self.engine.build_parlays(opps)
        assert len(parlays) == 1
        assert parlays[0]["num_legs"] == 3

    def test_rejects_correlated_same_game(self):
        opps = [
            _make_leg("g1", "Player A", 0.80),
            _make_leg("g1", "Player B", 0.75),
        ]
        parlays = self.engine.build_parlays(opps)
        assert len(parlays) == 0

    def test_rejects_correlated_same_player(self):
        opps = [
            _make_leg("g1", "Player A", 0.80),
            _make_leg("g2", "Player A", 0.75),
        ]
        parlays = self.engine.build_parlays(opps)
        assert len(parlays) == 0

    def test_filters_low_confidence(self):
        opps = [
            _make_leg("g1", "Player A", 0.80),
            _make_leg("g2", "Player B", 0.60),  # Below 0.70 threshold
        ]
        parlays = self.engine.build_parlays(opps)
        assert len(parlays) == 0

    def test_max_parlays_respected(self):
        opps = [_make_leg(f"g{i}", f"Player {i}", 0.80) for i in range(8)]
        parlays = self.engine.build_parlays(opps, max_parlays=2)
        assert len(parlays) <= 2

    def test_combined_odds_multiply(self):
        # -110 American = 1.909 decimal
        opps = [
            _make_leg("g1", "Player A", 0.80, odds=-110),
            _make_leg("g2", "Player B", 0.80, odds=-110),
        ]
        parlays = self.engine.build_parlays(opps)
        # 1.909 * 1.909 ≈ 3.645
        assert 3.5 < parlays[0]["combined_decimal_odds"] < 3.8

    def test_combined_confidence_multiply(self):
        opps = [
            _make_leg("g1", "Player A", 0.80),
            _make_leg("g2", "Player B", 0.75),
        ]
        parlays = self.engine.build_parlays(opps)
        assert parlays[0]["combined_confidence"] == pytest.approx(0.60, abs=0.01)

    def test_bet_size_positive_edge(self):
        parlay = {
            "combined_decimal_odds": 3.65,
            "combined_confidence": 0.60,
        }
        size = self.engine.calculate_parlay_bet_size(parlay, Decimal("100"))
        assert size > 0
        assert size <= Decimal("10")  # Max 10% of bankroll

    def test_bet_size_no_edge(self):
        parlay = {
            "combined_decimal_odds": 3.65,
            "combined_confidence": 0.20,  # No edge
        }
        size = self.engine.calculate_parlay_bet_size(parlay, Decimal("100"))
        assert size == Decimal("0")

    def test_legs_not_reused_across_parlays(self):
        opps = [_make_leg(f"g{i}", f"Player {i}", 0.80) for i in range(6)]
        parlays = self.engine.build_parlays(opps, max_parlays=3)
        all_players = []
        for p in parlays:
            all_players.extend(l["player"] for l in p["legs"])
        # No player should appear in more than one parlay
        assert len(all_players) == len(set(all_players))

    def test_empty_opportunities(self):
        assert self.engine.build_parlays([]) == []

    def test_single_opportunity_no_parlay(self):
        opps = [_make_leg("g1", "Player A", 0.80)]
        assert self.engine.build_parlays(opps) == []
