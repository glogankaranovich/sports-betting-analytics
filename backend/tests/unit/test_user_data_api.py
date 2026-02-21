import os
import unittest
from unittest.mock import MagicMock, patch, Mock
from api.user_data import UserDataHandler


class TestUserDataHandler(unittest.TestCase):
    def setUp(self):
        os.environ["DYNAMODB_TABLE"] = "test-table"

    @patch("api.utils.table")
    def test_route_list_user_models(self, mock_table):
        """Test routing to list user models"""
        handler = UserDataHandler()
        
        with patch.object(handler, "list_user_models") as mock_list:
            mock_list.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "GET", "/user-models", {"user_id": "user123"}, {}, {}
            )
            
            mock_list.assert_called_once_with({"user_id": "user123"})

    @patch("api.utils.table")
    def test_route_create_user_model(self, mock_table):
        """Test routing to create user model"""
        handler = UserDataHandler()
        
        with patch.object(handler, "create_user_model") as mock_create:
            mock_create.return_value = {"statusCode": 200}
            
            body = {"user_id": "user123", "name": "My Model"}
            result = handler.route_request("POST", "/user-models", {}, {}, body)
            
            mock_create.assert_called_once_with(body)

    @patch("api.utils.table")
    def test_route_get_user_model(self, mock_table):
        """Test routing to get user model"""
        handler = UserDataHandler()
        
        with patch.object(handler, "get_user_model") as mock_get:
            mock_get.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "GET", "/user-models/model123", {}, {"model_id": "model123"}, {}
            )
            
            mock_get.assert_called_once_with("model123", {})

    @patch("api.utils.table")
    def test_route_list_custom_data(self, mock_table):
        """Test routing to list custom data"""
        handler = UserDataHandler()
        
        with patch.object(handler, "list_custom_data") as mock_list:
            mock_list.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "GET", "/custom-data", {"user_id": "user123"}, {}, {}
            )
            
            mock_list.assert_called_once_with({"user_id": "user123"})

    @patch("api.utils.table")
    @patch("api.user_data.check_feature_access")
    @patch("api.user_data.UserModel")
    def test_list_user_models(self, mock_user_model, mock_access, mock_table):
        """Test listing user models"""
        mock_access.return_value = {"allowed": True}
        
        mock_model = Mock()
        mock_model.to_dynamodb.return_value = {"model_id": "model123"}
        mock_user_model.list_by_user.return_value = [mock_model]
        
        handler = UserDataHandler()
        result = handler.list_user_models({"user_id": "user123"})
        
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("models", result["body"])

    @patch("api.utils.table")
    @patch("api.user_data.check_feature_access")
    def test_list_user_models_no_access(self, mock_access, mock_table):
        """Test listing user models without access"""
        mock_access.return_value = {"allowed": False, "error": "No access"}
        
        handler = UserDataHandler()
        result = handler.list_user_models({"user_id": "user123"})
        
        self.assertEqual(result["statusCode"], 403)

    @patch("api.utils.table")
    def test_list_user_models_missing_user_id(self, mock_table):
        """Test listing user models without user_id"""
        handler = UserDataHandler()
        result = handler.list_user_models({})
        
        self.assertEqual(result["statusCode"], 400)

    @patch("api.utils.table")
    @patch("api.user_data.check_feature_access")
    @patch("api.user_data.CustomDataset")
    def test_list_custom_data(self, mock_dataset, mock_access, mock_table):
        """Test listing custom data"""
        mock_access.return_value = {"allowed": True}
        
        mock_ds = Mock()
        mock_ds.dataset_id = "ds123"
        mock_ds.name = "Test Dataset"
        mock_ds.description = "Test"
        mock_ds.sport = "basketball_nba"
        mock_ds.data_type = "player_stats"
        mock_ds.columns = ["col1"]
        mock_ds.row_count = 10
        mock_ds.created_at = "2026-01-01"
        mock_ds.updated_at = "2026-01-01"
        
        mock_dataset.list_by_user.return_value = [mock_ds]
        
        handler = UserDataHandler()
        result = handler.list_custom_data({"user_id": "user123"})
        
        self.assertEqual(result["statusCode"], 200)

    @patch("api.utils.table")
    def test_route_not_found(self, mock_table):
        """Test routing to non-existent endpoint"""
        handler = UserDataHandler()
        result = handler.route_request("GET", "/invalid", {}, {}, {})
        
        self.assertEqual(result["statusCode"], 404)

    @patch("api.utils.table")
    def test_route_update_user_model(self, mock_table):
        """Test routing to update user model"""
        handler = UserDataHandler()
        
        with patch.object(handler, "update_user_model") as mock_update:
            mock_update.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "PUT", "/user-models/model123", {}, {"model_id": "model123"}, {"name": "Updated"}
            )
            
            mock_update.assert_called_once_with("model123", {"name": "Updated"})

    @patch("api.utils.table")
    def test_route_delete_user_model(self, mock_table):
        """Test routing to delete user model"""
        handler = UserDataHandler()
        
        with patch.object(handler, "delete_user_model") as mock_delete:
            mock_delete.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "DELETE", "/user-models/model123", {}, {"model_id": "model123"}, {}
            )
            
            mock_delete.assert_called_once_with("model123", {})

    @patch("api.utils.table")
    def test_route_create_backtest(self, mock_table):
        """Test routing to create backtest"""
        handler = UserDataHandler()
        
        with patch.object(handler, "create_backtest") as mock_create:
            mock_create.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "POST", "/user-models/model123/backtests", {}, {"model_id": "model123"}, {"days": 30}
            )
            
            mock_create.assert_called_once_with("model123", {"days": 30})

    @patch("api.utils.table")
    def test_route_list_backtests(self, mock_table):
        """Test routing to list backtests"""
        handler = UserDataHandler()
        
        with patch.object(handler, "list_backtests") as mock_list:
            mock_list.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "GET", "/user-models/model123/backtests", {}, {"model_id": "model123"}, {}
            )
            
            mock_list.assert_called_once()

    @patch("api.utils.table")
    def test_route_get_backtest(self, mock_table):
        """Test routing to get backtest by ID"""
        handler = UserDataHandler()
        
        with patch.object(handler, "get_backtest") as mock_get:
            mock_get.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "GET", "/backtests/bt123", {}, {}, {}
            )
            
            mock_get.assert_called_once()

    @patch("api.utils.table")
    def test_route_upload_custom_data(self, mock_table):
        """Test routing to upload custom data"""
        handler = UserDataHandler()
        
        with patch.object(handler, "upload_custom_data") as mock_upload:
            mock_upload.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "POST", "/custom-data/upload", {}, {}, {"data": "test"}
            )
            
            mock_upload.assert_called_once()

    @patch("api.utils.table")
    def test_route_delete_custom_data(self, mock_table):
        """Test routing to delete custom data"""
        handler = UserDataHandler()
        
        with patch.object(handler, "delete_custom_data") as mock_delete:
            mock_delete.return_value = {"statusCode": 200}
            
            result = handler.route_request(
                "DELETE", "/custom-data/ds123", {}, {}, {}
            )
            
            mock_delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
