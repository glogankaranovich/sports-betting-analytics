# Weather API Key Setup

## Create Secret in AWS Secrets Manager

Run these commands to add the weather API key to Secrets Manager:

```bash
# Dev environment
aws secretsmanager create-secret \
  --name sports-betting/weather-api-key-dev \
  --secret-string "71f72391fa164b4dbf5212858262002" \
  --region us-east-1 \
  --profile sports-betting-dev

# Prod environment (when ready)
aws secretsmanager create-secret \
  --name sports-betting/weather-api-key-prod \
  --secret-string "71f72391fa164b4dbf5212858262002" \
  --region us-east-1 \
  --profile sports-betting-prod
```

## Usage in Lambda Functions

Any Lambda function that needs weather data should:

1. Have the secret ARN in environment variables:
   ```typescript
   environment: {
     WEATHER_API_SECRET_ARN: weatherApiSecret.secretArn
   }
   ```

2. Grant read permissions:
   ```typescript
   weatherApiSecret.grantRead(lambdaFunction);
   ```

3. Access in Python code:
   ```python
   from weather_collector import WeatherCollector
   
   weather = WeatherCollector()
   weather_data = weather.get_weather_for_game(game_id, venue, city, sport, game_time)
   ```

## API Provider

- Provider: WeatherAPI.com
- Free tier: 1M calls/month
- Documentation: https://www.weatherapi.com/docs/
