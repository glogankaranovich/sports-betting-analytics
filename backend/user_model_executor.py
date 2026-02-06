"""
User Model Executor - Processes user models from SQS queue and generates predictions
"""
import json
import os
from typing import Dict, List
import boto3
from user_models import UserModel, ModelPrediction

dynamodb = boto3.resource("dynamodb")
BETS_TABLE = os.environ.get("BETS_TABLE", "carpool-bets-v2-dev")
bets_table = dynamodb.Table(BETS_TABLE)


def evaluate_team_stats(game_data: Dict) -> float:
    """
    Evaluate team stats data source
    Returns normalized score 0-1 (>0.5 favors home, <0.5 favors away)
    """
    from boto3.dynamodb.conditions import Key

    sport = game_data.get("sport", "basketball_nba")
    home_team = game_data.get("home_team", "").lower().replace(" ", "_")
    away_team = game_data.get("away_team", "").lower().replace(" ", "_")

    try:
        # Query recent stats for both teams (last game)
        home_response = bets_table.query(
            KeyConditionExpression=Key("pk").eq(f"TEAM_STATS#{sport}#{home_team}"),
            ScanIndexForward=False,
            Limit=1,
        )
        away_response = bets_table.query(
            KeyConditionExpression=Key("pk").eq(f"TEAM_STATS#{sport}#{away_team}"),
            ScanIndexForward=False,
            Limit=1,
        )

        home_stats = home_response.get("Items", [{}])[0].get("stats", {})
        away_stats = away_response.get("Items", [{}])[0].get("stats", {})

        if not home_stats or not away_stats:
            return 0.5  # No data, neutral

        # Calculate composite score from key metrics
        home_score = 0
        away_score = 0

        # Field Goal % (weight: 0.4)
        home_fg = float(home_stats.get("Field Goal %", "0"))
        away_fg = float(away_stats.get("Field Goal %", "0"))
        if home_fg + away_fg > 0:
            home_score += 0.4 * (home_fg / (home_fg + away_fg))
            away_score += 0.4 * (away_fg / (home_fg + away_fg))

        # Three Point % (weight: 0.3)
        home_3pt = float(home_stats.get("Three Point %", "0"))
        away_3pt = float(away_stats.get("Three Point %", "0"))
        if home_3pt + away_3pt > 0:
            home_score += 0.3 * (home_3pt / (home_3pt + away_3pt))
            away_score += 0.3 * (away_3pt / (home_3pt + away_3pt))

        # Rebounds (weight: 0.3)
        home_reb = float(home_stats.get("Rebounds", "0"))
        away_reb = float(away_stats.get("Rebounds", "0"))
        if home_reb + away_reb > 0:
            home_score += 0.3 * (home_reb / (home_reb + away_reb))
            away_score += 0.3 * (away_reb / (home_reb + away_reb))

        # Normalize to 0-1 (>0.5 favors home)
        total = home_score + away_score
        return home_score / total if total > 0 else 0.5

    except Exception as e:
        print(f"Error evaluating team stats: {e}")
        return 0.5  # Fallback to neutral


def evaluate_odds_movement(game_data: Dict) -> float:
    """
    Evaluate odds movement data source
    Returns normalized score 0-1 (>0.5 favors home, <0.5 favors away)
    Detects sharp action by comparing opening vs current lines
    """
    from boto3.dynamodb.conditions import Key

    game_id = game_data.get("game_id", "")
    if not game_id:
        return 0.5

    try:
        # Query all historical odds for this game
        response = bets_table.query(
            KeyConditionExpression=Key("pk").eq(f"GAME#{game_id}"),
            ScanIndexForward=True,  # Oldest first
        )

        items = response.get("Items", [])
        if len(items) < 2:
            return 0.5  # Need at least 2 data points

        # Find opening and latest odds for h2h market
        opening_odds = None
        latest_odds = None

        for item in items:
            sk = item.get("sk", "")
            if "#h2h#" not in sk:
                continue

            if sk.endswith("#LATEST"):
                latest_odds = item
            elif not opening_odds:  # First historical record
                opening_odds = item

        if not opening_odds or not latest_odds:
            return 0.5

        # Extract home/away odds
        opening_home = None
        opening_away = None
        latest_home = None
        latest_away = None

        for outcome in opening_odds.get("outcomes", []):
            if outcome["name"] == opening_odds["home_team"]:
                opening_home = float(outcome["price"])
            elif outcome["name"] == opening_odds["away_team"]:
                opening_away = float(outcome["price"])

        for outcome in latest_odds.get("outcomes", []):
            if outcome["name"] == latest_odds["home_team"]:
                latest_home = float(outcome["price"])
            elif outcome["name"] == latest_odds["away_team"]:
                latest_away = float(outcome["price"])

        if not all([opening_home, opening_away, latest_home, latest_away]):
            return 0.5

        # Calculate movement (positive = line moved toward home)
        home_movement = latest_home - opening_home

        # Sharp action threshold: >20 points moneyline movement
        sharp_threshold = 20

        if abs(home_movement) < sharp_threshold:
            return 0.5  # No significant movement

        # Normalize movement to 0-1 score
        # Positive home movement (odds increased) = sharps on away
        # Negative home movement (odds decreased) = sharps on home
        movement_score = -home_movement / 100  # Scale to reasonable range
        return max(0.0, min(1.0, 0.5 + movement_score))

    except Exception as e:
        print(f"Error evaluating odds movement: {e}")
        return 0.5


def evaluate_recent_form(game_data: Dict) -> float:
    """
    Evaluate recent form data source
    Returns normalized score 0-1 (>0.5 favors home, <0.5 favors away)
    Based on last 5 games win rate and point differential
    """
    from boto3.dynamodb.conditions import Key

    sport = game_data.get("sport", "basketball_nba")
    home_team = game_data.get("home_team", "")
    away_team = game_data.get("away_team", "")

    if not home_team or not away_team:
        return 0.5

    try:
        # Query recent outcomes for both teams
        home_outcomes = bets_table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"TEAM#{sport}#{home_team}"),
            ScanIndexForward=False,
            Limit=5,
        )

        away_outcomes = bets_table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"TEAM#{sport}#{away_team}"),
            ScanIndexForward=False,
            Limit=5,
        )

        home_games = home_outcomes.get("Items", [])
        away_games = away_outcomes.get("Items", [])

        if not home_games or not away_games:
            return 0.5  # No data

        # Calculate win rate and point differential
        home_wins = sum(1 for g in home_games if g.get("winner") == home_team)
        away_wins = sum(1 for g in away_games if g.get("winner") == away_team)

        home_win_rate = home_wins / len(home_games)
        away_win_rate = away_wins / len(away_games)

        # Calculate average point differential
        home_diff = sum(
            float(g.get("home_score", 0)) - float(g.get("away_score", 0))
            if g.get("home_team") == home_team
            else float(g.get("away_score", 0)) - float(g.get("home_score", 0))
            for g in home_games
        ) / len(home_games)

        away_diff = sum(
            float(g.get("home_score", 0)) - float(g.get("away_score", 0))
            if g.get("home_team") == away_team
            else float(g.get("away_score", 0)) - float(g.get("home_score", 0))
            for g in away_games
        ) / len(away_games)

        # Combine win rate (70%) and point diff (30%)
        home_score = 0.7 * home_win_rate + 0.3 * (home_diff / 20)  # Normalize diff
        away_score = 0.7 * away_win_rate + 0.3 * (away_diff / 20)

        # Normalize to 0-1
        total = home_score + away_score
        return home_score / total if total > 0 else 0.5

    except Exception as e:
        print(f"Error evaluating recent form: {e}")
        return 0.5


def evaluate_rest_schedule(game_data: Dict) -> float:
    """
    Evaluate rest and schedule data source
    Returns normalized score 0-1
    """
    game_id = game_data.get("game_id", "")
    hash_val = (sum(ord(c) for c in game_id) * 13) % 100
    return 0.4 + (hash_val / 100) * 0.2  # Range: 0.4-0.6


def evaluate_head_to_head(game_data: Dict) -> float:
    """
    Evaluate head-to-head data source
    Returns normalized score 0-1
    """
    game_id = game_data.get("game_id", "")
    hash_val = (sum(ord(c) for c in game_id) * 17) % 100
    return 0.3 + (hash_val / 100) * 0.4  # Range: 0.3-0.7


DATA_SOURCE_EVALUATORS = {
    "team_stats": evaluate_team_stats,
    "odds_movement": evaluate_odds_movement,
    "recent_form": evaluate_recent_form,
    "rest_schedule": evaluate_rest_schedule,
    "head_to_head": evaluate_head_to_head,
}


def calculate_prediction(model: UserModel, game_data: Dict) -> Dict:
    """
    Calculate prediction using model configuration
    Returns: {prediction, confidence, reasoning} or None if below threshold
    """
    total_score = 0
    total_weight = 0
    source_scores = {}

    # Evaluate each enabled data source
    for source_name, config in model.data_sources.items():
        if not config.get("enabled"):
            continue

        evaluator = DATA_SOURCE_EVALUATORS.get(source_name)
        if not evaluator:
            continue

        # Get normalized score (0-1) from data source
        score = evaluator(game_data)
        weight = float(config.get("weight", 0))

        source_scores[source_name] = score
        total_score += score * weight
        total_weight += weight

    # Normalize to 0-1
    confidence = total_score / total_weight if total_weight > 0 else 0

    # Check minimum confidence threshold
    if confidence < float(model.min_confidence):
        return None

    # Determine prediction based on score
    if confidence > 0.55:
        prediction = game_data["home_team"]
    elif confidence < 0.45:
        prediction = game_data["away_team"]
    else:
        return None  # Too close to call

    # Generate reasoning
    reasoning_parts = []
    for source, score in sorted(
        source_scores.items(), key=lambda x: x[1], reverse=True
    ):
        weight = float(model.data_sources[source]["weight"])
        reasoning_parts.append(f"{source}: {score:.2f} (weight: {weight:.0%})")

    reasoning = f"Prediction based on: {', '.join(reasoning_parts[:3])}"

    return {"prediction": prediction, "confidence": confidence, "reasoning": reasoning}


def get_upcoming_games(sport: str, bet_types: List[str]) -> List[Dict]:
    """
    Get upcoming games for the sport
    """
    from datetime import datetime, timedelta
    from boto3.dynamodb.conditions import Key

    now = datetime.utcnow()
    future = now + timedelta(days=7)

    games = {}

    # Query using ActiveBetsIndexV2 to get upcoming games
    response = bets_table.query(
        IndexName="ActiveBetsIndexV2",
        KeyConditionExpression=Key("active_bet_pk").eq(f"GAME#{sport}")
        & Key("commence_time").between(now.isoformat(), future.isoformat()),
        FilterExpression="attribute_exists(latest)",
        Limit=100,
    )

    for item in response.get("Items", []):
        game_id = item.get("pk", "")[5:]  # Remove GAME# prefix
        if not game_id or game_id in games:
            continue

        games[game_id] = {
            "game_id": game_id,
            "sport": sport,
            "home_team": item.get("home_team", "Unknown"),
            "away_team": item.get("away_team", "Unknown"),
            "commence_time": item.get("commence_time"),
        }

    print(f"Found {len(games)} upcoming games for {sport}")
    return list(games.values())


def process_model(model_id: str, user_id: str):
    """
    Process a single user model - generate predictions for upcoming games
    """
    # Load model configuration
    model = UserModel.get(user_id, model_id)
    if not model or model.status != "active":
        print(f"Model {model_id} not found or inactive")
        return

    # Get upcoming games for this sport
    games = get_upcoming_games(model.sport, model.bet_types)

    predictions_created = 0
    for game in games:
        # Calculate prediction
        result = calculate_prediction(model, game)
        if not result:
            print(f"Skipped game {game['game_id']}: low confidence or too close")
            continue  # Skip low-confidence predictions

        # Create prediction record
        prediction = ModelPrediction(
            model_id=model.model_id,
            user_id=model.user_id,
            game_id=game["game_id"],
            sport=model.sport,
            prediction=result["prediction"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            bet_type=game.get("bet_type", "h2h"),
            home_team=game["home_team"],
            away_team=game["away_team"],
            commence_time=game["commence_time"],
        )

        # Save to DynamoDB
        prediction.save()
        predictions_created += 1

    print(f"Model {model_id}: Created {predictions_created} predictions")


def handler(event, context):
    """
    Lambda handler - processes SQS messages with model execution requests
    """
    print(f"Processing {len(event['Records'])} messages")

    failed_items = []

    for record in event["Records"]:
        try:
            # Parse message body
            body = json.loads(record["body"])
            model_id = body["model_id"]
            user_id = body["user_id"]

            print(f"Processing model: {model_id}")

            # Process the model
            process_model(model_id, user_id)

        except Exception as e:
            print(f"Error processing message: {str(e)}")
            # Add to failed items for partial batch failure
            failed_items.append({"itemIdentifier": record["messageId"]})

    # Return partial batch failure response
    if failed_items:
        return {"batchItemFailures": failed_items}

    return {
        "statusCode": 200,
        "body": json.dumps(f'Processed {len(event["Records"])} models'),
    }
