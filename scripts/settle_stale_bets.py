"""Delete stale pending bets and refund bankroll for BENNY and BENNY_V3."""
import boto3
from decimal import Decimal
from datetime import datetime, timedelta, timezone

session = boto3.Session(profile_name="sports-betting-dev", region_name="us-east-1")
dynamodb = session.resource("dynamodb")
table = dynamodb.Table("carpool-bets-v2-dev")
now = datetime.now(timezone.utc)

for pk in ["BENNY", "BENNY_V3"]:
    resp = table.query(
        KeyConditionExpression="pk = :pk AND begins_with(sk, :bet)",
        FilterExpression="#s IN (:pending, :lost)",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":pk": pk, ":bet": "BET#", ":pending": "pending", ":lost": "lost"},
    )
    stale = []
    for item in resp.get("Items", []):
        ct = item.get("commence_time", "")
        # Include bets we just wrongly settled as lost
        just_settled = item.get("status") == "lost" and item.get("settled_at", "").startswith("2026-03-19T15:")
        if just_settled:
            stale.append(item)
            continue
        if item.get("status") != "pending":
            continue
        if not ct:
            placed = item.get("placed_at", "")
            if placed and placed < now.isoformat()[:10]:
                stale.append(item)
            continue
        try:
            game_time = datetime.fromisoformat(ct.replace("Z", "+00:00"))
            if game_time + timedelta(hours=4) < now:
                stale.append(item)
        except Exception:
            pass

    refund = Decimal("0")
    print(f"\n{pk}: {len(stale)} stale bets to delete")
    for item in sorted(stale, key=lambda x: x.get("sk", "")):
        sk = item["sk"]
        amt = Decimal(str(item["bet_amount"]))
        pred = item.get("prediction", item.get("market_key", "?"))
        print(f"  Deleting: {pred} ${amt:.2f}")
        table.delete_item(Key={"pk": pk, "sk": sk})
        refund += amt

    if refund > 0:
        br_resp = table.get_item(Key={"pk": pk, "sk": "BANKROLL"})
        old = Decimal(str(br_resp["Item"]["amount"]))
        new = old + refund
        table.update_item(
            Key={"pk": pk, "sk": "BANKROLL"},
            UpdateExpression="SET amount = :a",
            ExpressionAttributeValues={":a": new},
        )
        print(f"  Refunded ${refund:.2f} → bankroll ${old:.2f} → ${new:.2f}")

print("\nDone.")
