#!/usr/bin/env python3
"""
Script to delete all items from DynamoDB table while preserving table structure
"""
import boto3
import os
from typing import List, Dict, Any

def clear_dynamodb_table(table_name: str, profile: str = None):
    """Delete all items from a DynamoDB table"""
    
    # Initialize DynamoDB resource
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    print(f"Starting to clear table: {table_name}")
    
    # Scan and delete in batches
    total_deleted = 0
    last_evaluated_key = None
    
    while True:
        # Scan for items (only get keys for efficiency)
        scan_kwargs = {
            'ProjectionExpression': 'pk, sk',
            'Limit': 25  # DynamoDB batch_writer can handle up to 25 items
        }
        
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
            
        response = table.scan(**scan_kwargs)
        
        items = response.get('Items', [])
        if not items:
            # Check if we have more items to scan
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
            else:
                # Continue scanning even if no items in this batch
                continue
            
        # Delete items in batch
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})
                total_deleted += 1
        
        print(f"Deleted {len(items)} items (total: {total_deleted})")
        
        # Check if there are more items
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    
    print(f"✅ Cleared table {table_name}. Total items deleted: {total_deleted}")

if __name__ == "__main__":
    table_name = os.getenv('DYNAMODB_TABLE', 'carpool-bets-v2-dev')
    profile = os.getenv('AWS_PROFILE', 'sports-betting-dev')
    
    print(f"Clearing table: {table_name}")
    print(f"Using AWS profile: {profile}")
    
    clear_dynamodb_table(table_name, profile)
