"""
Configuration management for sports data crawlers.

This module handles loading and managing crawler configurations
from environment variables and configuration files.
"""

import os
import json
import boto3
from typing import Dict, List, Optional
from dataclasses import dataclass


def get_secret_value(secret_arn: str) -> Optional[str]:
    """Get secret value from AWS Secrets Manager."""
    try:
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=secret_arn)
        return response['SecretString']
    except Exception as e:
        print(f"Failed to get secret {secret_arn}: {e}")
        return None


def get_odds_api_key() -> Optional[str]:
    """Get The Odds API key from environment or Secrets Manager."""
    # First try direct environment variable (for local development)
    if os.getenv('THE_ODDS_API_KEY'):
        return os.getenv('THE_ODDS_API_KEY')
    
    # Then try Secrets Manager (for Lambda)
    secret_arn = os.getenv('ODDS_API_SECRET_ARN')
    if secret_arn:
        return get_secret_value(secret_arn)
    
    return None


def get_sportsdata_api_key() -> Optional[str]:
    """Get SportsData.io API key from environment or Secrets Manager."""
    # First try direct environment variable (for local development)
    if os.getenv('SPORTSDATA_API_KEY'):
        return os.getenv('SPORTSDATA_API_KEY')
    
    # Then try Secrets Manager (for Lambda)
    secret_arn = os.getenv('SPORTSDATA_API_SECRET_ARN')
    if secret_arn:
        return get_secret_value(secret_arn)
    
    return None


def get_api_sports_key() -> Optional[str]:
    """Get API-SPORTS API key from environment or Secrets Manager."""
    # First try direct environment variable (for local development)
    if os.getenv('API_SPORTS_KEY'):
        return os.getenv('API_SPORTS_KEY')
    
    # Then try Secrets Manager (for Lambda)
    secret_arn = os.getenv('API_SPORTS_SECRET_ARN')
    if secret_arn:
        return get_secret_value(secret_arn)
    
    return None
from .base_crawler import CrawlerConfig, DataSourceType


@dataclass
class CrawlerSettings:
    """Global crawler settings."""
    default_sports: List[str]
    collection_interval_minutes: int
    max_concurrent_crawlers: int
    data_retention_days: int
    enable_historical_data: bool


class CrawlerConfigManager:
    """Manages crawler configurations and settings."""
    
    DEFAULT_SPORTS = [
        'nfl', 'nba', 'mlb', 'nhl', 
        'soccer_epl', 'soccer_uefa_champs_league'
    ]
    
    def __init__(self):
        self.settings = self._load_settings()
        self.crawler_configs = self._load_crawler_configs()
    
    def _load_settings(self) -> CrawlerSettings:
        """Load global crawler settings from environment."""
        return CrawlerSettings(
            default_sports=self._get_env_list('CRAWLER_DEFAULT_SPORTS', self.DEFAULT_SPORTS),
            collection_interval_minutes=int(os.getenv('CRAWLER_INTERVAL_MINUTES', '60')),
            max_concurrent_crawlers=int(os.getenv('CRAWLER_MAX_CONCURRENT', '5')),
            data_retention_days=int(os.getenv('CRAWLER_DATA_RETENTION_DAYS', '30')),
            enable_historical_data=os.getenv('CRAWLER_ENABLE_HISTORICAL', 'false').lower() == 'true'
        )
    
    def _load_crawler_configs(self) -> Dict[str, CrawlerConfig]:
        """Load individual crawler configurations."""
        configs = {}
        
        # The Odds API configuration
        odds_api_key = get_odds_api_key()
        if odds_api_key:
            configs['the_odds_api'] = CrawlerConfig(
                name='the_odds_api',
                source_type=DataSourceType.API,
                base_url='https://api.the-odds-api.com/v4',
                api_key=odds_api_key,
                rate_limit_per_minute=int(os.getenv('THE_ODDS_API_RATE_LIMIT', '10')),
                timeout_seconds=int(os.getenv('THE_ODDS_API_TIMEOUT', '30')),
                retry_attempts=int(os.getenv('THE_ODDS_API_RETRIES', '3')),
                enabled=os.getenv('THE_ODDS_API_ENABLED', 'true').lower() == 'true'
            )
        
        # SportsData.io configuration
        sportsdata_api_key = get_sportsdata_api_key()
        if sportsdata_api_key:
            configs['sportsdata_io'] = CrawlerConfig(
                name='sportsdata_io',
                source_type=DataSourceType.API,
                base_url='https://api.sportsdata.io',
                api_key=sportsdata_api_key,
                rate_limit_per_minute=int(os.getenv('SPORTSDATA_IO_RATE_LIMIT', '60')),
                timeout_seconds=int(os.getenv('SPORTSDATA_IO_TIMEOUT', '30')),
                retry_attempts=int(os.getenv('SPORTSDATA_IO_RETRIES', '3')),
                enabled=os.getenv('SPORTSDATA_IO_ENABLED', 'true').lower() == 'true'
            )
        
        return configs
    
    def _get_env_list(self, env_var: str, default: List[str]) -> List[str]:
        """Get a list from environment variable (comma-separated)."""
        env_value = os.getenv(env_var)
        if env_value:
            return [item.strip() for item in env_value.split(',')]
        return default
    
    def get_enabled_crawlers(self) -> Dict[str, CrawlerConfig]:
        """Get only enabled crawler configurations."""
        return {name: config for name, config in self.crawler_configs.items() if config.enabled}
    
    def update_crawler_config(self, name: str, **kwargs):
        """Update a crawler configuration."""
        if name in self.crawler_configs:
            config = self.crawler_configs[name]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def disable_crawler(self, name: str):
        """Disable a specific crawler."""
        if name in self.crawler_configs:
            self.crawler_configs[name].enabled = False
    
    def enable_crawler(self, name: str):
        """Enable a specific crawler."""
        if name in self.crawler_configs:
            self.crawler_configs[name].enabled = True
    
    def get_config_summary(self) -> Dict[str, any]:
        """Get a summary of current configuration."""
        return {
            'settings': {
                'default_sports': self.settings.default_sports,
                'collection_interval_minutes': self.settings.collection_interval_minutes,
                'max_concurrent_crawlers': self.settings.max_concurrent_crawlers,
                'data_retention_days': self.settings.data_retention_days,
                'enable_historical_data': self.settings.enable_historical_data,
            },
            'crawlers': {
                name: {
                    'enabled': config.enabled,
                    'source_type': config.source_type.value,
                    'rate_limit_per_minute': config.rate_limit_per_minute,
                    'has_api_key': bool(config.api_key),
                }
                for name, config in self.crawler_configs.items()
            }
        }
