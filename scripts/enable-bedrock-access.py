#!/usr/bin/env python3
"""
Submit Anthropic use case form to enable Claude model access
"""
import json
import boto3

bedrock = boto3.client("bedrock", region_name="us-east-1")

form_data = {
    "companyName": "Carpool Bets",
    "companyWebsite": "carpoolbets.com",
    "intendedUsers": "1",  # External users
    "industryOption": "Entertainment",
    "otherIndustryOption": "",
    "useCases": "AI-powered sports betting analytics assistant that helps users create custom prediction models, analyze betting performance, and make data-driven decisions."
}

try:
    response = bedrock.put_use_case_for_model_access(
        formData=json.dumps(form_data)
    )
    print("✅ Use case form submitted successfully!")
    print(f"Response: {response}")
except Exception as e:
    print(f"❌ Error: {e}")
