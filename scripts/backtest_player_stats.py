#!/usr/bin/env python3
"""Backtest player stats model on historical prop data"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta
from ml.player_stats_model import PlayerStatsModel

def backtest_player_stats(env, sport, days=90):
    """Simulate what player_stats model would have predicted"""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(f'carpool-bets-v2-{env}')
    
    # Get verified prop outcomes from any model
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    pk = f'VERIFIED#consensus#{sport}#prop'
    
    response = table.query(
        IndexName='VerifiedAnalysisGSI',
        KeyConditionExpression=Key('verified_analysis_pk').eq(pk) & Key('verified_analysis_sk').gte(cutoff)
    )
    
    props = response['Items']
    print(f"\nFound {len(props)} verified props to test\n")
    
    if not props:
        print("No prop data available")
        return
    
    model = PlayerStatsModel()
    
    correct = 0
    total = 0
    bankroll = 10000
    results = []
    
    for prop in sorted(props, key=lambda x: x.get('outcome_verified_at', '')):
        # Reconstruct prop item from verified outcome
        player_name = prop.get('player_name')
        market_key = prop.get('market_key')
        
        # Extract line from prediction (e.g., "Over 25.5" -> 25.5)
        prediction = prop.get('prediction', '')
        try:
            line = float(prediction.split()[-1])
        except:
            continue
        
        prop_item = {
            'player_name': player_name,
            'sport': sport,
            'market_key': market_key,
            'point': line,
            'event_id': prop.get('game_id'),
            'home_team': prop.get('home_team'),
            'away_team': prop.get('away_team'),
            'commence_time': prop.get('commence_time'),
            'bookmaker': prop.get('bookmaker', 'fanduel')
        }
        
        # Simulate what our model would predict
        result = model.analyze_prop_odds(prop_item)
        
        if result:
            # Check if prediction would have been correct
            actual_correct = prop.get('analysis_correct', False)
            
            if actual_correct:
                bankroll += 90.91
                correct += 1
            else:
                bankroll -= 110
            
            total += 1
            results.append((prop.get('outcome_verified_at'), bankroll))
    
    if total == 0:
        print("Model made no predictions (all lines were fair)")
        return
    
    # Calculate metrics
    accuracy = correct / total
    profit = bankroll - 10000
    roi_wagered = (profit / (total * 110)) * 100
    roi_bankroll = (profit / 10000) * 100
    
    # Sharpe ratio
    if len(results) > 1:
        returns = [results[i][1] - results[i-1][1] for i in range(1, len(results))]
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe = (avg_return / std_return) if std_return > 0 else 0
    else:
        sharpe = 0
    
    # Max drawdown
    peak = 10000
    max_dd = 0
    for _, value in results:
        if value > peak:
            peak = value
        dd = peak - value
        if dd > max_dd:
            max_dd = dd
    
    print(f"{'='*60}")
    print(f"PLAYER STATS MODEL - {sport} - props")
    print(f"{'='*60}")
    print(f"Predictions Made: {total}")
    print(f"Accuracy: {correct}/{total} ({accuracy*100:.1f}%)")
    print(f"Total Profit: ${profit:,.2f}")
    print(f"ROI (on wagered): {roi_wagered:.2f}%")
    print(f"ROI (on bankroll): {roi_bankroll:.2f}%")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Max Drawdown: ${max_dd:,.2f}")
    print(f"Final Bankroll: ${bankroll:,.2f}")
    
    # Compare to best existing prop model
    print(f"\nBest existing prop model: momentum (41.2% accuracy, -21.32% ROI)")
    print(f"Improvement: {(accuracy - 0.412)*100:+.1f}% accuracy, {(roi_wagered + 21.32):+.2f}% ROI")

if __name__ == "__main__":
    env = sys.argv[1] if len(sys.argv) > 1 else "dev"
    sport = sys.argv[2] if len(sys.argv) > 2 else "basketball_nba"
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 90
    
    backtest_player_stats(env, sport, days)
