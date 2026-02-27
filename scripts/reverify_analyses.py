#!/usr/bin/env python3
"""
Re-verify all historical analyses using stored outcomes.
Fixes incorrect verification results caused by score parsing bug.
"""

import argparse
import boto3
import re
from decimal import Decimal

def check_game_analysis_accuracy(prediction: str, home_score: int, away_score: int, home_team: str, away_team: str) -> bool:
    """Check if game analysis was accurate (copied from outcome_collector.py)"""
    try:
        home_won = home_score > away_score
        prediction_lower = prediction.lower()
        home_team_lower = home_team.lower()
        away_team_lower = away_team.lower()

        # Check for spread bets
        if "+" in prediction or "-" in prediction:
            spread_match = re.search(r"([+-]\d+\.?\d*)", prediction)
            if spread_match:
                spread = float(spread_match.group(1))
                if home_team_lower in prediction_lower:
                    adjusted_score = home_score + spread
                    return adjusted_score > away_score
                elif away_team_lower in prediction_lower:
                    adjusted_score = away_score + spread
                    return adjusted_score > home_score

        # Check for totals
        if "over" in prediction_lower or "under" in prediction_lower:
            total_score = home_score + away_score
            total_match = re.search(r"(\d+\.?\d*)", prediction)
            if total_match:
                line = float(total_match.group(1))
                if "over" in prediction_lower:
                    return total_score > line
                else:
                    return total_score < line

        # Check for team name predictions
        if home_team_lower in prediction_lower:
            return home_won
        elif away_team_lower in prediction_lower:
            return not home_won

        # Fallback to home/away
        if prediction.lower() == "home":
            return home_won
        elif prediction.lower() == "away":
            return not home_won

        return False
    except Exception as e:
        print(f"Error checking accuracy: {e}")
        return False

def check_prop_analysis_accuracy(prediction: str, actual_value: float) -> bool:
    """Check if prop analysis was accurate"""
    try:
        prediction_lower = prediction.lower()
        
        if "over" in prediction_lower or "under" in prediction_lower:
            line_match = re.search(r"(\d+\.?\d*)", prediction)
            if line_match:
                line = float(line_match.group(1))
                if "over" in prediction_lower:
                    return actual_value > line
                else:
                    return actual_value < line
        return False
    except:
        return False

def reverify_analyses(environment: str, dry_run: bool = True):
    """Re-verify all analyses using stored outcomes."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table_name = f"carpool-bets-v2-{environment}"
    table = dynamodb.Table(table_name)
    
    print(f"🔍 Scanning for verified analyses in {environment}...")
    
    verified_analyses = []
    scan_kwargs = {"FilterExpression": "attribute_exists(outcome_verified_at)"}
    
    while True:
        response = table.scan(**scan_kwargs)
        verified_analyses.extend(response["Items"])
        
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        print(f"  Scanned {len(verified_analyses)} analyses so far...")
    
    print(f"✓ Found {len(verified_analyses)} verified analyses")
    
    fixed_count = 0
    error_count = 0
    
    for analysis in verified_analyses:
        try:
            pk_parts = analysis["pk"].split("#")
            if len(pk_parts) < 3:
                continue
            
            sport = pk_parts[1]
            game_id = pk_parts[2]
            prediction = analysis.get("prediction", "")
            is_prop = "prop" in analysis.get("sk", "").lower()
            
            if is_prop:
                # For props, look up PROP_OUTCOME record
                player_name = analysis.get("player_name", "")
                market_key = analysis.get("market_key", "")
                player_normalized = player_name.lower().replace(" ", "_")
                
                prop_outcome_pk = f"PROP_OUTCOME#{sport}#{game_id}#{player_normalized}"
                prop_outcome_response = table.get_item(Key={"pk": prop_outcome_pk, "sk": f"RESULT#{market_key}"})
                
                if "Item" not in prop_outcome_response:
                    error_count += 1
                    if error_count <= 5:
                        print(f"  ⚠️  No prop outcome for {player_name} {market_key}")
                    continue
                
                actual_value = float(prop_outcome_response["Item"]["actual_value"])
                new_correct = check_prop_analysis_accuracy(prediction, actual_value)
                actual_home_won = None  # Not applicable for props
            else:
                # For games, look up OUTCOME record
                outcome_pk = f"OUTCOME#{sport}#{game_id}"
                outcome_response = table.get_item(Key={"pk": outcome_pk, "sk": "RESULT"})
                
                if "Item" not in outcome_response:
                    error_count += 1
                    if error_count <= 5:
                        print(f"  ⚠️  No outcome found for {sport}#{game_id}")
                    continue
                
                outcome = outcome_response["Item"]
                home_score = int(outcome["home_score"])
                away_score = int(outcome["away_score"])
                actual_home_won = home_score > away_score
                home_team = outcome.get("home_team", "")
                away_team = outcome.get("away_team", "")
                
                new_correct = check_game_analysis_accuracy(prediction, home_score, away_score, home_team, away_team)
            
            old_correct = analysis.get("analysis_correct")
            
            if new_correct != old_correct:
                if not dry_run:
                    update_expr = "SET analysis_correct = :correct"
                    expr_values = {":correct": new_correct}
                    
                    if actual_home_won is not None:
                        update_expr += ", actual_home_won = :home_won"
                        expr_values[":home_won"] = actual_home_won
                    
                    table.update_item(
                        Key={"pk": analysis["pk"], "sk": analysis["sk"]},
                        UpdateExpression=update_expr,
                        ExpressionAttributeValues=expr_values
                    )
                fixed_count += 1
                if fixed_count <= 5:
                    result_info = f"score: {home_score}-{away_score}" if not is_prop else f"actual: {actual_value}"
                    print(f"  🔧 {analysis['sk']}: {old_correct} → {new_correct} ({result_info})")
        
        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"  ❌ Error: {analysis.get('pk')}/{analysis.get('sk')}: {e}")
    
    print(f"\n📊 Summary:")
    print(f"  Total verified: {len(verified_analyses)}")
    print(f"  Fixed: {fixed_count}")
    print(f"  Errors: {error_count}")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN - No changes made. Run with --execute to apply fixes.")
    else:
        print(f"\n✅ Re-verification complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-verify analyses using stored outcomes")
    parser.add_argument("environment", choices=["dev", "beta", "prod"], help="Environment to fix")
    parser.add_argument("--execute", action="store_true", help="Actually apply fixes (default is dry run)")
    
    args = parser.parse_args()
    reverify_analyses(args.environment, dry_run=not args.execute)
