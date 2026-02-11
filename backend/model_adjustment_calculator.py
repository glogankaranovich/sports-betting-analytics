"""
Model Adjustment Calculator

Runs periodically to calculate and store model performance adjustments.
Determines which models should use original predictions, inverse predictions, or be avoided.
"""
from ml.dynamic_weighting import DynamicModelWeighting


def lambda_handler(event, context):
    """Calculate and store model adjustments for all sports."""
    try:
        weighting = DynamicModelWeighting(lookback_days=30)

        sports = [
            "basketball_nba",
            "americanfootball_nfl",
            "baseball_mlb",
            "icehockey_nhl",
            "soccer_epl",
        ]

        all_adjustments = []

        for sport in sports:
            print(f"Calculating adjustments for {sport}...")

            # Game predictions
            game_adjustments = weighting.store_model_adjustments(sport, "game")
            all_adjustments.extend(game_adjustments)

            print(f"Stored {len(game_adjustments)} game adjustments for {sport}")

            # Prop predictions (if applicable)
            # prop_adjustments = weighting.store_model_adjustments(sport, "prop")
            # all_adjustments.extend(prop_adjustments)

        # Summary
        inverse_recommended = sum(
            1 for a in all_adjustments if a["recommendation"] == "INVERSE"
        )
        avoid_recommended = sum(
            1 for a in all_adjustments if a["recommendation"] == "AVOID"
        )

        print("\nSummary:")
        print(f"Total adjustments: {len(all_adjustments)}")
        print(f"Inverse recommended: {inverse_recommended}")
        print(f"Avoid recommended: {avoid_recommended}")

        return {
            "statusCode": 200,
            "body": {
                "message": "Model adjustments calculated successfully",
                "total_adjustments": len(all_adjustments),
                "inverse_recommended": inverse_recommended,
                "avoid_recommended": avoid_recommended,
                "adjustments": all_adjustments,
            },
        }

    except Exception as e:
        print(f"Error calculating model adjustments: {e}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": {"error": str(e)}}
