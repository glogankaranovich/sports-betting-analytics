"""
ML Models for Sports Betting Analytics
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import math
from datetime import datetime


@dataclass
class GameAnalysis:
    game_id: str
    sport: str
    home_win_probability: float
    away_win_probability: float
    confidence_score: float
    value_bets: List[str]


@dataclass
class PropAnalysis:
    game_id: str
    sport: str
    player_name: str
    prop_type: str
    line: float
    over_probability: float
    under_probability: float
    confidence_score: float
    value_bets: List[str]


@dataclass
class AnalysisResult:
    """Standardized analysis result for DynamoDB storage"""

    game_id: str
    model: str
    analysis_type: str  # "game" or "prop"
    sport: str
    prediction: str
    confidence: float
    reasoning: str
    home_team: str = None
    away_team: str = None
    commence_time: str = None
    player_name: str = None
    bookmaker: str = None
    market_key: str = None  # For props: player_points, player_assists, etc.

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format with GSI attributes"""
        # For props, include player_name in PK to avoid collisions with game analyses
        if self.analysis_type == "prop" and self.player_name:
            pk = f"ANALYSIS#{self.sport}#{self.game_id}#{self.player_name}#{self.bookmaker}"
            analysis_pk = f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#prop"
            analysis_time_pk = (
                f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#prop"
            )
        else:
            pk = f"ANALYSIS#{self.sport}#{self.game_id}#{self.bookmaker}"
            analysis_pk = f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#game"
            analysis_time_pk = (
                f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#game"
            )

        return {
            "pk": pk,
            "sk": f"{self.model}#{self.analysis_type}#LATEST",
            "analysis_pk": analysis_pk,  # AnalysisGSI partition key
            "analysis_time_pk": analysis_time_pk,  # AnalysisTimeGSI partition key
            "commence_time": self.commence_time,  # Sort key for AnalysisTimeGSI
            "model_type": f"{self.model}#{self.analysis_type}",  # Sort key for AnalysisGSI
            "analysis_type": self.analysis_type,
            "model": self.model,
            "game_id": self.game_id,
            "sport": self.sport,
            "bookmaker": self.bookmaker,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "player_name": self.player_name,
            "market_key": self.market_key,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "created_at": datetime.utcnow().isoformat(),
            "latest": True,
        }


class BaseAnalysisModel:
    """Base class for all analysis models"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """Analyze game odds and return analysis result"""
        raise NotImplementedError("Subclasses must implement analyze_game_odds")

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds and return analysis result"""
        raise NotImplementedError("Subclasses must implement analyze_prop_odds")

    def american_to_decimal(self, american_odds: int) -> float:
        """Convert American odds to decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)


class ConsensusModel(BaseAnalysisModel):
    """Consensus model: Average across all bookmakers"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        spreads = []
        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    spreads.append(float(item["outcomes"][0].get("point", 0)))

        if not spreads:
            return None

        avg_spread = sum(spreads) / len(spreads)
        confidence = min(0.95, 0.6 + (len(spreads) * 0.05))

        return AnalysisResult(
            game_id=game_id,
            model="consensus",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=f"{game_info.get('home_team')} {avg_spread:+.1f}",
            confidence=confidence,
            reasoning=f"Consensus across {len(spreads)} bookmakers: {avg_spread:+.1f}",
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds using consensus approach"""
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            # Convert American odds to probabilities
            over_decimal = self.american_to_decimal(int(over_outcome["price"]))
            under_decimal = self.american_to_decimal(int(under_outcome["price"]))

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            # Remove vig and normalize
            total_prob = over_prob + under_prob
            over_prob_fair = over_prob / total_prob
            under_prob_fair = under_prob / total_prob

            # Determine prediction based on higher probability
            if over_prob_fair > under_prob_fair:
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = over_prob_fair
            else:
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = under_prob_fair

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                bookmaker="consensus",  # Will be overridden per bookmaker
                model="consensus",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                market_key=prop_item.get("market_key"),
                prediction=prediction,
                confidence=confidence,
                reasoning=f"Consensus across {len(prop_item.get('bookmakers', []))} bookmakers: {prediction}",
            )

        except Exception as e:
            print(f"Error analyzing prop odds: {e}")
            return None


class ValueModel(BaseAnalysisModel):
    """Value model: Find best odds discrepancies"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        spreads = []
        current_bookmaker = game_info.get("bookmaker")

        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    spread = float(item["outcomes"][0].get("point", 0))
                    price = float(item["outcomes"][0].get("price", 0))
                    spreads.append((spread, price))

        if not spreads:
            return None

        # For value model, just use the first spread since we're analyzing per-bookmaker
        selected_spread = spreads[0]
        avg_spread = sum(s[0] for s in spreads) / len(spreads)
        confidence = 0.7 if abs(selected_spread[0] - avg_spread) > 1.0 else 0.5

        return AnalysisResult(
            game_id=game_id,
            model="value",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=f"{game_info.get('home_team')} {selected_spread[0]:+.1f} @ {current_bookmaker}",
            confidence=confidence,
            reasoning=f"Value bet: {selected_spread[0]:+.1f} vs consensus {avg_spread:+.1f}",
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds looking for value opportunities"""
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            # Convert American odds to probabilities
            over_decimal = self.american_to_decimal(int(over_outcome["price"]))
            under_decimal = self.american_to_decimal(int(under_outcome["price"]))

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            # Look for value - if one side has significantly better odds
            total_prob = over_prob + under_prob
            vig = total_prob - 1.0

            # Remove vig to get fair probabilities
            over_prob_fair = over_prob / total_prob
            under_prob_fair = under_prob / total_prob

            # Value model looks for low vig situations (better value for bettors)
            if vig < 0.06:  # Low vig (< 6%) = good value
                confidence = 0.75
                if over_prob_fair > under_prob_fair:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Low vig value: {vig:.1%} vig, Over {over_prob_fair:.1%}"
                    )
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Low vig value: {vig:.1%} vig, Under {under_prob_fair:.1%}"
                    )
            elif vig < 0.08:  # Moderate vig (6-8%) = decent value
                confidence = 0.65
                if over_prob_fair > 0.52:  # Slight edge
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Moderate value: {vig:.1%} vig, Over {over_prob_fair:.1%}"
                    )
                elif under_prob_fair > 0.52:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Moderate value: {vig:.1%} vig, Under {under_prob_fair:.1%}"
                    )
                else:
                    return None  # Too close to call
            else:
                # High vig - only recommend if there's a clear edge
                if over_prob_fair > 0.55:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    confidence = 0.6
                    reasoning = f"High vig but strong edge: Over {over_prob_fair:.1%}"
                elif under_prob_fair > 0.55:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    confidence = 0.6
                    reasoning = f"High vig but strong edge: Under {under_prob_fair:.1%}"
                else:
                    return None  # No value in high vig situation

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                model="value",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                market_key=prop_item.get("market_key"),
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
            )

        except Exception as e:
            print(f"Error analyzing prop odds: {e}")
            return None


class MomentumModel(BaseAnalysisModel):
    """Momentum model: Based on recent odds movement"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        # Filter for spread items and sort by timestamp
        spread_items = [
            item
            for item in odds_items
            if "spreads" in item.get("sk", "") and "outcomes" in item
        ]

        if len(spread_items) < 2:
            return None  # Need at least 2 data points for momentum

        # Sort by updated_at timestamp
        spread_items.sort(key=lambda x: x.get("updated_at", ""))

        # Get oldest and newest spreads
        oldest = spread_items[0]
        newest = spread_items[-1]

        if len(oldest.get("outcomes", [])) < 2 or len(newest.get("outcomes", [])) < 2:
            return None

        old_spread = float(oldest["outcomes"][0].get("point", 0))
        new_spread = float(newest["outcomes"][0].get("point", 0))

        # Calculate movement
        movement = new_spread - old_spread

        # Higher confidence if significant movement
        if abs(movement) > 1.0:
            confidence = 0.8
            reasoning = f"Strong line movement: {old_spread:+.1f} → {new_spread:+.1f} ({movement:+.1f})"
        elif abs(movement) > 0.5:
            confidence = 0.7
            reasoning = f"Moderate line movement: {old_spread:+.1f} → {new_spread:+.1f} ({movement:+.1f})"
        else:
            confidence = 0.6
            reasoning = f"Slight line movement: {old_spread:+.1f} → {new_spread:+.1f} ({movement:+.1f})"

        return AnalysisResult(
            game_id=game_id,
            model="momentum",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=f"{game_info.get('home_team')} {new_spread:+.1f}",
            confidence=confidence,
            reasoning=reasoning,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds based on line movement - requires historical data"""
        # Note: This is a simplified version since we're analyzing a single prop_item
        # In a real implementation with historical data, we'd query multiple timestamps
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            over_price = int(over_outcome["price"])
            under_price = int(under_outcome["price"])

            # Convert to probabilities
            over_decimal = self.american_to_decimal(over_price)
            under_decimal = self.american_to_decimal(under_price)

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            # Detect sharp money based on odds imbalance
            # If one side has significantly worse odds, sharp money is on the other side
            if over_price <= -120:  # Over is heavily favored
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = 0.75
                reasoning = (
                    f"Sharp action on Over: {over_price} indicates heavy betting"
                )
            elif under_price <= -120:  # Under is heavily favored
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = 0.75
                reasoning = (
                    f"Sharp action on Under: {under_price} indicates heavy betting"
                )
            elif over_prob > under_prob * 1.1:  # Over has 10%+ edge
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = 0.7
                reasoning = f"Momentum favors Over: {over_price} vs {under_price}"
            elif under_prob > over_prob * 1.1:  # Under has 10%+ edge
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = 0.7
                reasoning = f"Momentum favors Under: {under_price} vs {over_price}"
            else:
                return None  # No clear momentum signal

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                model="momentum",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                market_key=prop_item.get("market_key"),
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
            )

        except Exception as e:
            print(f"Error analyzing prop odds: {e}")
            return None


class ContrarianModel(BaseAnalysisModel):
    """Contrarian model: Fade the public, follow sharp action"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """
        Contrarian approach:
        1. Look for reverse line movement (line moves against public betting)
        2. Identify odds imbalances that suggest sharp action
        3. Fade heavy public favorites
        """
        spread_items = []

        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    spread_items.append(item)

        if not spread_items:
            return None

        # Sort by timestamp to track movement
        spread_items.sort(key=lambda x: x.get("updated_at", ""))

        if len(spread_items) < 2:
            # Not enough data for movement analysis, use odds imbalance
            return self._analyze_odds_imbalance(game_id, spread_items[0], game_info)

        # Analyze line movement for reverse line movement
        oldest = spread_items[0]
        newest = spread_items[-1]

        if len(oldest.get("outcomes", [])) < 2 or len(newest.get("outcomes", [])) < 2:
            return None

        old_spread = float(oldest["outcomes"][0].get("point", 0))
        new_spread = float(newest["outcomes"][0].get("point", 0))
        movement = new_spread - old_spread

        # Contrarian signal: significant line movement suggests sharp action
        if abs(movement) > 1.0:
            # Strong movement = sharp money
            confidence = 0.75
            # Bet with the line movement (sharp side)
            if movement > 0:
                prediction = f"{game_info.get('away_team')} {-new_spread:+.1f}"
                reasoning = f"Sharp action detected: Line moved {movement:+.1f} points. Fading public, following sharps."
            else:
                prediction = f"{game_info.get('home_team')} {new_spread:+.1f}"
                reasoning = f"Sharp action detected: Line moved {movement:+.1f} points. Fading public, following sharps."
        elif abs(movement) > 0.5:
            confidence = 0.65
            if movement > 0:
                prediction = f"{game_info.get('away_team')} {-new_spread:+.1f}"
                reasoning = f"Moderate sharp action: Line moved {movement:+.1f} points."
            else:
                prediction = f"{game_info.get('home_team')} {new_spread:+.1f}"
                reasoning = f"Moderate sharp action: Line moved {movement:+.1f} points."
        else:
            # No significant movement, use odds imbalance
            return self._analyze_odds_imbalance(game_id, newest, game_info)

        return AnalysisResult(
            game_id=game_id,
            model="contrarian",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _analyze_odds_imbalance(
        self, game_id: str, spread_item: Dict, game_info: Dict
    ) -> AnalysisResult:
        """
        Analyze odds imbalance to detect sharp action
        When one side has worse odds than expected, it suggests sharp money
        """
        outcomes = spread_item.get("outcomes", [])
        if len(outcomes) < 2:
            return None

        home_outcome = outcomes[0]
        away_outcome = outcomes[1]

        home_price = float(home_outcome.get("price", -110))
        away_price = float(away_outcome.get("price", -110))
        home_spread = float(home_outcome.get("point", 0))

        # Calculate vig imbalance
        # Standard is -110/-110, imbalance suggests one-sided action
        price_diff = abs(home_price - away_price)

        if price_diff > 15:
            # Significant imbalance - bet the worse price (sharp side)
            confidence = 0.70
            if home_price < away_price:
                # Home has worse price = sharp money on home
                prediction = f"{game_info.get('home_team')} {home_spread:+.1f}"
                reasoning = f"Odds imbalance detected ({home_price}/{away_price}). Sharp money on home team."
            else:
                # Away has worse price = sharp money on away
                prediction = f"{game_info.get('away_team')} {-home_spread:+.1f}"
                reasoning = f"Odds imbalance detected ({home_price}/{away_price}). Sharp money on away team."
        elif price_diff > 10:
            confidence = 0.60
            if home_price < away_price:
                prediction = f"{game_info.get('home_team')} {home_spread:+.1f}"
                reasoning = f"Moderate odds imbalance ({home_price}/{away_price}). Slight sharp lean on home."
            else:
                prediction = f"{game_info.get('away_team')} {-home_spread:+.1f}"
                reasoning = f"Moderate odds imbalance ({home_price}/{away_price}). Slight sharp lean on away."
        else:
            # No clear signal, fade the favorite
            confidence = 0.55
            if home_spread < 0:
                # Home is favorite, fade them
                prediction = f"{game_info.get('away_team')} {-home_spread:+.1f}"
                reasoning = f"No clear sharp action. Fading favorite {game_info.get('home_team')}."
            else:
                # Away is favorite, fade them
                prediction = f"{game_info.get('home_team')} {home_spread:+.1f}"
                reasoning = f"No clear sharp action. Fading favorite {game_info.get('away_team')}."

        return AnalysisResult(
            game_id=game_id,
            model="contrarian",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds using contrarian approach"""
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            over_price = float(over_outcome.get("price", -110))
            under_price = float(under_outcome.get("price", -110))

            # Analyze odds imbalance
            price_diff = abs(over_price - under_price)

            if price_diff > 15:
                # Significant imbalance - bet the worse price (sharp side)
                confidence = 0.70
                if over_price < under_price:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = f"Sharp action on Over. Odds imbalance: {over_price}/{under_price}"
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = f"Sharp action on Under. Odds imbalance: {over_price}/{under_price}"
            elif price_diff > 10:
                confidence = 0.60
                if over_price < under_price:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Moderate sharp lean on Over: {over_price}/{under_price}"
                    )
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Moderate sharp lean on Under: {over_price}/{under_price}"
                    )
            else:
                # No clear signal, fade the public (assume public likes overs)
                confidence = 0.55
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                reasoning = "No clear sharp action. Fading public (typically on overs)."

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                bookmaker="contrarian",
                model="contrarian",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                market_key=prop_item.get("market_key"),
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
            )

        except Exception as e:
            print(f"Error analyzing contrarian prop odds: {e}")
            return None


class HotColdModel(BaseAnalysisModel):
    """Hot/Cold model: Track recent form and momentum"""

    def __init__(self, dynamodb_table=None):
        """Initialize with optional DynamoDB table for querying recent games"""
        self.table = dynamodb_table
        if not self.table:
            import boto3
            import os

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """
        Analyze based on recent team performance
        - Query last 5-10 games for each team
        - Calculate win/loss streaks
        - Weight recent games more heavily
        """
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        sport = game_info.get("sport")

        # Get recent performance for both teams
        home_record = self._get_recent_record(home_team, sport, lookback=10)
        away_record = self._get_recent_record(away_team, sport, lookback=10)

        # Calculate form scores (0-1)
        home_form = self._calculate_form_score(home_record)
        away_form = self._calculate_form_score(away_record)

        # Determine prediction based on form differential
        form_diff = home_form - away_form

        # Get spread for context
        spread = self._get_current_spread(odds_items)

        if abs(form_diff) > 0.3:
            # Strong form differential
            confidence = 0.75
            if form_diff > 0:
                prediction = f"{home_team} {spread:+.1f}"
                reasoning = f"Strong home form: {home_record['wins']}-{home_record['losses']} last {home_record['games']} games. Away: {away_record['wins']}-{away_record['losses']}."
            else:
                prediction = f"{away_team} {-spread:+.1f}"
                reasoning = f"Strong away form: {away_record['wins']}-{away_record['losses']} last {away_record['games']} games. Home: {home_record['wins']}-{home_record['losses']}."
        elif abs(form_diff) > 0.15:
            # Moderate form differential
            confidence = 0.65
            if form_diff > 0:
                prediction = f"{home_team} {spread:+.1f}"
                reasoning = f"Home team trending up ({home_record['wins']}-{home_record['losses']}), away trending down ({away_record['wins']}-{away_record['losses']})."
            else:
                prediction = f"{away_team} {-spread:+.1f}"
                reasoning = f"Away team trending up ({away_record['wins']}-{away_record['losses']}), home trending down ({home_record['wins']}-{home_record['losses']})."
        else:
            # Similar form, slight edge to home
            confidence = 0.55
            prediction = f"{home_team} {spread:+.1f}"
            reasoning = f"Similar recent form. Home: {home_record['wins']}-{home_record['losses']}, Away: {away_record['wins']}-{away_record['losses']}. Slight home edge."

        return AnalysisResult(
            game_id=game_id,
            model="hot_cold",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _get_recent_record(
        self, team: str, sport: str, lookback: int = 10
    ) -> Dict[str, int]:
        """
        Query recent games for a team
        Returns wins, losses, and total games
        """
        try:
            # Query for recent games where this team played
            response = self.table.query(
                IndexName="AnalysisTimeGSI",
                KeyConditionExpression="analysis_time_pk = :pk",
                FilterExpression="(home_team = :team OR away_team = :team) AND attribute_exists(analysis_correct)",
                ExpressionAttributeValues={
                    ":pk": f"ANALYSIS#{sport}#all#all#game",
                    ":team": team,
                },
                Limit=lookback,
                ScanIndexForward=False,  # Most recent first
            )

            items = response.get("Items", [])

            if not items:
                # No data available, return neutral record
                return {"wins": 5, "losses": 5, "games": 10}

            wins = 0
            losses = 0

            for item in items:
                home_team = item.get("home_team")
                prediction = item.get("prediction", "")
                correct = item.get("analysis_correct", False)

                # Determine if this team won
                if home_team == team:
                    # Team was home
                    team_won = correct if team in prediction else not correct
                else:
                    # Team was away
                    team_won = correct if team in prediction else not correct

                if team_won:
                    wins += 1
                else:
                    losses += 1

            return {"wins": wins, "losses": losses, "games": wins + losses}

        except Exception as e:
            print(f"Error querying recent record: {e}")
            # Return neutral record on error
            return {"wins": 5, "losses": 5, "games": 10}

    def _calculate_form_score(self, record: Dict[str, int]) -> float:
        """
        Calculate form score (0-1) based on recent record
        Weight recent games more heavily
        """
        games = record["games"]
        if games == 0:
            return 0.5  # Neutral

        win_pct = record["wins"] / games

        # Boost for winning streaks
        if record["wins"] >= games * 0.7:
            # Hot team (70%+ wins)
            return min(win_pct * 1.2, 1.0)
        elif record["losses"] >= games * 0.7:
            # Cold team (70%+ losses)
            return max(win_pct * 0.8, 0.0)
        else:
            return win_pct

    def _get_current_spread(self, odds_items: List[Dict]) -> float:
        """Get current spread from odds items"""
        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    return float(item["outcomes"][0].get("point", 0))
        return 0.0

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """
        Analyze prop based on player's recent performance
        Queries last 5-10 games for player stats
        """
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            player_name = prop_item.get("player_name", "Unknown Player")
            sport = prop_item.get("sport")
            market_key = prop_item.get("market_key", "")
            line = prop_item.get("point", 0)

            # Get recent player performance
            recent_stats = self._get_recent_player_stats(player_name, sport, market_key)

            if not recent_stats or recent_stats["games"] == 0:
                # No data available, return neutral prediction
                return AnalysisResult(
                    game_id=prop_item.get("event_id", "unknown"),
                    bookmaker="hot_cold",
                    model="hot_cold",
                    analysis_type="prop",
                    sport=sport,
                    home_team=prop_item.get("home_team"),
                    away_team=prop_item.get("away_team"),
                    commence_time=prop_item.get("commence_time"),
                    player_name=player_name,
                    market_key=market_key,
                    prediction=f"Over {line}",
                    confidence=0.55,
                    reasoning=f"Insufficient data for {player_name}. Neutral prediction.",
                )

            # Calculate if player is hot or cold
            avg_stat = recent_stats["average"]
            over_rate = recent_stats["over_count"] / recent_stats["games"]

            # Determine prediction based on recent performance
            if avg_stat > line * 1.1 and over_rate > 0.7:
                # Hot player, well above line
                confidence = 0.75
                prediction = f"Over {line}"
                reasoning = f"{player_name} averaging {avg_stat:.1f} over last {recent_stats['games']} games. Hit over {int(over_rate*100)}% of time."
            elif avg_stat > line and over_rate > 0.6:
                # Trending over
                confidence = 0.65
                prediction = f"Over {line}"
                reasoning = f"{player_name} trending up: {avg_stat:.1f} avg, {int(over_rate*100)}% over rate last {recent_stats['games']} games."
            elif avg_stat < line * 0.9 and over_rate < 0.3:
                # Cold player, well below line
                confidence = 0.75
                prediction = f"Under {line}"
                reasoning = f"{player_name} averaging {avg_stat:.1f} over last {recent_stats['games']} games. Hit under {int((1-over_rate)*100)}% of time."
            elif avg_stat < line and over_rate < 0.4:
                # Trending under
                confidence = 0.65
                prediction = f"Under {line}"
                reasoning = f"{player_name} trending down: {avg_stat:.1f} avg, {int((1-over_rate)*100)}% under rate last {recent_stats['games']} games."
            else:
                # Close to line, slight edge based on recent trend
                confidence = 0.55
                if avg_stat > line:
                    prediction = f"Over {line}"
                    reasoning = f"{player_name} slightly above line: {avg_stat:.1f} avg over last {recent_stats['games']} games."
                else:
                    prediction = f"Under {line}"
                    reasoning = f"{player_name} slightly below line: {avg_stat:.1f} avg over last {recent_stats['games']} games."

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                bookmaker="hot_cold",
                model="hot_cold",
                analysis_type="prop",
                sport=sport,
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=player_name,
                market_key=market_key,
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
            )

        except Exception as e:
            print(f"Error analyzing hot/cold prop odds: {e}")
            return None

    def _get_recent_player_stats(
        self, player_name: str, sport: str, market_key: str, lookback: int = 10
    ) -> Dict[str, Any]:
        """
        Query recent player stats
        Returns average, games played, and over/under count
        Weights recent games by minutes played for importance
        """
        try:
            # Normalize player name to match storage format
            normalized_name = player_name.lower().replace(" ", "_")
            pk = f"PLAYER_STATS#{sport}#{normalized_name}"

            # Query recent stats
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                Limit=lookback,
                ScanIndexForward=False,  # Most recent first
            )

            items = response.get("Items", [])

            if not items:
                return {"games": 0, "average": 0, "over_count": 0}

            # Extract stat based on market_key
            stat_field = self._map_market_to_stat(market_key)
            weighted_sum = 0.0
            total_weight = 0.0
            games_count = 0

            for item in items:
                stats = item.get("stats", {})
                if stat_field in stats:
                    try:
                        value = float(stats[stat_field])
                        minutes = float(stats.get("MIN", 20))  # Default 20 if missing

                        # Weight by minutes played (more minutes = more reliable)
                        # 30+ minutes = full weight, <10 minutes = 0.3 weight
                        weight = min(minutes / 30.0, 1.0) if minutes > 0 else 0.3

                        weighted_sum += value * weight
                        total_weight += weight
                        games_count += 1
                    except (ValueError, TypeError):
                        continue

            if games_count == 0 or total_weight == 0:
                return {"games": 0, "average": 0, "over_count": 0}

            weighted_avg = weighted_sum / total_weight

            return {"games": games_count, "average": weighted_avg, "over_count": 0}

        except Exception as e:
            print(f"Error querying player stats: {e}")
            return {"games": 0, "average": 0, "over_count": 0}

    def _map_market_to_stat(self, market_key: str) -> str:
        """Map prop market key to player stat field"""
        mapping = {
            "player_points": "PTS",
            "player_rebounds": "REB",
            "player_assists": "AST",
            "player_threes": "3PM",
            "player_blocks": "BLK",
            "player_steals": "STL",
            "player_turnovers": "TO",
            "player_points_rebounds_assists": "PTS+REB+AST",
        }
        return mapping.get(market_key, "PTS")


class RestScheduleModel(BaseAnalysisModel):
    """Model that analyzes rest days, back-to-back games, and home/away splits"""

    def __init__(self, dynamodb_table=None):
        """Initialize with optional DynamoDB table"""
        self.table = dynamodb_table
        if not self.table:
            import boto3
            import os

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """Analyze game based on rest and schedule factors"""
        sport = game_info.get("sport")
        home_team = game_info.get("home_team", "").lower().replace(" ", "_")
        away_team = game_info.get("away_team", "").lower().replace(" ", "_")
        game_date = game_info.get("commence_time")

        home_rest = self._get_rest_score(sport, home_team, game_date, is_home=True)
        away_rest = self._get_rest_score(sport, away_team, game_date, is_home=False)

        rest_advantage = home_rest - away_rest
        confidence = 0.5 + (rest_advantage * 0.05)
        confidence = max(0.3, min(0.9, confidence))

        pick = (
            game_info.get("home_team")
            if rest_advantage > 0
            else game_info.get("away_team")
        )
        reasoning = f"Rest advantage: {home_team} ({home_rest:.1f}) vs {away_team} ({away_rest:.1f})"

        return AnalysisResult(
            game_id=game_id,
            model="rest_schedule",
            analysis_type="game",
            sport=sport,
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_date,
            prediction=pick,
            confidence=confidence,
            reasoning=reasoning,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop based on team rest situation"""
        sport = prop_item.get("sport")
        player_name = prop_item.get("player_name", "").lower().replace(" ", "_")
        game_date = prop_item.get("commence_time")

        # Get team from player stats
        team = self._get_player_team(sport, player_name)
        if not team:
            return None

        rest_score = self._get_rest_score(sport, team, game_date, is_home=True)

        confidence = 0.5 + (rest_score * 0.03)
        confidence = max(0.3, min(0.8, confidence))

        pick = "over" if rest_score > 1 else "under"
        reasoning = f"Team rest score: {rest_score:.1f}"

        return AnalysisResult(
            game_id=prop_item.get("game_id"),
            model="rest_schedule",
            analysis_type="prop",
            sport=sport,
            player_name=prop_item.get("player_name"),
            market_key=prop_item.get("market_key"),
            commence_time=game_date,
            prediction=pick,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _get_rest_score(
        self, sport: str, team: str, game_date: str, is_home: bool
    ) -> float:
        """Calculate rest score for a team"""
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND sk <= :date",
                ExpressionAttributeValues={
                    ":pk": f"SCHEDULE#{sport}#{team}",
                    ":date": game_date,
                },
                ScanIndexForward=False,
                Limit=2,
            )

            items = response.get("Items", [])
            if not items:
                return 0.0

            # Current game
            current_game = items[0]
            rest_days = current_game.get("rest_days", 2)

            score = 0.0

            # Rest days factor
            if rest_days >= 3:
                score += 3.0
            elif rest_days == 2:
                score += 1.5
            elif rest_days == 1:
                score += 0.5
            elif rest_days == 0:
                score -= 3.0  # Back-to-back

            # Home advantage
            if is_home:
                score += 1.0
            else:
                score -= 0.5

            return score

        except Exception as e:
            print(f"Error getting rest score: {e}")
            return 0.0

    def _get_player_team(self, sport: str, player_name: str) -> Optional[str]:
        """Get team for a player from recent stats"""
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={
                    ":pk": f"PLAYER_STATS#{sport}#{player_name}"
                },
                ScanIndexForward=False,
                Limit=1,
            )

            items = response.get("Items", [])
            if items:
                return items[0].get("team", "").lower().replace(" ", "_")
            return None

        except Exception as e:
            print(f"Error getting player team: {e}")
            return None


class MatchupModel(BaseAnalysisModel):
    """Model that analyzes head-to-head history and style matchups"""

    def __init__(self, dynamodb_table=None):
        """Initialize with optional DynamoDB table"""
        self.table = dynamodb_table
        if not self.table:
            import boto3
            import os

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """Analyze game based on matchup history and team styles"""
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")

        # Get head-to-head history
        h2h_advantage = self._get_h2h_advantage(sport, home_team, away_team)

        # Get style matchup
        style_advantage = self._get_style_matchup(sport, home_team, away_team)

        # Combined advantage
        total_advantage = (h2h_advantage * 0.6) + (style_advantage * 0.4)

        # Calculate confidence
        confidence = 0.5 + (abs(total_advantage) * 0.1)
        confidence = max(0.3, min(0.85, confidence))

        # Make prediction
        pick = home_team if total_advantage > 0 else away_team

        reasoning = f"H2H: {h2h_advantage:.1f}, Style: {style_advantage:.1f}"

        return AnalysisResult(
            game_id=game_id,
            model="matchup",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=pick,
            confidence=confidence,
            reasoning=reasoning,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop based on player matchup history"""
        try:
            player = prop_item.get("player_name")
            if not player:
                return None

            sport = prop_item.get("sport")

            # Get opponent from game info
            game_id = prop_item.get("event_id")
            game_response = self.table.get_item(
                Key={"pk": f"GAME#{game_id}", "sk": "LATEST"}
            )
            game_item = game_response.get("Item", {})
            home_team = game_item.get("home_team", "")
            away_team = game_item.get("away_team", "")

            # Determine opponent (player's team vs opponent)
            player_team = prop_item.get("team", "")
            opponent = away_team if player_team == home_team else home_team

            # Get player's historical stats vs this opponent
            vs_opponent_avg = self._get_player_vs_opponent_avg(
                sport, player, opponent, prop_item.get("market_key")
            )

            if vs_opponent_avg is None:
                return None

            # Compare to prop line
            prop_line = float(prop_item.get("point", 0))
            diff = vs_opponent_avg - prop_line

            # Calculate confidence based on difference
            confidence = 0.5 + min(abs(diff) * 0.05, 0.25)

            if diff > 2:
                prediction = f"Over {prop_line}"
                reasoning = f"Averages {vs_opponent_avg:.1f} vs {opponent}"
            elif diff < -2:
                prediction = f"Under {prop_line}"
                reasoning = f"Averages {vs_opponent_avg:.1f} vs {opponent}"
            else:
                return None  # Not confident enough

            return AnalysisResult(
                game_id=game_id,
                model="matchup",
                analysis_type="prop",
                sport=sport,
                home_team=home_team,
                away_team=away_team,
                commence_time=game_item.get("commence_time"),
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
            )
        except Exception as e:
            print(f"Error analyzing prop matchup: {e}")
            return None

    def _get_h2h_advantage(self, sport: str, home_team: str, away_team: str) -> float:
        """Get head-to-head advantage from historical games"""
        try:
            # Normalize team names for H2H query
            home_normalized = home_team.lower().replace(" ", "_")
            away_normalized = away_team.lower().replace(" ", "_")

            # Sort teams alphabetically for consistent H2H key
            teams_sorted = sorted([home_normalized, away_normalized])
            h2h_pk = f"H2H#{sport}#{teams_sorted[0]}#{teams_sorted[1]}"

            # Query H2H index for recent games
            response = self.table.query(
                IndexName="H2HIndex",
                KeyConditionExpression="h2h_pk = :pk",
                ExpressionAttributeValues={":pk": h2h_pk},
                ScanIndexForward=False,  # Most recent first
                Limit=10,
            )

            home_wins = 0
            away_wins = 0
            total_games = 0

            for item in response.get("Items", []):
                winner = item.get("winner", "")
                if winner == home_team:
                    home_wins += 1
                elif winner == away_team:
                    away_wins += 1
                total_games += 1

            if total_games == 0:
                return 0.0

            # Calculate advantage (-2 to +2 scale)
            win_rate = home_wins / total_games
            return (win_rate - 0.5) * 4

        except Exception as e:
            print(f"Error getting H2H advantage: {e}")
            return 0.0

    def _get_style_matchup(self, sport: str, home_team: str, away_team: str) -> float:
        """Analyze style matchup between teams"""
        try:
            home_stats = self._get_team_stats(sport, home_team)
            away_stats = self._get_team_stats(sport, away_team)

            if not home_stats or not away_stats:
                return 0.0

            # Compare offensive vs defensive ratings
            home_offense = home_stats.get("points_per_game", 0)
            home_defense = home_stats.get("points_allowed_per_game", 999)
            away_offense = away_stats.get("points_per_game", 0)
            away_defense = away_stats.get("points_allowed_per_game", 999)

            # Home advantage calculation:
            # Positive if home offense beats away defense AND home defense beats away offense
            # Home offense vs away defense (higher offense vs lower defense = advantage)
            offense_matchup = home_offense - away_defense
            # Home defense vs away offense (lower defense vs higher offense = advantage)
            defense_matchup = away_offense - home_defense

            # Combine (both should be positive for home advantage)
            return (offense_matchup + defense_matchup) / 20

        except Exception as e:
            print(f"Error getting style matchup: {e}")
            return 0.0

    def _get_team_stats(self, sport: str, team: str) -> Optional[Dict]:
        """Get recent team statistics"""
        try:
            team_key = team.lower().replace(" ", "_")
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": f"TEAM_STATS#{sport}#{team_key}"},
                ScanIndexForward=False,
                Limit=1,
            )

            items = response.get("Items", [])
            return items[0] if items else None

        except Exception as e:
            print(f"Error getting team stats: {e}")
            return None

    def _get_player_vs_opponent_avg(
        self, sport: str, player_name: str, opponent: str, stat_key: str
    ) -> Optional[float]:
        """Get player's average stat vs specific opponent"""
        try:
            normalized_player = player_name.lower().replace(" ", "_")
            normalized_opponent = opponent.lower().replace(" ", "_")

            # Query all player stats, then filter by opponent
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={
                    ":pk": f"PLAYER_STATS#{sport}#{normalized_player}",
                },
                ScanIndexForward=False,
                Limit=20,  # Get more, filter to last 5 vs opponent
            )

            items = response.get("Items", [])
            if not items:
                return None

            # Filter for opponent in SK
            opponent_games = [
                item
                for item in items
                if normalized_opponent in item.get("sk", "").lower()
            ][
                :5
            ]  # Last 5 vs this opponent

            if not opponent_games:
                return None

            # Map prop key to stat name
            stat_map = {
                "player_points": "PTS",
                "player_rebounds": "REB",
                "player_assists": "AST",
                "player_threes": "3PM",
            }
            stat_name = stat_map.get(stat_key, "PTS")

            # Calculate average
            total = 0
            count = 0
            for item in opponent_games:
                stats = item.get("stats", {})
                stat_value = stats.get(stat_name)
                if stat_value:
                    total += float(stat_value)
                    count += 1

            return total / count if count > 0 else None

        except Exception as e:
            print(f"Error getting player vs opponent avg: {e}")
            return None


class InjuryAwareModel(BaseAnalysisModel):
    """Injury-Aware model: Adjust predictions based on player injuries"""

    def __init__(self, dynamodb_table=None):
        self.table = dynamodb_table
        if not self.table:
            import boto3
            import os

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """Analyze game odds considering injury impact"""
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        sport = game_info.get("sport")

        # Get injuries for both teams
        home_injuries = self._get_team_injuries(home_team, sport)
        away_injuries = self._get_team_injuries(away_team, sport)

        # Calculate injury impact scores
        home_impact = self._calculate_injury_impact(home_injuries)
        away_impact = self._calculate_injury_impact(away_injuries)

        # Determine prediction based on injury differential
        impact_diff = away_impact - home_impact  # Higher away impact favors home
        spread = self._get_current_spread(odds_items)

        if abs(impact_diff) > 0.3:
            confidence = 0.75
            if impact_diff > 0:
                prediction = f"{home_team} {spread:+.1f}"
                reasoning = f"{away_team} has {len(away_injuries)} key injuries. {home_team} healthier with {len(home_injuries)} injuries."
            else:
                prediction = f"{away_team} {-spread:+.1f}"
                reasoning = f"{home_team} has {len(home_injuries)} key injuries. {away_team} healthier with {len(away_injuries)} injuries."
        elif abs(impact_diff) > 0.15:
            confidence = 0.65
            if impact_diff > 0:
                prediction = f"{home_team} {spread:+.1f}"
                reasoning = f"{away_team} dealing with injuries ({len(away_injuries)} out). {home_team} advantage."
            else:
                prediction = f"{away_team} {-spread:+.1f}"
                reasoning = f"{home_team} dealing with injuries ({len(home_injuries)} out). {away_team} advantage."
        else:
            confidence = 0.55
            prediction = f"{home_team} {spread:+.1f}"
            reasoning = f"Both teams relatively healthy. {home_team}: {len(home_injuries)} injuries, {away_team}: {len(away_injuries)} injuries."

        return AnalysisResult(
            game_id=game_id,
            model="injury_aware",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop considering player injury status"""
        try:
            player_name = prop_item.get("player_name", "Unknown Player")
            sport = prop_item.get("sport")
            market_key = prop_item.get("market_key", "")
            line = prop_item.get("point", 0)

            # Check if player is injured
            player_injury = self._get_player_injury_status(player_name, sport)

            if player_injury and player_injury.get("status") in ["Out", "Doubtful"]:
                return AnalysisResult(
                    game_id=prop_item.get("event_id", "unknown"),
                    bookmaker="injury_aware",
                    model="injury_aware",
                    analysis_type="prop",
                    sport=sport,
                    home_team=prop_item.get("home_team"),
                    away_team=prop_item.get("away_team"),
                    commence_time=prop_item.get("commence_time"),
                    player_name=player_name,
                    market_key=market_key,
                    prediction="AVOID",
                    confidence=0.9,
                    reasoning=f"{player_name} listed as {player_injury['status']} ({player_injury.get('injury_type', 'injury')}). Avoid this prop.",
                )

            # Player is healthy or questionable
            confidence = 0.6 if player_injury else 0.55
            status_note = (
                f" (listed as {player_injury['status']})" if player_injury else ""
            )

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                bookmaker="injury_aware",
                model="injury_aware",
                analysis_type="prop",
                sport=sport,
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=player_name,
                market_key=market_key,
                prediction=f"Over {line}",
                confidence=confidence,
                reasoning=f"{player_name} healthy{status_note}. Monitor injury reports before game.",
            )

        except Exception as e:
            print(f"Error analyzing injury-aware prop: {e}")
            return None

    def _get_team_injuries(self, team: str, sport: str) -> List[Dict]:
        """Get current injuries for a team"""
        try:
            # Map team name to ESPN team ID (simplified - would need full mapping)
            team_id = self._get_team_id(team, sport)
            if not team_id:
                return []

            pk = f"INJURIES#{sport}#{team_id}"
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                Limit=1,
                ScanIndexForward=False,
            )

            items = response.get("Items", [])
            if items:
                return [
                    inj
                    for inj in items[0].get("injuries", [])
                    if inj.get("status") == "Out"
                ]
            return []

        except Exception as e:
            print(f"Error getting team injuries: {e}")
            return []

    def _get_player_injury_status(self, player_name: str, sport: str) -> Dict:
        """Check if a specific player is injured"""
        try:
            # Normalize player name to match storage format
            normalized_name = player_name.lower().replace(" ", "_")
            pk = f"PLAYER_INJURY#{sport}#{normalized_name}"

            response = self.table.query(
                KeyConditionExpression="pk = :pk AND sk = :sk",
                ExpressionAttributeValues={":pk": pk, ":sk": "LATEST"},
                Limit=1,
            )

            items = response.get("Items", [])
            if items:
                item = items[0]
                return {
                    "status": item.get("status"),
                    "injury_type": item.get("injury_type"),
                    "return_date": item.get("return_date"),
                }

            return None

        except Exception as e:
            print(f"Error checking player injury status: {e}")
            return None

    def _calculate_injury_impact(self, injuries: List[Dict]) -> float:
        """Calculate overall injury impact (0-1 scale) weighted by player importance"""
        if not injuries:
            return 0.0

        # Weight injuries by average minutes played
        # Starters typically play 30+ minutes, bench players 10-20
        total_impact = 0.0
        for injury in injuries:
            avg_minutes = injury.get("avg_minutes", 0)

            # Convert minutes to importance weight (0-1 scale)
            # 35+ minutes = 1.0 (star player)
            # 25-35 minutes = 0.7 (starter)
            # 15-25 minutes = 0.4 (rotation player)
            # <15 minutes = 0.2 (bench player)
            if avg_minutes >= 35:
                weight = 1.0
            elif avg_minutes >= 25:
                weight = 0.7
            elif avg_minutes >= 15:
                weight = 0.4
            else:
                weight = 0.2

            total_impact += weight * 0.3  # Each weighted injury adds up to 0.3

        # Cap at 1.0
        return min(total_impact, 1.0)

    def _get_current_spread(self, odds_items: List[Dict]) -> float:
        """Get current spread from odds items"""
        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    return float(item["outcomes"][0].get("point", 0))
        return 0.0

    def _get_team_id(self, team_name: str, sport: str) -> str:
        """Map team name to ESPN team ID"""
        team_mapping = {
            "basketball_nba": {
                "Atlanta Hawks": "1",
                "Boston Celtics": "2",
                "Brooklyn Nets": "17",
                "Charlotte Hornets": "30",
                "Chicago Bulls": "4",
                "Cleveland Cavaliers": "5",
                "Dallas Mavericks": "6",
                "Denver Nuggets": "7",
                "Detroit Pistons": "8",
                "Golden State Warriors": "9",
                "Houston Rockets": "10",
                "Indiana Pacers": "11",
                "LA Clippers": "12",
                "Los Angeles Lakers": "13",
                "Memphis Grizzlies": "29",
                "Miami Heat": "14",
                "Milwaukee Bucks": "15",
                "Minnesota Timberwolves": "16",
                "New Orleans Pelicans": "3",
                "New York Knicks": "18",
                "Oklahoma City Thunder": "25",
                "Orlando Magic": "19",
                "Philadelphia 76ers": "20",
                "Phoenix Suns": "21",
                "Portland Trail Blazers": "22",
                "Sacramento Kings": "23",
                "San Antonio Spurs": "24",
                "Toronto Raptors": "28",
                "Utah Jazz": "26",
                "Washington Wizards": "27",
            },
            "americanfootball_nfl": {
                "Arizona Cardinals": "22",
                "Atlanta Falcons": "1",
                "Baltimore Ravens": "33",
                "Buffalo Bills": "2",
                "Carolina Panthers": "29",
                "Chicago Bears": "3",
                "Cincinnati Bengals": "4",
                "Cleveland Browns": "5",
                "Dallas Cowboys": "6",
                "Denver Broncos": "7",
                "Detroit Lions": "8",
                "Green Bay Packers": "9",
                "Houston Texans": "34",
                "Indianapolis Colts": "11",
                "Jacksonville Jaguars": "30",
                "Kansas City Chiefs": "12",
                "Las Vegas Raiders": "13",
                "Los Angeles Chargers": "24",
                "Los Angeles Rams": "14",
                "Miami Dolphins": "15",
                "Minnesota Vikings": "16",
                "New England Patriots": "17",
                "New Orleans Saints": "18",
                "New York Giants": "19",
                "New York Jets": "20",
                "Philadelphia Eagles": "21",
                "Pittsburgh Steelers": "23",
                "San Francisco 49ers": "25",
                "Seattle Seahawks": "26",
                "Tampa Bay Buccaneers": "27",
                "Tennessee Titans": "10",
                "Washington Commanders": "28",
            },
            "baseball_mlb": {
                "Arizona Diamondbacks": "29",
                "Athletics": "11",
                "Atlanta Braves": "15",
                "Baltimore Orioles": "1",
                "Boston Red Sox": "2",
                "Chicago Cubs": "16",
                "Chicago White Sox": "4",
                "Cincinnati Reds": "17",
                "Cleveland Guardians": "5",
                "Colorado Rockies": "27",
                "Detroit Tigers": "6",
                "Houston Astros": "18",
                "Kansas City Royals": "7",
                "Los Angeles Angels": "3",
                "Los Angeles Dodgers": "19",
                "Miami Marlins": "28",
                "Milwaukee Brewers": "8",
                "Minnesota Twins": "9",
                "New York Mets": "21",
                "New York Yankees": "10",
                "Philadelphia Phillies": "22",
                "Pittsburgh Pirates": "23",
                "San Diego Padres": "25",
                "San Francisco Giants": "26",
                "Seattle Mariners": "12",
                "St. Louis Cardinals": "24",
                "Tampa Bay Rays": "30",
                "Texas Rangers": "13",
                "Toronto Blue Jays": "14",
                "Washington Nationals": "20",
            },
            "icehockey_nhl": {
                "Anaheim Ducks": "25",
                "Boston Bruins": "1",
                "Buffalo Sabres": "2",
                "Calgary Flames": "3",
                "Carolina Hurricanes": "7",
                "Chicago Blackhawks": "4",
                "Colorado Avalanche": "17",
                "Columbus Blue Jackets": "29",
                "Dallas Stars": "9",
                "Detroit Red Wings": "5",
                "Edmonton Oilers": "6",
                "Florida Panthers": "26",
                "Los Angeles Kings": "8",
                "Minnesota Wild": "30",
                "Montreal Canadiens": "10",
                "Nashville Predators": "27",
                "New Jersey Devils": "11",
                "New York Islanders": "12",
                "New York Rangers": "13",
                "Ottawa Senators": "14",
                "Philadelphia Flyers": "15",
                "Pittsburgh Penguins": "16",
                "San Jose Sharks": "18",
                "Seattle Kraken": "124292",
                "St. Louis Blues": "19",
                "Tampa Bay Lightning": "20",
                "Toronto Maple Leafs": "21",
                "Utah Mammoth": "129764",
                "Vancouver Canucks": "22",
                "Vegas Golden Knights": "37",
                "Washington Capitals": "23",
                "Winnipeg Jets": "28",
            },
        }
        return team_mapping.get(sport, {}).get(team_name)


class ModelFactory:
    """Factory for creating analysis models"""

    _models = {
        "consensus": ConsensusModel,
        "value": ValueModel,
        "momentum": MomentumModel,
        "contrarian": ContrarianModel,
        "hot_cold": HotColdModel,
        "rest_schedule": RestScheduleModel,
        "matchup": MatchupModel,
        "injury_aware": InjuryAwareModel,
    }

    @classmethod
    def create_model(cls, model_name: str) -> BaseAnalysisModel:
        """Create and return a model instance"""
        if model_name not in cls._models:
            raise ValueError(
                f"Unknown model: {model_name}. Available: {list(cls._models.keys())}"
            )

        return cls._models[model_name]()

    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of available model names"""
        return list(cls._models.keys())

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)
