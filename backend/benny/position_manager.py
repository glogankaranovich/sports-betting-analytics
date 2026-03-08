"""Position management for Benny - handles cash-out and double-down decisions"""
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os
import boto3
from boto3.dynamodb.conditions import Key


class PositionManager:
    """Manages existing bet positions - cash-out and double-down logic"""
    
    def __init__(self, table, bedrock_client):
        self.table = table
        self.bedrock = bedrock_client
        self.sqs = boto3.client('sqs')
        self.notification_queue_url = os.environ.get('NOTIFICATION_QUEUE_URL')
    
    def evaluate_pending_bets(self) -> List[Dict[str, Any]]:
        """Evaluate existing pending bets for cash-out or double-down opportunities"""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq("BENNY") & Key("sk").begins_with("BET#"),
                FilterExpression="#status = :pending",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":pending": "pending"}
            )
            
            pending_bets = response.get("Items", [])
            print(f"Evaluating {len(pending_bets)} pending bets")
            
            evaluations = []
            for bet in pending_bets:
                evaluation = self._evaluate_single_bet(bet)
                if evaluation:
                    evaluations.append(evaluation)
            
            return evaluations
        except Exception as e:
            print(f"Error evaluating pending bets: {e}")
            return []
    
    def _evaluate_single_bet(self, bet: Dict) -> Optional[Dict]:
        """Evaluate a single bet for position management"""
        game_id = bet.get("game_id")
        market_key = bet.get("market_key")
        original_odds = float(bet.get("odds", 0))
        original_confidence = float(bet.get("confidence", 0))
        
        # Get current odds
        current_odds = self._get_current_odds(game_id, market_key, bet.get("prediction"))
        if not current_odds:
            return None
        
        # Re-analyze with current data
        current_analysis = self._reanalyze_bet(bet)
        if not current_analysis:
            return None
        
        current_confidence = current_analysis.get("confidence", original_confidence)
        
        # Calculate changes
        odds_change = ((current_odds - original_odds) / abs(original_odds)) if original_odds else 0
        confidence_change = current_confidence - original_confidence
        
        return {
            "bet": bet,
            "original_odds": original_odds,
            "current_odds": current_odds,
            "odds_change": odds_change,
            "original_confidence": original_confidence,
            "current_confidence": current_confidence,
            "confidence_change": confidence_change,
            "current_reasoning": current_analysis.get("reasoning", "")
        }
    
    def should_cash_out(self, evaluation: Dict) -> tuple[bool, str]:
        """Determine if bet should be cashed out early"""
        confidence_change = evaluation["confidence_change"]
        odds_change = evaluation["odds_change"]
        
        # Cash out if confidence dropped significantly
        if confidence_change < -0.15:  # Lost 15%+ confidence
            return True, f"Confidence dropped {abs(confidence_change):.1%}"
        
        # Cash out if odds moved against us significantly (worse payout)
        if odds_change < -0.20:  # Odds worsened by 20%+
            return True, f"Odds worsened {abs(odds_change):.1%}"
        
        return False, ""
    
    def should_double_down(self, evaluation: Dict, bankroll: Decimal) -> tuple[bool, str, Decimal]:
        """Determine if should increase position size"""
        confidence_change = evaluation["confidence_change"]
        odds_change = evaluation["odds_change"]
        current_confidence = evaluation["current_confidence"]
        
        # Double down if confidence increased significantly AND still high
        if confidence_change > 0.10 and current_confidence > 0.75:
            # Calculate additional bet size (same as original)
            original_stake = Decimal(str(evaluation["bet"]["bet_amount"]))
            additional_stake = min(original_stake, bankroll * Decimal("0.10"))  # Max 10% of bankroll
            
            if additional_stake >= Decimal("5.00"):
                return True, f"Confidence increased {confidence_change:.1%}", additional_stake
        
        return False, "", Decimal("0")
    
    def execute_cash_out(self, bet: Dict, reason: str) -> Dict:
        """Execute cash-out of a bet"""
        bet_id = bet["bet_id"]
        original_stake = Decimal(str(bet["bet_amount"]))
        
        # Calculate cash-out value (typically 70-90% of original stake)
        cash_out_value = original_stake * Decimal("0.80")
        
        # Update bet status
        self.table.update_item(
            Key={"pk": "BENNY", "sk": bet_id},
            UpdateExpression="SET #status = :cashed_out, cash_out_value = :value, cash_out_reason = :reason, cash_out_at = :timestamp",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":cashed_out": "cashed_out",
                ":value": cash_out_value,
                ":reason": reason,
                ":timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Record cash-out decision for post-game evaluation
        self.table.put_item(Item={
            "pk": "BENNY#CASHOUT",
            "sk": f"{bet_id}#{datetime.utcnow().isoformat()}",
            "bet_id": bet_id,
            "game_id": bet["game_id"],
            "original_stake": original_stake,
            "cash_out_value": cash_out_value,
            "reason": reason,
            "original_prediction": bet["prediction"],
            "cashed_out_at": datetime.utcnow().isoformat()
        })
        
        # Send notification
        self._send_notification('cash_out', bet, {
            'cash_out_value': float(cash_out_value),
            'reason': reason
        })
        
        return {
            "success": True,
            "cash_out_value": float(cash_out_value),
            "reason": reason
        }
    
    def _send_notification(self, notification_type: str, bet: Dict, details: Dict):
        """Send notification for position action"""
        environment = os.environ.get('ENVIRONMENT', 'dev')
        if environment != 'dev' or not self.notification_queue_url:
            return
        
        message = {
            'type': notification_type,
            'data': {
                'game': f"{bet.get('away_team')} @ {bet.get('home_team')}",
                'prediction': bet.get('prediction'),
                'original_stake': float(bet.get('bet_amount', 0)),
                **details
            }
        }
        
        try:
            self.sqs.send_message(
                QueueUrl=self.notification_queue_url,
                MessageBody=json.dumps(message)
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")
    
    def execute_double_down(self, bet: Dict, additional_stake: Decimal, reason: str) -> Dict:
        """Execute double-down on a bet"""
        bet_id = bet["bet_id"]
        
        # Create new bet entry for the additional stake
        double_down_id = f"BET#{datetime.utcnow().isoformat()}#{bet['game_id']}_DD"
        
        self.table.put_item(Item={
            "pk": "BENNY",
            "sk": double_down_id,
            "bet_id": double_down_id,
            "original_bet_id": bet_id,
            "game_id": bet["game_id"],
            "sport": bet["sport"],
            "home_team": bet["home_team"],
            "away_team": bet["away_team"],
            "prediction": bet["prediction"],
            "confidence": bet["confidence"],
            "bet_amount": additional_stake,
            "market_key": bet["market_key"],
            "commence_time": bet["commence_time"],
            "placed_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "is_double_down": True,
            "double_down_reason": reason
        })
        
        # Send notification
        self._send_notification('double_down', bet, {
            'additional_stake': float(additional_stake),
            'reason': reason
        })
        
        return {
            "success": True,
            "additional_stake": float(additional_stake),
            "reason": reason
        }
    
    def evaluate_cash_out_correctness(self, game_id: str) -> Dict:
        """Post-game evaluation: was cash-out decision correct?"""
        try:
            # Get cash-out decisions for this game
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq("BENNY#CASHOUT") & Key("sk").begins_with(f"BET#"),
                FilterExpression="game_id = :gid",
                ExpressionAttributeValues={":gid": game_id}
            )
            
            cash_outs = response.get("Items", [])
            if not cash_outs:
                return {}
            
            # Get actual game outcome
            outcome = self._get_game_outcome(game_id)
            if not outcome:
                return {}
            
            evaluations = []
            for cash_out in cash_outs:
                original_bet_id = cash_out["bet_id"]
                
                # Get original bet
                bet_response = self.table.get_item(Key={"pk": "BENNY", "sk": original_bet_id})
                bet = bet_response.get("Item")
                if not bet:
                    continue
                
                # Would the bet have won?
                would_have_won = self._check_if_would_win(bet, outcome)
                
                # Calculate what would have happened
                original_stake = Decimal(str(cash_out["original_stake"]))
                cash_out_value = Decimal(str(cash_out["cash_out_value"]))
                
                if would_have_won:
                    # Calculate what payout would have been
                    odds = float(bet.get("odds", 0))
                    if odds > 0:
                        payout = original_stake * (1 + Decimal(str(odds / 100)))
                    else:
                        payout = original_stake * (1 + Decimal(str(100 / abs(odds))))
                    
                    profit_if_held = payout - original_stake
                    profit_from_cashout = cash_out_value - original_stake
                    decision_cost = profit_if_held - profit_from_cashout
                    
                    correct = False  # Cashed out a winner
                else:
                    # Would have lost
                    loss_if_held = original_stake
                    profit_from_cashout = cash_out_value - original_stake
                    decision_value = profit_from_cashout + loss_if_held
                    
                    correct = True  # Correctly cashed out a loser
                
                evaluations.append({
                    "bet_id": original_bet_id,
                    "correct_decision": correct,
                    "would_have_won": would_have_won,
                    "decision_value": float(decision_value) if not would_have_won else float(-decision_cost)
                })
                
                # Store evaluation
                self.table.update_item(
                    Key={"pk": "BENNY#CASHOUT", "sk": cash_out["sk"]},
                    UpdateExpression="SET correct_decision = :correct, would_have_won = :won, decision_value = :value",
                    ExpressionAttributeValues={
                        ":correct": correct,
                        ":won": would_have_won,
                        ":value": Decimal(str(decision_value)) if not would_have_won else Decimal(str(-decision_cost))
                    }
                )
            
            return {"evaluations": evaluations}
        except Exception as e:
            print(f"Error evaluating cash-out correctness: {e}")
            return {}
    
    def _get_current_odds(self, game_id: str, market_key: str, prediction: str) -> Optional[float]:
        """Get current odds for a specific bet"""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(f"GAME#{game_id}"),
                FilterExpression="market_key = :mk AND latest = :true",
                ExpressionAttributeValues={":mk": market_key, ":true": True}
            )
            
            odds_items = response.get("Items", [])
            if not odds_items:
                return None
            
            for item in odds_items:
                outcomes = item.get("outcomes", [])
                for outcome in outcomes:
                    if prediction.lower() in outcome.get("name", "").lower():
                        return float(outcome.get("price", 0))
            
            return None
        except Exception as e:
            print(f"Error getting current odds: {e}")
            return None
    
    def _reanalyze_bet(self, bet: Dict) -> Optional[Dict]:
        """Re-analyze a bet with current data"""
        try:
            prompt = f"""Re-evaluate this pending bet:

Original: {bet.get('prediction')} at {bet.get('confidence'):.0%} confidence
Reasoning: {bet.get('ai_reasoning')}

Has anything changed? Respond with JSON:
{{"confidence": 0.70, "reasoning": "Brief update"}}"""

            response = self.bedrock.invoke_model(
                modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response["body"].read())
            content = result["content"][0]["text"]
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"Error re-analyzing bet: {e}")
            return None
    
    def _get_game_outcome(self, game_id: str) -> Optional[Dict]:
        """Get actual game outcome"""
        try:
            response = self.table.get_item(Key={"pk": f"GAME#{game_id}", "sk": "OUTCOME"})
            return response.get("Item")
        except:
            return None
    
    def _check_if_would_win(self, bet: Dict, outcome: Dict) -> bool:
        """Check if bet would have won based on outcome"""
        prediction = bet.get("prediction", "").lower()
        winner = outcome.get("winner", "").lower()
        
        # Simple check - can be enhanced
        return winner in prediction
