"""
User Models and Custom Data API handler
"""

import csv
import io
import json
import os
import uuid
from typing import Any, Dict

import boto3

from api.utils import BaseAPIHandler, decimal_to_float
from api_middleware import check_feature_access, check_resource_limit
from custom_data import CustomDataset
from user_models import ModelPrediction, UserModel


class UserDataHandler(BaseAPIHandler):
    """Handler for user models and custom data endpoints"""

    def route_request(
        self,
        http_method: str,
        path: str,
        query_params: Dict[str, str],
        path_params: Dict[str, str],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route user data requests"""
        # User models endpoints
        if path == "/user-models" and http_method == "GET":
            return self.list_user_models(query_params)
        elif path == "/user-models" and http_method == "POST":
            return self.create_user_model(body)
        elif path == "/user-models/predictions" and http_method == "GET":
            return self.get_user_model_predictions(query_params)
        elif path_params.get("model_id"):
            model_id = path_params["model_id"]
            if "/backtests" in path and http_method == "GET":
                return self.list_backtests(model_id, query_params)
            elif "/backtests" in path and http_method == "POST":
                return self.create_backtest(model_id, body)
            elif "/performance" in path:
                return self.get_user_model_performance(model_id)
            elif http_method == "GET":
                return self.get_user_model(model_id, query_params)
            elif http_method == "PUT":
                return self.update_user_model(model_id, body)
            elif http_method == "DELETE":
                return self.delete_user_model(model_id, query_params)
        # Backtest by ID
        elif path.startswith("/backtests/") and http_method == "GET":
            backtest_id = path.split("/")[-1]
            return self.get_backtest(backtest_id, query_params)
        # Custom data endpoints
        elif path == "/custom-data" and http_method == "GET":
            return self.list_custom_data(query_params)
        elif path == "/custom-data/upload" and http_method == "POST":
            return self.upload_custom_data(body)
        elif path.startswith("/custom-data/") and http_method == "DELETE":
            dataset_id = path.split("/")[-1]
            return self.delete_custom_data(dataset_id, query_params)
        else:
            return self.error_response("Endpoint not found", 404)

    # User Models
    def list_user_models(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """List all models for a user"""
        try:

            user_id = query_params.get("user_id")
            if not user_id:
                return self.error_response("user_id parameter required")

            access_check = check_feature_access(user_id, "user_models")
            if not access_check["allowed"]:
                return self.error_response(access_check["error"], 403)

            models = UserModel.list_by_user(user_id)
            return self.success_response({"models": [decimal_to_float(m.to_dynamodb()) for m in models]})
        except Exception as e:
            return self.error_response(f"Error listing models: {str(e)}", 500)

    def create_user_model(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user model"""
        try:
            from user_models import validate_model_config

            user_id = body.get("user_id")
            if not user_id:
                return self.error_response("user_id is required")

            access_check = check_feature_access(user_id, "user_models")
            if not access_check["allowed"]:
                return self.error_response(access_check["error"], 403)

            current_models = len(UserModel.list_by_user(user_id))
            limit_check = check_resource_limit(user_id, "user_model", current_models)
            if not limit_check["allowed"]:
                return self.error_response(limit_check["error"], 403)

            required = ["name", "sport", "bet_types", "data_sources"]
            for field in required:
                if field not in body:
                    return self.error_response(f"Missing required field: {field}")

            is_valid, error = validate_model_config(body)
            if not is_valid:
                return self.error_response(error)

            model = UserModel(
                user_id=user_id,
                name=body["name"],
                description=body.get("description", ""),
                sport=body["sport"],
                bet_types=body["bet_types"],
                data_sources=body["data_sources"],
                min_confidence=body.get("min_confidence", 0.6),
                status=body.get("status", "active"),
                auto_adjust_weights=body.get("auto_adjust_weights", False),
            )
            model.save()

            return self.success_response({"message": "Model created successfully", "model": decimal_to_float(model.to_dynamodb())}, 201)
        except Exception as e:
            return self.error_response(f"Error creating model: {str(e)}", 500)

    def get_user_model(self, model_id: str, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get a specific user model"""
        try:
            user_id = query_params.get("user_id")
            if not user_id:
                return self.error_response("user_id parameter required")

            model = UserModel.get(user_id, model_id)
            if not model:
                return self.error_response("Model not found", 404)

            return self.success_response({"model": decimal_to_float(model.to_dynamodb())})
        except Exception as e:
            return self.error_response(f"Error fetching model: {str(e)}", 500)

    def update_user_model(self, model_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing user model"""
        try:
            from user_models import validate_model_config

            user_id = body.get("user_id")
            if not user_id:
                return self.error_response("user_id required in body")

            model = UserModel.get(user_id, model_id)
            if not model:
                return self.error_response("Model not found", 404)

            if "name" in body:
                model.name = body["name"]
            if "description" in body:
                model.description = body["description"]
            if "data_sources" in body:
                test_config = {"user_id": user_id, "name": model.name, "sport": model.sport, "bet_types": model.bet_types, "data_sources": body["data_sources"]}
                is_valid, error = validate_model_config(test_config)
                if not is_valid:
                    return self.error_response(error)
                model.data_sources = body["data_sources"]
            if "min_confidence" in body:
                model.min_confidence = body["min_confidence"]
            if "status" in body:
                model.status = body["status"]
            if "auto_adjust_weights" in body:
                model.auto_adjust_weights = body["auto_adjust_weights"]

            model.save()

            return self.success_response({"message": "Model updated successfully", "model": decimal_to_float(model.to_dynamodb())})
        except Exception as e:
            return self.error_response(f"Error updating model: {str(e)}", 500)

    def delete_user_model(self, model_id: str, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Delete a user model"""
        try:
            user_id = query_params.get("user_id")
            if not user_id:
                return self.error_response("user_id parameter required")

            model = UserModel.get(user_id, model_id)
            if not model:
                return self.error_response("Model not found", 404)

            model.delete()
            return self.success_response({"message": "Model deleted successfully"})
        except Exception as e:
            return self.error_response(f"Error deleting model: {str(e)}", 500)

    def create_backtest(self, model_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Create a backtest for a user model"""
        try:
            from backtest_engine import BacktestEngine

            user_id = body.get("user_id")
            start_date = body.get("start_date")
            end_date = body.get("end_date")

            if not all([user_id, start_date, end_date]):
                return self.error_response("user_id, start_date, and end_date required")

            model = UserModel.get(user_id, model_id)
            if not model:
                return self.error_response("Model not found", 404)

            engine = BacktestEngine()
            result = engine.run_backtest(user_id, model_id, model.to_dynamodb(), start_date, end_date)

            return self.success_response(decimal_to_float(result))
        except Exception as e:
            return self.error_response(f"Error creating backtest: {str(e)}", 500)

    def list_backtests(self, model_id: str, query_params: Dict[str, str]) -> Dict[str, Any]:
        """List backtests for a model"""
        try:
            from backtest_engine import BacktestEngine

            backtests = BacktestEngine.list_backtests(model_id)
            return self.success_response({"backtests": decimal_to_float(backtests)})
        except Exception as e:
            return self.error_response(f"Error listing backtests: {str(e)}", 500)

    def get_backtest(self, backtest_id: str, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get a specific backtest"""
        try:
            from backtest_engine import BacktestEngine

            user_id = query_params.get("user_id")
            if not user_id:
                return self.error_response("user_id parameter required")

            backtest = BacktestEngine.get_backtest(user_id, backtest_id)
            if not backtest:
                return self.error_response("Backtest not found", 404)

            return self.success_response(decimal_to_float(backtest))
        except Exception as e:
            return self.error_response(f"Error getting backtest: {str(e)}", 500)

    def get_user_model_performance(self, model_id: str) -> Dict[str, Any]:
        """Get performance metrics for a user model"""
        try:
            performance = ModelPrediction.get_performance(model_id)
            return self.success_response({"model_id": model_id, "performance": decimal_to_float(performance)})
        except Exception as e:
            return self.error_response(f"Error fetching model performance: {str(e)}", 500)

    def get_user_model_predictions(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get predictions for user's models"""
        try:
            user_id = query_params.get("user_id")
            if not user_id:
                return self.error_response("user_id is required")

            models = UserModel.list_by_user(user_id)

            all_predictions = []
            for model in models:
                predictions = ModelPrediction.list_by_model(model.model_id, limit=50)
                for pred in predictions:
                    all_predictions.append({
                        "model_id": pred.model_id,
                        "model_name": model.name,
                        "game_id": pred.game_id,
                        "sport": pred.sport,
                        "prediction": pred.prediction,
                        "confidence": pred.confidence,
                        "reasoning": pred.reasoning,
                        "bet_type": pred.bet_type,
                        "home_team": pred.home_team,
                        "away_team": pred.away_team,
                        "commence_time": pred.commence_time,
                        "outcome": pred.outcome,
                        "created_at": pred.created_at,
                    })

            return self.success_response({"predictions": decimal_to_float(all_predictions)})
        except Exception as e:
            return self.error_response(f"Error fetching predictions: {str(e)}", 500)

    # Custom Data
    def list_custom_data(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """List user's custom datasets"""
        try:

            user_id = query_params.get("user_id")
            if not user_id:
                return self.error_response("user_id is required")

            access = check_feature_access(user_id, "custom_data")
            if not access["allowed"]:
                return self.error_response(access["error"], 403)

            datasets = CustomDataset.list_by_user(user_id)

            return self.success_response({
                "datasets": [{
                    "dataset_id": d.dataset_id,
                    "name": d.name,
                    "description": d.description,
                    "sport": d.sport,
                    "data_type": d.data_type,
                    "columns": d.columns,
                    "row_count": d.row_count,
                    "created_at": d.created_at,
                } for d in datasets]
            })
        except Exception as e:
            return self.error_response(f"Error listing datasets: {str(e)}", 500)

    def upload_custom_data(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Upload custom dataset"""
        try:

            required = ["user_id", "name", "sport", "data_type", "data"]
            for field in required:
                if field not in body:
                    return self.error_response(f"Missing required field: {field}")

            user_id = body["user_id"]

            access = check_feature_access(user_id, "custom_data")
            if not access["allowed"]:
                return self.error_response(access["error"], 403)

            current_datasets = CustomDataset.list_by_user(user_id)
            limit_check = check_resource_limit(user_id, "dataset", len(current_datasets))
            if not limit_check["allowed"]:
                return self.error_response(limit_check["error"], 403)

            name = body["name"]
            description = body.get("description", "")
            sport = body["sport"]
            data_type = body["data_type"]

            data_str = body["data"]
            file_format = body.get("format", "csv")

            if file_format == "csv":
                csv_reader = csv.DictReader(io.StringIO(data_str))
                data = list(csv_reader)
            else:
                data = json.loads(data_str)

            is_valid, error = validate_dataset(data, data_type)
            if not is_valid:
                return self.error_response(error)

            dataset = CustomDataset(
                user_id=user_id,
                name=name,
                description=description,
                sport=sport,
                data_type=data_type,
                columns=list(data[0].keys()),
                s3_key=f"{user_id}/{uuid.uuid4().hex}.json",
                row_count=len(data),
            )

            s3 = boto3.client("s3", region_name="us-east-1")
            bucket = os.environ.get("CUSTOM_DATA_BUCKET", "dev-custom-data-bucket")
            s3.put_object(Bucket=bucket, Key=dataset.s3_key, Body=json.dumps(data).encode("utf-8"))

            dataset.save()

            return self.success_response({"message": "Dataset uploaded successfully", "dataset": {"dataset_id": dataset.dataset_id, "name": dataset.name, "row_count": dataset.row_count}}, 201)
        except Exception as e:
            return self.error_response(f"Error uploading dataset: {str(e)}", 500)

    def delete_custom_data(self, dataset_id: str, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Delete custom dataset"""
        try:

            user_id = query_params.get("user_id")
            if not user_id:
                return self.error_response("user_id is required")

            access = check_feature_access(user_id, "custom_data")
            if not access["allowed"]:
                return self.error_response(access["error"], 403)

            dataset = CustomDataset.get(user_id, dataset_id)
            if not dataset:
                return self.error_response("Dataset not found", 404)

            dataset.delete()

            return self.success_response({"message": "Dataset deleted successfully"})
        except Exception as e:
            return self.error_response(f"Error deleting dataset: {str(e)}", 500)


# Lambda handler entry point
handler = UserDataHandler()
lambda_handler = handler.lambda_handler

# Backward compatibility functions for tests
def handle_list_user_models(query_params: Dict[str, str]):
    return handler.list_user_models(query_params)

def handle_create_user_model(body: Dict[str, Any]):
    return handler.create_user_model(body)

def handle_get_user_model(model_id: str, query_params: Dict[str, str]):
    return handler.get_user_model(model_id, query_params)

def handle_update_user_model(model_id: str, body: Dict[str, Any]):
    return handler.update_user_model(model_id, body)

def handle_delete_user_model(model_id: str, query_params: Dict[str, str]):
    return handler.delete_user_model(model_id, query_params)

def handle_get_user_model_performance(model_id: str):
    return handler.get_user_model_performance(model_id)

def handle_get_user_model_predictions(query_params: Dict[str, str]):
    return handler.get_user_model_predictions(query_params)

def handle_list_custom_data(query_params: Dict[str, str]):
    return handler.list_custom_data(query_params)

def handle_upload_custom_data(body: Dict[str, Any]):
    return handler.upload_custom_data(body)

def handle_delete_custom_data(dataset_id: str, query_params: Dict[str, str]):
    return handler.delete_custom_data(dataset_id, query_params)
