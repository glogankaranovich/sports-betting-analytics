"""
Test script to verify Benny's enhanced learning feedback with real data
"""
import os
from benny_trader import BennyTrader

# Set environment for dev testing
os.environ["DYNAMODB_TABLE"] = "carpool-bets-v2-dev"

def test_learning_with_real_data():
    """Test that learning methods work with real dev data"""
    trader = BennyTrader()
    
    print("=" * 60)
    print("UPDATING LEARNING PARAMETERS FROM REAL DATA")
    print("=" * 60)
    
    # Update learning parameters to populate performance data
    trader.update_learning_parameters()
    
    print("\n" + "=" * 60)
    print("TESTING BENNY LEARNING FEEDBACK")
    print("=" * 60)
    
    print("\n1. What Works Analysis:")
    print("-" * 60)
    result = trader._get_what_works_analysis()
    print(result)
    
    print("\n2. What Fails Analysis:")
    print("-" * 60)
    result = trader._get_what_fails_analysis()
    print(result)
    
    print("\n3. Recent Mistakes:")
    print("-" * 60)
    result = trader._analyze_recent_mistakes(limit=10)
    print(result)
    
    print("\n4. Winning Examples (basketball_nba):")
    print("-" * 60)
    result = trader._get_winning_examples("basketball_nba", limit=3)
    print(result)
    
    print("\n5. Winning Factors Correlation:")
    print("-" * 60)
    result = trader._extract_winning_factors()
    print(result)
    
    print("\n6. Model Benchmarks (basketball_nba):")
    print("-" * 60)
    result = trader._get_model_benchmarks("basketball_nba")
    print(result)
    
    print("\n" + "=" * 60)
    print("LEARNING FEEDBACK TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_learning_with_real_data()
