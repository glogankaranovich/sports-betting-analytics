"""Manually settle the 8 remaining pending V1 prop bets that are outside the 3-day API window."""
import boto3
from decimal import Decimal
from datetime import datetime

session = boto3.Session(profile_name="sports-betting-dev", region_name="us-east-1")
dynamodb = session.resource("dynamodb")
table = dynamodb.Table("carpool-bets-v2-dev")

pending_sks = [
    "BET#2026-03-12T13:39:06.709778#05abd26b6e3a0a9e4317e3948c06a097",  # Jalen Duren
    "BET#2026-03-12T13:39:06.773144#934acadeb7fcd3d3c1d79fd8b324040c",  # Grayson Allen
    "BET#2026-03-12T21:08:16.870603#05abd26b6e3a0a9e4317e3948c06a097",  # Andre Drummond
    "BET#2026-03-12T21:08:16.923677#cd2e1d8b7576bcfeb478f6e35d9b3981",  # Bilal Coulibaly
    "BET#2026-03-13T13:08:19.948773#9f90f0cfcf3b921f77ede1f83724a96f",  # Cade Cunningham
    "BET#2026-03-13T13:08:19.990688#fff92660471a227787e69030342c161a",  # Cooper Flagg
    "BET#2026-03-14T01:09:04.900131#8f70af8b76f27c4f0a7a6957464edf9d",  # Julius Randle
    "BET#2026-03-14T01:09:04.955665#8f70af8b76f27c4f0a7a6957464edf9d",  # Rudy Gobert
]

now = datetime.utcnow().isoformat()

for sk in pending_sks:
    resp = table.get_item(Key={"pk": "BENNY", "sk": sk})
    item = resp["Item"]
    bet_amount = Decimal(str(item["bet_amount"]))

    table.update_item(
        Key={"pk": "BENNY", "sk": sk},
        UpdateExpression="SET #s = :lost, payout = :zero, profit = :neg, settled_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":lost": "lost",
            ":zero": Decimal("0"),
            ":neg": -bet_amount,
            ":now": now,
        },
    )
    print(f"Settled as lost: {item['player_name']} {item['prediction']} (${bet_amount})")

print(f"\nDone. Settled {len(pending_sks)} bets as lost (no player stats available).")
