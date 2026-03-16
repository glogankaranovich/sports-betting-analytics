"""Base interface for Benny betting models"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, List


class BennyModelBase(ABC):
    """Abstract base class for Benny betting models.
    
    Each model implements its own:
    - AI prompts (how to ask for predictions)
    - Bet sizing (Kelly vs flat)
    - Threshold logic (adaptive vs fixed)
    - Post-run learning
    """

    @property
    @abstractmethod
    def pk(self) -> str:
        """DynamoDB partition key for this model's data"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Model version identifier (v1, v2, v3)"""
        pass

    @abstractmethod
    def build_game_prompt(
        self,
        game_data: Dict,
        context: Dict[str, Any],
    ) -> str:
        """Build the AI prompt for game analysis.
        
        Args:
            game_data: Game info (teams, odds, commence_time)
            context: Gathered data (elo, form, injuries, weather, etc.)
        
        Returns:
            Prompt string for the AI model
        """
        pass

    @abstractmethod
    def build_prop_prompt(
        self,
        prop_data: Dict,
        player_stats: Dict,
        player_trends: Dict,
        matchup_data: Dict,
    ) -> str:
        """Build the AI prompt for prop analysis."""
        pass

    @abstractmethod
    def calculate_bet_size(
        self,
        confidence: float,
        odds: float,
        bankroll: Decimal,
    ) -> Decimal:
        """Calculate bet size for an opportunity.
        
        Args:
            confidence: AI's stated confidence (0-1)
            odds: American odds
            bankroll: Current bankroll
        
        Returns:
            Bet size in dollars
        """
        pass

    @abstractmethod
    def get_threshold(self, sport: str, market: str) -> float:
        """Get minimum confidence threshold for a sport/market combo."""
        pass

    @abstractmethod
    def should_bet(
        self,
        confidence: float,
        expected_value: float,
        implied_prob: float,
        sport: str,
        market: str,
    ) -> bool:
        """Determine if an opportunity meets betting criteria.
        
        Args:
            confidence: AI's stated confidence
            expected_value: Calculated EV
            implied_prob: Market's implied probability
            sport: Sport key
            market: Market key (h2h, spread, player_points, etc.)
        
        Returns:
            True if should place bet
        """
        pass

    @abstractmethod
    def post_run(self, results: Dict[str, Any]):
        """Called after each run for learning/tracking.
        
        Args:
            results: Summary of bets placed, outcomes, etc.
        """
        pass

    def get_min_bet(self) -> Decimal:
        """Minimum bet size. Override if needed."""
        return Decimal("5.00")

    def get_max_bet_pct(self) -> float:
        """Maximum bet as percentage of bankroll. Override if needed."""
        return 0.20
