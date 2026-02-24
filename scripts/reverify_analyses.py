#!/usr/bin/env python3
"""
Re-verify all historical analyses using stored outcomes.
Fixes incorrect verification results caused by score parsing bug.
"""

import argparse
import boto3
from decimal import Decimal

def check_analysis_accuracy(prediction: str, actual_home_won: bool) -> bool:
    """Check if analysis prediction was correct."""
    if prediction == "home":
        return actual_home_won
    elif prediction == "away":
        return not actual_home_won
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
            
            outcome_pk = f"OUTCOME#{sport}#{game_id}"
            outcome_response = table.get_item(Key={"pk": outcome_pk, "sk": "RESULT"})
            
            if "Item" not in outcome_response:
                error_count += 1
                continue
            
            outcome = outcome_response["Item"]
            home_score = int(outcome["home_score"])
            away_score = int(outcome["away_score"])
            actual_home_won = home_score > away_score
            
            prediction = analysis.get("prediction")
            new_correct = check_analysis_accuracy(prediction, actual_home_won)
            old_correct = analysis.get("analysis_correct")
            
            if new_correct != old_correct:
                if not dry_run:
                    table.update_item(
                        Key={"pk": analysis["pk"], "sk": analysis["sk"]},
                        UpdateExpression="SET analysis_correct = :correct, actual_home_won = :home_won",
                        ExpressionAttributeValues={
                            ":correct": new_correct,
                            ":home_won": actual_home_won
                        }
                    )
                fixed_count += 1
                if fixed_count <= 5:
                    print(f"  🔧 {analysis['sk']}: {old_correct} → {new_correct} (score: {home_score}-{away_score})")
        
        except Exception as e:
            error_count += 1
    
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
