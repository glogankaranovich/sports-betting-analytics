"""Benny V2 — V1 + feature extraction and learned feature insights.

Extends V1 with:
- Feature insights in prompts (learned feature importance from OutcomeAnalyzer)
- Feature analysis + threshold optimization in post_run
"""
from datetime import datetime
from typing import Any, Dict

from benny.models.v1 import BennyV1


class BennyV2(BennyV1):

    @property
    def pk(self) -> str:
        return "BENNY_V2"

    @property
    def version(self) -> str:
        return "v2"

    def _get_feature_insights(self) -> str:
        """Get learned feature importance insights for AI prompt."""
        try:
            response = self.table.get_item(
                Key={"pk": f"{self.pk}#LEARNING", "sk": "FEATURES"}
            )
            insights = response.get("Item", {}).get("insights", {})
            if not insights or "strongest_predictors" not in insights:
                return "Insufficient data to determine feature importance"

            lines = ["LEARNED FEATURE IMPORTANCE (What Actually Predicts Wins):"]
            for pred in insights["strongest_predictors"][:3]:
                feature = pred["feature"]
                lines.append(f"\n{feature.upper()} (predictive power: {pred['spread']:.1%} spread)")
                feature_data = insights.get("insights", {}).get(feature, {})
                if feature_data:
                    for range_key, data in sorted(feature_data.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True)[:3]:
                        if data.get("count", 0) >= 5:
                            lines.append(f"  • {range_key}: {data['win_rate']:.1%} win rate ({data['count']} bets)")
            return "\n".join(lines)
        except Exception:
            return "Error loading feature insights"

    def post_run(self, results: Dict[str, Any]):
        """V1 learning + feature analysis + threshold optimization."""
        # V1 learning update
        super().post_run(results)

        # Feature analysis
        try:
            from benny.outcome_analyzer import OutcomeAnalyzer
            from benny.threshold_optimizer import ThresholdOptimizer

            analyzer = OutcomeAnalyzer(self.table, self.pk)
            insights = analyzer.analyze_features()
            if "error" in insights:
                print(f"Feature analysis: {insights['error']} ({insights.get('bet_count', 0)} bets)")
            else:
                print(f"\n=== FEATURE ANALYSIS ({insights['total_bets']} bets) ===")
                for pred in insights["strongest_predictors"][:5]:
                    print(f"  {pred['feature']}: {pred['spread']:.1%} spread")
                insights["timestamp"] = datetime.utcnow().isoformat()
                analyzer.save_insights(insights)

            calibration = analyzer.analyze_confidence_calibration()
            if "error" not in calibration:
                print(f"Calibration error: {calibration['avg_calibration_error']:.1%}")
                calibration["timestamp"] = datetime.utcnow().isoformat()
                analyzer.save_calibration(calibration)

            optimizer = ThresholdOptimizer(self.table, self.pk)
            thresholds = optimizer.optimize_thresholds()
            if "error" not in thresholds:
                print(f"Optimal threshold: conf={thresholds['global']['optimal_min_confidence']:.0%}, EV={thresholds['global']['optimal_min_ev']:.1%}")
                thresholds["timestamp"] = datetime.utcnow().isoformat()
                optimizer.save_optimal_thresholds(thresholds)
        except Exception as e:
            print(f"Error in V2 feature analysis: {e}")
