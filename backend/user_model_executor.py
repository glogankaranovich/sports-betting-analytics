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
    Returns normalized score 0-1 (>0.5 favors home, <0.5 favors away)
    Based on days of rest and back-to-back detection
    """
    from boto3.dynamodb.conditions import Key
    from datetime import datetime

    sport = game_data.get("sport", "basketball_nba")
    home_team = game_data.get("home_team", "")
    away_team = game_data.get("away_team", "")
    game_time = game_data.get("commence_time", "")

    if not all([home_team, away_team, game_time]):
        return 0.5

    try:
        game_dt = datetime.fromisoformat(game_time.replace("Z", "+00:00"))

        # Query last game for both teams
        home_outcomes = bets_table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"TEAM#{sport}#{home_team}"),
            ScanIndexForward=False,
            Limit=1,
        )

        away_outcomes = bets_table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"TEAM#{sport}#{away_team}"),
            ScanIndexForward=False,
            Limit=1,
        )

        home_last = home_outcomes.get("Items", [])
        away_last = away_outcomes.get("Items", [])

        if not home_last or not away_last:
            return 0.5  # No data

        # Calculate days of rest
        home_last_dt = datetime.fromisoformat(
            home_last[0].get("completed_at", "").replace("Z", "+00:00")
        )
        away_last_dt = datetime.fromisoformat(
            away_last[0].get("completed_at", "").replace("Z", "+00:00")
        )

        home_rest_days = (game_dt - home_last_dt).days
        away_rest_days = (game_dt - away_last_dt).days

        # Score based on rest advantage (0-1 back-to-back, 1-2 normal, 3+ well-rested)
        home_rest_score = min(home_rest_days / 3, 1.0)
        away_rest_score = min(away_rest_days / 3, 1.0)

        # Normalize to 0-1
        total = home_rest_score + away_rest_score
        return home_rest_score / total if total > 0 else 0.5

    except Exception as e:
        print(f"Error evaluating rest schedule: {e}")
        return 0.5


def evaluate_head_to_head(game_data: Dict) -> float:
    """
    Evaluate head-to-head data source
    Returns normalized score 0-1 (>0.5 favors home, <0.5 favors away)
    Based on historical matchup record between teams
    """
    from boto3.dynamodb.conditions import Key

    sport = game_data.get("sport", "basketball_nba")
    home_team = game_data.get("home_team", "")
    away_team = game_data.get("away_team", "")

    if not home_team or not away_team:
        return 0.5

    try:
        # Normalize team names for H2H query
        home_normalized = home_team.lower().replace(" ", "_")
        away_normalized = away_team.lower().replace(" ", "_")

        # Sort teams alphabetically for consistent H2H key
        teams_sorted = sorted([home_normalized, away_normalized])
        h2h_pk = f"H2H#{sport}#{teams_sorted[0]}#{teams_sorted[1]}"

        # Query historical matchups
        response = bets_table.query(
            KeyConditionExpression=Key("h2h_pk").eq(h2h_pk),
            ScanIndexForward=False,
            Limit=10,
        )

        matchups = response.get("Items", [])
        if not matchups:
            return 0.5  # No history

        # Count wins for each team
        home_wins = sum(1 for m in matchups if m.get("winner") == home_team)
        away_wins = sum(1 for m in matchups if m.get("winner") == away_team)

        total_games = len(matchups)
        home_win_rate = home_wins / total_games
        away_win_rate = away_wins / total_games

        # Normalize to 0-1
        total = home_win_rate + away_win_rate
        return home_win_rate / total if total > 0 else 0.5

    except Exception as e:
        print(f"Error evaluating head-to-head: {e}")
        return 0.5


def evaluate_player_stats(bet_data: Dict) -> float:
    """
    Evaluate player stats data source for props
    Returns normalized score 0-1 based on recent player performance
    """
    from boto3.dynamodb.conditions import Key

    if bet_data.get("bet_type") != "props":
        return 0.5  # Only for props

    sport = bet_data.get("sport", "basketball_nba")
    player_name = bet_data.get("player_name", "")

    if not player_name:
        return 0.5

    try:
        # Normalize player name
        normalized_name = player_name.lower().replace(" ", "_")

        # Query recent player stats
        response = bets_table.query(
            KeyConditionExpression=Key("pk").eq(
                f"PLAYER_STATS#{sport}#{normalized_name}"
            ),
            ScanIndexForward=False,
            Limit=5,
        )

        stats = response.get("Items", [])
        if not stats:
            return 0.5  # No data

        # Calculate average performance (simplified - would need market-specific logic)
        # For now, return slight positive bias if player has recent stats
        return 0.55  # Player has recent activity

    except Exception as e:
        print(f"Error evaluating player stats: {e}")
        return 0.5


def evaluate_player_injury(bet_data: Dict) -> float:
    """
    Evaluate player injury status for props
    Returns normalized score 0-1 (lower if player is injured)
    """
    if bet_data.get("bet_type") != "props":
        return 0.5  # Only for props

    player_name = bet_data.get("player_name", "")

    if not player_name:
        return 0.5

    try:
        # Query injury data for player
        # Injuries are stored per team, so we'd need to query by team
        # For now, return neutral - full implementation would check injury status
        return 0.5

    except Exception as e:
        print(f"Error evaluating player injury: {e}")
        return 0.5


DATA_SOURCE_EVALUATORS = {
    "team_stats": evaluate_team_stats,
    "odds_movement": evaluate_odds_movement,
    "recent_form": evaluate_recent_form,
    "rest_schedule": evaluate_rest_schedule,
    "head_to_head": evaluate_head_to_head,
    "player_stats": evaluate_player_stats,
    "player_injury": evaluate_player_injury,
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


def get_upcoming_bets(sport: str, bet_types: List[str]) -> List[Dict]:
    """
    Get upcoming bets (games and props) for the sport based on bet_types
    """
    from datetime import datetime, timedelta
    from boto3.dynamodb.conditions import Key

    now = datetime.utcnow()
    future = now + timedelta(days=7)

    bets = []
    seen_keys = set()

    # Query using ActiveBetsIndexV2 to get upcoming bets
    response = bets_table.query(
        IndexName="ActiveBetsIndexV2",
        KeyConditionExpression=Key("active_bet_pk").eq(f"GAME#{sport}")
        & Key("commence_time").between(now.isoformat(), future.isoformat()),
        FilterExpression="attribute_exists(latest)",
        Limit=200,
    )

    for item in response.get("Items", []):
        market_key = item.get("market_key", "")

        # Determine bet type from market key
        if market_key == "h2h" and "h2h" in bet_types:
            bet_type = "h2h"
        elif market_key == "spreads" and "spreads" in bet_types:
            bet_type = "spreads"
        elif market_key == "totals" and "totals" in bet_types:
            bet_type = "totals"
        elif market_key.startswith("player_") and "props" in bet_types:
            bet_type = "props"
        else:
            continue  # Skip if not in requested bet types

        # Create unique key to avoid duplicates
        pk = item.get("pk", "")
        sk = item.get("sk", "")
        unique_key = f"{pk}#{sk}"

        if unique_key in seen_keys:
            continue
        seen_keys.add(unique_key)

        game_id = pk[5:] if pk.startswith("GAME#") else ""

        bet = {
            "game_id": game_id,
            "sport": sport,
            "bet_type": bet_type,
            "market_key": market_key,
            "home_team": item.get("home_team", "Unknown"),
            "away_team": item.get("away_team", "Unknown"),
            "commence_time": item.get("commence_time"),
        }

        # Add prop-specific fields
        if bet_type == "props":
            # SK format: {player_name}#{bookmaker}#{market}#LATEST
            sk_parts = sk.split("#")
            bet["player_name"] = sk_parts[0] if len(sk_parts) > 0 else "Unknown"
            bet["bookmaker"] = item.get("bookmaker", "Unknown")

        bets.append(bet)

    print(f"Found {len(bets)} upcoming bets for {sport} (types: {bet_types})")
    return bets


def process_model(model_id: str, user_id: str):
    """
    Process a single user model - generate predictions for upcoming bets
    """
    # Load model configuration
    model = UserModel.get(user_id, model_id)
    if not model or model.status != "active":
        print(f"Model {model_id} not found or inactive")
        return

    # Get upcoming bets for this sport and bet types
    bets = get_upcoming_bets(model.sport, model.bet_types)

    predictions_created = 0
    for bet in bets:
        # Calculate prediction using game-level evaluators
        # (Props use game context - team stats, rest, etc. affect player performance)
        result = calculate_prediction(model, bet)
        if not result:
            print(
                f"Skipped {bet['bet_type']} {bet.get('player_name', bet['game_id'])}: low confidence"
            )
            continue  # Skip low-confidence predictions

        # Create prediction record
        prediction = ModelPrediction(
            model_id=model.model_id,
            user_id=model.user_id,
            game_id=bet["game_id"],
            sport=model.sport,
            prediction=result["prediction"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            bet_type=bet.get("bet_type", "h2h"),
            home_team=bet["home_team"],
            away_team=bet["away_team"],
            commence_time=bet["commence_time"],
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
