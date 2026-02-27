#!/usr/bin/env python3
"""Simulate ensemble with improved weighting."""
import sys
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta
from collections import defaultdict

def simulate(env, sport, days=90):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(f"carpool-bets-v2-{env}")
    
    models = ["consensus", "value", "momentum", "contrarian", "hot_cold", 
              "rest_schedule", "matchup", "injury_aware"]
    
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    # Get performance for each model
    print(f"\nModel Performance (last {days} days):")
    print("-" * 60)
    performances = {}
    
    for model in models:
        pk = f"VERIFIED#{model}#{sport}#game"
        response = table.query(
            IndexName='VerifiedAnalysisGSI',
            KeyConditionExpression=Key('verified_analysis_pk').eq(pk) & Key('verified_analysis_sk').gte(cutoff)
        )
        
        items = response['Items']
        correct = sum(1 for i in items if i.get('analysis_correct'))
        total = len(items)
        accuracy = correct / total if total >= 20 else 0.0
        
        performances[model] = (accuracy, total)
        print(f"{model:20s}: {accuracy*100:5.1f}% ({total:3d} bets)")
    
    # Calculate new weights based on ROI from backtest
    roi_map = {
        'momentum': 0.0977,
        'rest_schedule': 0.0977,
        'consensus': 0.0359,
        'value': 0.0023,
        'hot_cold': 0.0023,
        'injury_aware': 0.0023,
        'contrarian': -0.2364,
        'matchup': -0.1250
    }
    
    weights = {}
    for model in models:
        roi = roi_map.get(model, 0)
        weights[model] = max(0, roi)  # Exclude negative ROI
    
    total_weight = sum(weights.values())
    weights = {m: w/total_weight for m, w in weights.items()} if total_weight > 0 else {m: 1.0/len(models) for m in models}
    
    print(f"\nNew Weights:")
    print("-" * 60)
    for model, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        print(f"{model:20s}: {weight*100:5.1f}%")
    
    # Get ensemble games
    pk = f"VERIFIED#ensemble#{sport}#game"
    response = table.query(
        IndexName='VerifiedAnalysisGSI',
        KeyConditionExpression=Key('verified_analysis_pk').eq(pk) & Key('verified_analysis_sk').gte(cutoff)
    )
    
    games = {}
    for item in response['Items']:
        game_id = item['game_id']
        games[game_id] = {
            'actual': item.get('analysis_correct', False),
            'verified_at': item['outcome_verified_at']
        }
    
    print(f"\nSimulating {len(games)} games...")
    
    # Recalculate ensemble predictions
    correct = 0
    total = 0
    bankroll = 10000
    
    for game_id in sorted(games.keys(), key=lambda g: games[g]['verified_at']):
        # Try common bookmakers
        model_confs = {}
        
        for bookmaker in ['fanduel', 'draftkings', 'betmgm']:
            for model in models:
                pk = f'ANALYSIS#basketball_nba#{game_id}#{bookmaker}'
                sk = f'{model}#game#LATEST'
                
                response = table.get_item(Key={'pk': pk, 'sk': sk})
                if 'Item' in response and response['Item'].get('confidence'):
                    model_confs[model] = float(response['Item']['confidence'])
            
            if len(model_confs) >= 3:
                break
        
        if len(model_confs) < 3:
            continue
        
        # Weighted average confidence
        weighted_conf = sum(model_confs[m] * weights.get(m, 0) for m in model_confs) / sum(weights.get(m, 0) for m in model_confs)
        predicted_home_win = weighted_conf > 0.5
        
        if predicted_home_win == games[game_id]['actual']:
            bankroll += 90.91
            correct += 1
        else:
            bankroll -= 110
        
        total += 1
    
    profit = bankroll - 10000
    roi_wagered = (profit / (total * 110)) * 100 if total > 0 else 0
    roi_bankroll = (profit / 10000) * 100
    
    print(f"\n{'='*60}")
    print(f"SIMULATED ENSEMBLE")
    print(f"{'='*60}")
    
    if total == 0:
        print("No games found to simulate")
        return
    
    print(f"Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"Total Profit: ${profit:,.2f}")
    print(f"ROI (on wagered): {roi_wagered:.2f}%")
    print(f"ROI (on bankroll): {roi_bankroll:.2f}%")
    print(f"Final Bankroll: ${bankroll:,.2f}")
    
    print(f"\nOriginal Ensemble: 53.8% accuracy, 2.64% ROI")
    print(f"Improvement: {(correct/total - 0.538)*100:+.1f}% accuracy, {(roi_wagered - 2.64):+.2f}% ROI")

if __name__ == "__main__":
    simulate(sys.argv[1] if len(sys.argv) > 1 else "dev", 
             sys.argv[2] if len(sys.argv) > 2 else "basketball_nba",
             int(sys.argv[3]) if len(sys.argv) > 3 else 90)
