"""
ML Models for Sports Betting Analytics
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class GamePrediction:
    game_id: str
    sport: str
    home_win_probability: float
    away_win_probability: float
    confidence_score: float
    value_bets: List[str]


@dataclass
class PlayerPropPrediction:
    player_name: str
    prop_type: str
    predicted_value: float
    over_probability: float
    under_probability: float
    confidence_score: float
    value_bets: List[str]


class OddsAnalyzer:
    @staticmethod
    def american_to_decimal(american_odds: int) -> float:
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    @staticmethod
    def decimal_to_probability(decimal_odds: float) -> float:
        return 1 / decimal_odds

    def analyze_game(self, game_data: Dict) -> GamePrediction:
        """Analyze a single game and return predictions"""

        # Extract moneyline odds from bookmaker items (new schema)
        home_odds = []
        away_odds = []
        bookmaker_names = []

        # New schema: game_data.bookmakers is a list of DynamoDB items
        bookmaker_items = game_data.get("bookmakers", [])
        home_team = game_data.get("home_team")
        away_team = game_data.get("away_team")

        for item in bookmaker_items:
            # Only process h2h (moneyline) markets
            if item.get("market_key") == "h2h":
                outcomes = item.get("outcomes", [])
                bookmaker_name = item.get("bookmaker")

                if len(outcomes) >= 2 and bookmaker_name:
                    # Find home and away team odds
                    home_outcome = next(
                        (o for o in outcomes if o["name"] == home_team), None
                    )
                    away_outcome = next(
                        (o for o in outcomes if o["name"] == away_team), None
                    )

                    if home_outcome and away_outcome:
                        home_odds.append(
                            self.american_to_decimal(int(home_outcome["price"]))
                        )
                        away_odds.append(
                            self.american_to_decimal(int(away_outcome["price"]))
                        )
                        bookmaker_names.append(bookmaker_name)

        if not home_odds:
            return GamePrediction(
                game_id=game_data.get("game_id", "unknown"),
                sport=game_data.get("sport", "unknown"),
                home_win_probability=0.5,
                away_win_probability=0.5,
                confidence_score=0.1,
                value_bets=[],
            )

        # Calculate consensus probabilities
        home_probs = [self.decimal_to_probability(odds) for odds in home_odds]
        away_probs = [self.decimal_to_probability(odds) for odds in away_odds]

        # Remove vig and normalize
        avg_home_prob = sum(home_probs) / len(home_probs)
        avg_away_prob = sum(away_probs) / len(away_probs)
        total_prob = avg_home_prob + avg_away_prob

        home_prob = avg_home_prob / total_prob
        away_prob = avg_away_prob / total_prob

        # Calculate confidence (lower std = higher confidence)
        home_std = self._calculate_std(home_probs)
        away_std = self._calculate_std(away_probs)
        confidence = 1 - (home_std + away_std) / 2
        confidence = max(0.1, min(0.9, confidence))

        # Find value bets (5% edge threshold)
        value_bets = []
        for i, bookmaker in enumerate(bookmaker_names):
            home_ev = home_prob - home_probs[i]
            away_ev = away_prob - away_probs[i]

            if home_ev > 0.05:
                value_bets.append(f"{bookmaker}_home")
            if away_ev > 0.05:
                value_bets.append(f"{bookmaker}_away")

        return GamePrediction(
            game_id=game_data.get("game_id", "unknown"),
            sport=game_data.get("sport", "unknown"),
            home_win_probability=round(home_prob, 3),
            away_win_probability=round(away_prob, 3),
            confidence_score=round(confidence, 3),
            value_bets=value_bets,
        )

    def analyze_player_props(
        self, props_data: List[Dict]
    ) -> List[PlayerPropPrediction]:
        """Analyze player props and return predictions"""
        predictions = []

        # Group props by player and market_key (prop type)
        grouped_props = {}
        for prop in props_data:
            key = f"{prop['player_name']}_{prop['market_key']}"
            if key not in grouped_props:
                grouped_props[key] = []
            grouped_props[key].append(prop)

        for key, prop_group in grouped_props.items():
            if not prop_group:
                continue

            player_name = prop_group[0]["player_name"]
            market_key = prop_group[0]["market_key"]

            # Group by Over/Under for the same line
            over_props = [p for p in prop_group if p["outcome"] == "Over"]
            under_props = [p for p in prop_group if p["outcome"] == "Under"]

            if not over_props or not under_props:
                continue

            # Use the most common point value
            points = [float(p["point"]) for p in prop_group if p.get("point")]
            if not points:
                continue
            consensus_line = max(set(points), key=points.count)

            # Calculate probabilities from Over odds
            over_probs = []
            for prop in over_props:
                if prop["point"] == consensus_line:
                    decimal_odds = self.american_to_decimal(int(prop["price"]))
                    prob = self.decimal_to_probability(decimal_odds)
                    over_probs.append(prob)

            if over_probs:
                avg_over_prob = sum(over_probs) / len(over_probs)
                avg_under_prob = 1 - avg_over_prob

                # Calculate confidence based on consensus
                confidence = 1 - abs(avg_over_prob - 0.5) * 2
                confidence = max(0.1, min(0.9, confidence))

                # Identify value bets
                value_bets = []
                for prop in over_props:
                    if prop["point"] == consensus_line:
                        decimal_odds = self.american_to_decimal(int(prop["price"]))
                        implied_prob = self.decimal_to_probability(decimal_odds)

                        if avg_over_prob > implied_prob * 1.05:  # 5% edge for over
                            value_bets.append(
                                f"Over {prop['point']} at {prop['bookmaker']}"
                            )

                predictions.append(
                    PlayerPropPrediction(
                        player_name=player_name,
                        prop_type=market_key,
                        predicted_value=round(consensus_line, 1),
                        over_probability=round(avg_over_prob, 3),
                        under_probability=round(avg_under_prob, 3),
                        confidence_score=round(confidence, 3),
                        value_bets=value_bets,
                    )
                )

        return predictions

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation without numpy"""
        if len(values) <= 1:
            return 0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance**0.5
