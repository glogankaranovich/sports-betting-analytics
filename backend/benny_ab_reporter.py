"""Daily A/B comparison report for Benny v1 vs v3"""
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
import boto3
from boto3.dynamodb.conditions import Key


def calculate_metrics(bets: List[Dict]) -> Dict[str, Any]:
    """Calculate performance metrics from bet list"""
    if not bets:
        return {
            "total_bets": 0,
            "win_rate": 0,
            "roi": 0,
            "total_wagered": 0,
            "total_profit": 0,
            "avg_bet_size": 0,
            "by_sport": {},
            "by_market": {}
        }
    
    total_wagered = sum(float(b.get("bet_amount", 0)) for b in bets)
    settled = [b for b in bets if b.get("status") in ["won", "lost"]]
    wins = [b for b in settled if b.get("status") == "won"]
    
    total_profit = sum(float(b.get("profit", 0)) for b in settled)
    roi = (total_profit / total_wagered * 100) if total_wagered > 0 else 0
    win_rate = (len(wins) / len(settled) * 100) if settled else 0
    
    # By sport
    by_sport = {}
    for sport in set(b.get("sport") for b in bets):
        sport_bets = [b for b in settled if b.get("sport") == sport]
        sport_wins = [b for b in sport_bets if b.get("status") == "won"]
        if sport_bets:
            by_sport[sport] = {
                "bets": len(sport_bets),
                "win_rate": len(sport_wins) / len(sport_bets) * 100,
                "profit": sum(float(b.get("profit", 0)) for b in sport_bets)
            }
    
    # By market
    by_market = {}
    for market in set(b.get("market_key") for b in bets):
        market_bets = [b for b in settled if b.get("market_key") == market]
        market_wins = [b for b in market_bets if b.get("status") == "won"]
        if market_bets:
            by_market[market] = {
                "bets": len(market_bets),
                "win_rate": len(market_wins) / len(market_bets) * 100,
                "profit": sum(float(b.get("profit", 0)) for b in market_bets)
            }
    
    return {
        "total_bets": len(bets),
        "settled_bets": len(settled),
        "win_rate": win_rate,
        "roi": roi,
        "total_wagered": total_wagered,
        "total_profit": total_profit,
        "avg_bet_size": total_wagered / len(bets) if bets else 0,
        "by_sport": by_sport,
        "by_market": by_market
    }


def get_bets(table, pk: str, days: int) -> List[Dict]:
    """Get bets for a version from last N days"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    response = table.query(
        KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("BET#"),
        FilterExpression="placed_at > :cutoff",
        ExpressionAttributeValues={":cutoff": cutoff}
    )
    
    return response.get("Items", [])


def format_email(v1_metrics: Dict, v3_metrics: Dict, days: int) -> str:
    """Format HTML email comparing v1 and v3"""
    
    def format_sport_table(metrics: Dict) -> str:
        if not metrics["by_sport"]:
            return "<p>No data</p>"
        rows = ""
        for sport, data in metrics["by_sport"].items():
            rows += f"""
            <tr>
                <td>{sport}</td>
                <td>{data['bets']}</td>
                <td>{data['win_rate']:.1f}%</td>
                <td>${data['profit']:.2f}</td>
            </tr>"""
        return f"<table border='1' cellpadding='5'><tr><th>Sport</th><th>Bets</th><th>Win Rate</th><th>Profit</th></tr>{rows}</table>"
    
    def format_market_table(metrics: Dict) -> str:
        if not metrics["by_market"]:
            return "<p>No data</p>"
        rows = ""
        for market, data in metrics["by_market"].items():
            rows += f"""
            <tr>
                <td>{market}</td>
                <td>{data['bets']}</td>
                <td>{data['win_rate']:.1f}%</td>
                <td>${data['profit']:.2f}</td>
            </tr>"""
        return f"<table border='1' cellpadding='5'><tr><th>Market</th><th>Bets</th><th>Win Rate</th><th>Profit</th></tr>{rows}</table>"
    
    winner = "v3" if v3_metrics["roi"] > v1_metrics["roi"] else "v1"
    roi_diff = abs(v3_metrics["roi"] - v1_metrics["roi"])
    
    return f"""
    <html>
    <body>
        <h2>Benny A/B Test Report - Last {days} Days</h2>
        <p><strong>Winner: {winner.upper()}</strong> (ROI difference: {roi_diff:.2f}%)</p>
        
        <h3>Overall Performance</h3>
        <table border="1" cellpadding="10">
            <tr>
                <th>Metric</th>
                <th>v1 (Kelly + Full Prompts)</th>
                <th>v3 (Flat 2% + Lean Prompts)</th>
            </tr>
            <tr>
                <td>Total Bets</td>
                <td>{v1_metrics['total_bets']}</td>
                <td>{v3_metrics['total_bets']}</td>
            </tr>
            <tr>
                <td>Settled Bets</td>
                <td>{v1_metrics['settled_bets']}</td>
                <td>{v3_metrics['settled_bets']}</td>
            </tr>
            <tr>
                <td>Win Rate</td>
                <td>{v1_metrics['win_rate']:.1f}%</td>
                <td>{v3_metrics['win_rate']:.1f}%</td>
            </tr>
            <tr>
                <td>ROI</td>
                <td>{v1_metrics['roi']:.2f}%</td>
                <td>{v3_metrics['roi']:.2f}%</td>
            </tr>
            <tr>
                <td>Total Wagered</td>
                <td>${v1_metrics['total_wagered']:.2f}</td>
                <td>${v3_metrics['total_wagered']:.2f}</td>
            </tr>
            <tr>
                <td>Total Profit</td>
                <td>${v1_metrics['total_profit']:.2f}</td>
                <td>${v3_metrics['total_profit']:.2f}</td>
            </tr>
            <tr>
                <td>Avg Bet Size</td>
                <td>${v1_metrics['avg_bet_size']:.2f}</td>
                <td>${v3_metrics['avg_bet_size']:.2f}</td>
            </tr>
        </table>
        
        <h3>v1 Performance by Sport</h3>
        {format_sport_table(v1_metrics)}
        
        <h3>v3 Performance by Sport</h3>
        {format_sport_table(v3_metrics)}
        
        <h3>v1 Performance by Market</h3>
        {format_market_table(v1_metrics)}
        
        <h3>v3 Performance by Market</h3>
        {format_market_table(v3_metrics)}
        
        <p><em>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</em></p>
    </body>
    </html>
    """


def handler(event, context):
    """Lambda handler for daily A/B comparison report"""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    ses = boto3.client("ses", region_name="us-east-1")
    
    table_name = os.environ["BETS_TABLE"]
    table = dynamodb.Table(table_name)
    
    # Get bets for both versions (last 7 days)
    v1_bets = get_bets(table, "BENNY", 7)
    v3_bets = get_bets(table, "BENNY_V3", 7)
    
    # Calculate metrics
    v1_metrics = calculate_metrics(v1_bets)
    v3_metrics = calculate_metrics(v3_bets)
    
    # Format email
    email_body = format_email(v1_metrics, v3_metrics, 7)
    
    # Send email
    try:
        ses.send_email(
            Source="noreply@carpoolbets.com",
            Destination={"ToAddresses": ["glogankaranovich@gmail.com"]},
            Message={
                "Subject": {"Data": f"Benny A/B Test Report - {datetime.utcnow().strftime('%Y-%m-%d')}"},
                "Body": {"Html": {"Data": email_body}}
            }
        )
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise
    
    return {
        "statusCode": 200,
        "body": "A/B report sent"
    }
