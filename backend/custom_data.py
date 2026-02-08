"""
Custom Data - User-uploaded datasets for custom model data sources
"""
import json
import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
s3 = boto3.client("s3", region_name="us-east-1")

CUSTOM_DATA_TABLE = os.environ.get("CUSTOM_DATA_TABLE", "Dev-CustomData")
CUSTOM_DATA_BUCKET = os.environ.get("CUSTOM_DATA_BUCKET", "dev-custom-data-bucket")

custom_data_table = dynamodb.Table(CUSTOM_DATA_TABLE)


def convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert floats to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj


class CustomDataset:
    """User-uploaded custom dataset"""

    def __init__(
        self,
        user_id: str,
        name: str,
        description: str,
        sport: str,
        data_type: str,  # 'team' or 'player'
        columns: List[str],
        s3_key: str,
        row_count: int,
        dataset_id: Optional[str] = None,
        allow_benny_access: bool = False,
        created_at: Optional[str] = None,
    ):
        self.dataset_id = dataset_id or f"dataset_{uuid.uuid4().hex[:12]}"
        self.user_id = user_id
        self.name = name
        self.description = description
        self.sport = sport
        self.data_type = data_type
        self.columns = columns
        self.s3_key = s3_key
        self.row_count = row_count
        self.allow_benny_access = allow_benny_access
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dynamodb(self) -> Dict:
        """Convert to DynamoDB item"""
        return {
            "PK": f"USER#{self.user_id}",
            "SK": f"DATASET#{self.dataset_id}",
            "GSI1PK": f"SPORT#{self.sport}",
            "GSI1SK": f"CREATED#{self.created_at}",
            "dataset_id": self.dataset_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "sport": self.sport,
            "data_type": self.data_type,
            "columns": self.columns,
            "s3_key": self.s3_key,
            "row_count": self.row_count,
            "allow_benny_access": self.allow_benny_access,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dynamodb(cls, item: Dict) -> "CustomDataset":
        """Create from DynamoDB item"""
        return cls(
            dataset_id=item["dataset_id"],
            user_id=item["user_id"],
            name=item["name"],
            description=item["description"],
            sport=item["sport"],
            data_type=item["data_type"],
            columns=item["columns"],
            s3_key=item["s3_key"],
            row_count=item["row_count"],
            allow_benny_access=item.get("allow_benny_access", False),
            created_at=item["created_at"],
        )

    def save(self):
        """Save dataset metadata to DynamoDB"""
        custom_data_table.put_item(Item=self.to_dynamodb())

    @staticmethod
    def get(user_id: str, dataset_id: str) -> Optional["CustomDataset"]:
        """Get dataset by ID"""
        response = custom_data_table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": f"DATASET#{dataset_id}"}
        )
        item = response.get("Item")
        return CustomDataset.from_dynamodb(item) if item else None

    @staticmethod
    def list_by_user(user_id: str, limit: int = 50) -> List["CustomDataset"]:
        """List all datasets for a user"""
        response = custom_data_table.query(
            KeyConditionExpression=Key("PK").eq(f"USER#{user_id}")
            & Key("SK").begins_with("DATASET#"),
            ScanIndexForward=False,  # Most recent first
            Limit=limit,
        )
        return [CustomDataset.from_dynamodb(item) for item in response.get("Items", [])]

    @staticmethod
    def list_benny_accessible(
        sport: str = None, limit: int = 100
    ) -> List["CustomDataset"]:
        """List all datasets that allow Benny access"""
        scan_params = {
            "FilterExpression": "allow_benny_access = :true AND begins_with(SK, :prefix)",
            "ExpressionAttributeValues": {":true": True, ":prefix": "DATASET#"},
            "Limit": limit,
        }

        if sport:
            scan_params["FilterExpression"] += " AND sport = :sport"
            scan_params["ExpressionAttributeValues"][":sport"] = sport

        response = custom_data_table.scan(**scan_params)
        return [CustomDataset.from_dynamodb(item) for item in response.get("Items", [])]

    def delete(self):
        """Delete dataset metadata and S3 file"""
        # Delete from DynamoDB
        custom_data_table.delete_item(
            Key={"PK": f"USER#{self.user_id}", "SK": f"DATASET#{self.dataset_id}"}
        )
        # Delete from S3
        try:
            s3.delete_object(Bucket=CUSTOM_DATA_BUCKET, Key=self.s3_key)
        except Exception as e:
            print(f"Error deleting S3 object: {e}")

    def get_data(self) -> List[Dict]:
        """Retrieve dataset from S3"""
        try:
            response = s3.get_object(Bucket=CUSTOM_DATA_BUCKET, Key=self.s3_key)
            data = json.loads(response["Body"].read().decode("utf-8"))
            return data
        except Exception as e:
            print(f"Error retrieving dataset from S3: {e}")
            return []


def validate_dataset(data: List[Dict], data_type: str) -> tuple[bool, Optional[str]]:
    """Validate dataset structure and content"""
    if not data or len(data) == 0:
        return False, "Dataset is empty"

    if len(data) > 10000:
        return False, "Dataset too large (max 10,000 rows)"

    # Check all rows have same columns
    first_row_keys = set(data[0].keys())
    for row in data:
        if set(row.keys()) != first_row_keys:
            return False, "Inconsistent columns across rows"

    # Validate data_type specific requirements
    if data_type == "team":
        if "team" not in first_row_keys:
            return False, "Team datasets must have 'team' column"
    elif data_type == "player":
        if "player" not in first_row_keys:
            return False, "Player datasets must have 'player' column"

    return True, None
