"""
Backtesting engine for user models

Replays historical games to evaluate model performance
"""
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

from user_model_executor import (
    evaluate_head_to_head,
    evaluate_odds_movement,
    evaluate_recent_form,
    evaluate_rest_schedule,
    evaluate_team_stats,
)

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE", "carpool-bets-v2-dev"))


class BacktestEngine:
    """Engine for backtesting user models against historical data"""

    def __init__(self):
        self.evaluators = {
            "team_stats": evaluate_team_stats,
            "odds_movement": evaluate_odds_movement,
            "recent_form": evaluate_recent_form,
            "rest_schedule": evaluate_rest_schedule,
            "head_to_head": evaluate_head_to_head,
        }

    def run_backtest(
        self,
        user_id: str,
        model_id: str,
        model_config: Dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Run backtest for a model over a date range"""
        backtest_id = str(uuid.uuid4())

        # Fetch historical games
        games = self._fetch_historical_games(
            model_config["sport"], start_date, end_date
        )

        # Run model on each game
        predictions = []
        for game in games:
            prediction = self._evaluate_game(game, model_config)
            if prediction:
                predictions.append(prediction)

        # Calculate metrics
        metrics = self._calculate_metrics(predictions)

        # Store results
        result = {
            "backtest_id": backtest_id,
            "user_id": user_id,
            "model_id": model_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_predictions": len(predictions),
            "metrics": metrics,
            "predictions": predictions[:100],  # Store first 100
            "created_at": datetime.utcnow().isoformat(),
        }

        self._store_backtest(result)
        return result

    def _fetch_historical_games(
        self, sport: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Fetch historical games with outcomes"""
        response = table.query(
            IndexName="AnalysisTimeGSI",
            KeyConditionExpression=Key("analysis_time_pk").eq(f"HISTORICAL#{sport}")
            & Key("commence_time").between(start_date, end_date),
        )

        # Group by game_id
        games_dict = {}
        for item in response.get("Items", []):
            game_id = item.get("game_id")
            if game_id not in games_dict:
                games_dict[game_id] = {
                    "game_id": game_id,
                    "sport": item.get("sport"),
                    "home_team": item.get("home_team"),
                    "away_team": item.get("away_team"),
                    "commence_time": item.get("commence_time"),
                    "odds": [],
                    "outcome": None,
                }

            if item.get("sk") == "OUTCOME":
                games_dict[game_id]["outcome"] = item
            else:
                games_dict[game_id]["odds"].append(item)

        # Only return games with outcomes
        return [g for g in games_dict.values() if g["outcome"]]

    def _evaluate_game(
        self, game: Dict[str, Any], model_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single game using model config"""
        try:
            scores = {}
            data_sources = model_config.get("data_sources", {})

            # Evaluate each enabled data source
            for source_name, source_config in data_sources.items():
                if not source_config.get("enabled", False):
                    continue

                evaluator = self.evaluators.get(source_name)
                if not evaluator:
                    continue

                score = evaluator(game)
                weight = source_config.get("weight", 0)
                scores[source_name] = score * weight

            # Calculate final score
            total_score = sum(scores.values())
            confidence = min(abs(total_score), 1.0)

            # Make prediction
            prediction = "home" if total_score > 0 else "away"
            predicted_team = (
                game.get("home_team") if prediction == "home" else game.get("away_team")
            )

            # Check if prediction was correct
            outcome = game.get("outcome", {})
            actual_winner = outcome.get("winner")
            correct = predicted_team == actual_winner

            return {
                "game_id": game.get("game_id"),
                "home_team": game.get("home_team"),
                "away_team": game.get("away_team"),
                "commence_time": game.get("commence_time"),
                "prediction": predicted_team,
                "confidence": confidence,
                "actual_winner": actual_winner,
                "correct": correct,
                "scores": scores,
            }

        except Exception as e:
            print(f"Error evaluating game: {e}")
            return None

    def _calculate_metrics(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if not predictions:
            return {
                "accuracy": 0,
                "total_predictions": 0,
                "correct_predictions": 0,
                "roi": 0,
                "avg_confidence": 0,
            }

        correct = sum(1 for p in predictions if p.get("correct"))
        total = len(predictions)
        accuracy = correct / total if total > 0 else 0

        # Calculate ROI (assuming -110 odds)
        total_bet = total * 100
        total_return = correct * 190.91  # Win $90.91 per $100 bet at -110
        roi = ((total_return - total_bet) / total_bet) if total_bet > 0 else 0

        avg_confidence = (
            sum(p.get("confidence", 0) for p in predictions) / total if total > 0 else 0
        )

        return {
            "accuracy": round(accuracy, 4),
            "total_predictions": total,
            "correct_predictions": correct,
            "roi": round(roi, 4),
            "avg_confidence": round(avg_confidence, 4),
        }

    def _store_backtest(self, result: Dict[str, Any]):
        """Store backtest results in DynamoDB"""
        item = {
            "PK": f"USER#{result['user_id']}",
            "SK": f"BACKTEST#{result['backtest_id']}",
            "GSI1PK": f"MODEL#{result['model_id']}",
            "GSI1SK": result["created_at"],
            "backtest_id": result["backtest_id"],
            "model_id": result["model_id"],
            "start_date": result["start_date"],
            "end_date": result["end_date"],
            "total_predictions": result["total_predictions"],
            "metrics": result["metrics"],
            "predictions": result["predictions"],
            "created_at": result["created_at"],
        }

        table.put_item(Item=item)

    @staticmethod
    def get_backtest(user_id: str, backtest_id: str) -> Optional[Dict[str, Any]]:
        """Get backtest results"""
        response = table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": f"BACKTEST#{backtest_id}"}
        )
        return response.get("Item")

    @staticmethod
    def list_backtests(model_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List backtests for a model"""
        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"MODEL#{model_id}"),
            ScanIndexForward=False,
            Limit=limit,
        )
        return response.get("Items", [])


def lambda_handler(event, context):
    """Lambda handler for backtest execution"""
    try:
        body = json.loads(event.get("body", "{}"))

        user_id = body.get("user_id")
        model_id = body.get("model_id")
        model_config = body.get("model_config")
        start_date = body.get("start_date")
        end_date = body.get("end_date")

        if not all([user_id, model_id, model_config, start_date, end_date]):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required parameters"}),
            }

        engine = BacktestEngine()
        result = engine.run_backtest(
            user_id, model_id, model_config, start_date, end_date
        )

        return {
            "statusCode": 200,
            "body": json.dumps(result, default=str),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
