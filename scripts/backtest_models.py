#!/usr/bin/env python3
"""
Backtest sports betting models using historical verified analyses.
Calculate accuracy, ROI, Sharpe ratio, and other performance metrics.
"""

import argparse
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

def backtest_model(environment: str, model: str, sport: str, days: int, bet_type: str = "game"):
    """Backtest a specific model"""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table_name = f"carpool-bets-v2-{environment}"
    table = dynamodb.Table(table_name)
    
    print(f"\n{'='*60}")
    print(f"Backtesting: {model} - {sport} - {bet_type}")
    print(f"{'='*60}\n")
    
    # Query verified analyses
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    pk = f"VERIFIED#{model}#{sport}#{bet_type}"
    
    response = table.query(
        IndexName="VerifiedAnalysisGSI",
        KeyConditionExpression=Key("verified_analysis_pk").eq(pk) & Key("verified_analysis_sk").gte(cutoff)
    )
    
    analyses = response["Items"]
    print(f"Found {len(analyses)} verified predictions\n")
    
    if not analyses:
        return None
    
    # Calculate metrics
    total = len(analyses)
    correct = sum(1 for a in analyses if a.get("analysis_correct"))
    accuracy = correct / total if total > 0 else 0
    
    # Simulate betting with flat stakes
    starting_bankroll = 10000  # Start with $10,000
    stake = 100  # $100 per bet
    bankroll = [starting_bankroll]
    current = starting_bankroll
    
    for analysis in sorted(analyses, key=lambda x: x.get("outcome_verified_at", "")):
        if analysis.get("analysis_correct"):
            # Win: assume -110 odds (risk $110 to win $100)
            profit = stake * (100/110)
        else:
            # Loss
            profit = -stake
        
        current += profit
        bankroll.append(current)
    
    # Calculate metrics
    total_profit = current - starting_bankroll
    total_wagered = stake * total
    roi = (total_profit / total_wagered) * 100 if total_wagered > 0 else 0
    bankroll_roi = (total_profit / starting_bankroll) * 100
    
    # Sharpe ratio (risk-adjusted return)
    if len(bankroll) > 1:
        returns = [bankroll[i] - bankroll[i-1] for i in range(1, len(bankroll))]
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0
        sharpe = (avg_return / std_return) if std_return > 0 else 0
    else:
        sharpe = 0
    
    # Max drawdown
    peak = 0
    max_dd = 0
    for value in bankroll:
        if value > peak:
            peak = value
        dd = peak - value
        if dd > max_dd:
            max_dd = dd
    
    # Print results
    print(f"Starting Bankroll: ${starting_bankroll:,.2f}")
    print(f"Accuracy: {correct}/{total} ({accuracy:.1%})")
    print(f"Total Profit: ${total_profit:,.2f}")
    print(f"ROI (on wagered): {roi:.2f}%")
    print(f"ROI (on bankroll): {bankroll_roi:.2f}%")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Max Drawdown: ${max_dd:,.2f}")
    print(f"Final Bankroll: ${current:,.2f}")
    
    return {
        "model": model,
        "sport": sport,
        "bet_type": bet_type,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "roi": roi,
        "bankroll_roi": bankroll_roi,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "final_bankroll": current
    }

def compare_models(environment: str, sport: str, days: int):
    """Compare all models for a sport"""
    models = ["consensus", "contrarian", "ensemble", "value", "momentum", "rest_schedule", 
              "matchup", "hot_cold", "injury_aware", "news"]
    
    results = []
    for model in models:
        for bet_type in ["game", "prop"]:
            result = backtest_model(environment, model, sport, days, bet_type)
            if result:
                results.append(result)
    
    # Sort by ROI
    results.sort(key=lambda x: x["roi"], reverse=True)
    
    print(f"\n{'='*80}")
    print(f"MODEL COMPARISON - {sport.upper()} - Last {days} days")
    print(f"{'='*80}\n")
    print(f"{'Model':<20} {'Type':<6} {'Accuracy':<12} {'ROI':<10} {'Sharpe':<10} {'Bets':<6}")
    print(f"{'-'*80}")
    
    for r in results:
        print(f"{r['model']:<20} {r['bet_type']:<6} {r['accuracy']:>10.1%}  {r['roi']:>8.2f}%  {r['sharpe']:>8.2f}  {r['total']:>5}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest sports betting models")
    parser.add_argument("environment", choices=["dev", "beta", "prod"])
    parser.add_argument("--model", help="Specific model to test")
    parser.add_argument("--sport", default="basketball_nba", help="Sport to test")
    parser.add_argument("--days", type=int, default=90, help="Days of history to test")
    parser.add_argument("--bet-type", default="game", choices=["game", "prop"])
    parser.add_argument("--compare", action="store_true", help="Compare all models")
    
    args = parser.parse_args()
    
    if args.compare:
        compare_models(args.environment, args.sport, args.days)
    elif args.model:
        backtest_model(args.environment, args.model, args.sport, args.days, args.bet_type)
    else:
        print("Specify --model or --compare")
