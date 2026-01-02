import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class OddsAPIClient:
    def __init__(self):
        self.api_key = os.getenv('ODDS_API_KEY')
        self.base_url = 'https://api.the-odds-api.com/v4'
        
        # Supported sports (NFL, NBA, MLB, NHL)
        self.supported_sports = [
            'americanfootball_nfl',
            'basketball_nba',
            'baseball_mlb',
            'icehockey_nhl'
        ]
        
    def get_sports(self):
        """Get available sports"""
        url = f"{self.base_url}/sports"
        params = {
            'api_key': self.api_key
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    
    def get_odds(self, sport, markets='h2h'):
        """Get odds for a specific sport"""
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            'api_key': self.api_key,
            'regions': 'us',
            'markets': markets,
            'oddsFormat': 'american',
            'dateFormat': 'iso'
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None

def main():
    client = OddsAPIClient()
    
    print("🎯 Fetching odds for supported sports...")
    print(f"Supported sports: {client.supported_sports}")
    print("-" * 50)
    
    for sport in client.supported_sports:
        print(f"\n🏆 Getting odds for {sport}...")
        odds = client.get_odds(sport)
        
        if odds:
            print(f"Found {len(odds)} games")
            
            # Show first 2 games for each sport
            for game in odds[:2]:
                print(f"\n📅 {game['commence_time']}")
                print(f"🏟️  {game['away_team']} @ {game['home_team']}")
                
                if game['bookmakers']:
                    bookmaker = game['bookmakers'][0]  # First bookmaker
                    print(f"📊 {bookmaker['title']}:")
                    
                    for market in bookmaker['markets']:
                        if market['key'] == 'h2h':  # Head-to-head (moneyline)
                            for outcome in market['outcomes']:
                                print(f"   {outcome['name']}: {outcome['price']}")
        else:
            print(f"No odds available for {sport}")
        
        print("-" * 30)

if __name__ == "__main__":
    main()
