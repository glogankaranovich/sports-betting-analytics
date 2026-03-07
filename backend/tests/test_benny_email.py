"""
Test script for Benny weekly email reporter
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from benny_weekly_reporter import lambda_handler

# Test event
event = {
    'report_type': 'weekly'
}

# Mock context
class Context:
    function_name = 'test'
    request_id = 'test-123'

if __name__ == '__main__':
    result = lambda_handler(event, Context())
    print(f"\nResult: {result}")
