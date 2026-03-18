"""Reset all incorrectly settled prop bets to pending and fix bankrolls."""
import boto3
from decimal import Decimal

session = boto3.Session(profile_name="sports-betting-dev", region_name="us-east-1")
dynamodb = session.resource("dynamodb")
table = dynamodb.Table("carpool-bets-v2-dev")

# All V1 won prop bets (19)
v1_won = [
    "BET#2026-03-12T13:39:06.709778#05abd26b6e3a0a9e4317e3948c06a097",  # Jalen Duren Over 22.5 Points
    "BET#2026-03-12T13:39:06.773144#934acadeb7fcd3d3c1d79fd8b324040c",  # Grayson Allen Over 15.5 Points
    "BET#2026-03-12T21:08:16.870603#05abd26b6e3a0a9e4317e3948c06a097",  # Andre Drummond Over 0.5 Assists
    "BET#2026-03-12T21:08:16.923677#cd2e1d8b7576bcfeb478f6e35d9b3981",  # Bilal Coulibaly Over 9.5 Points
    "BET#2026-03-13T13:08:19.948773#9f90f0cfcf3b921f77ede1f83724a96f",  # Cade Cunningham Over 10.5 Assists
    "BET#2026-03-13T13:08:19.990688#fff92660471a227787e69030342c161a",  # Cooper Flagg Over 19.5 Points
    "BET#2026-03-14T01:09:04.955665#8f70af8b76f27c4f0a7a6957464edf9d",  # Rudy Gobert Over 12.5 Rebounds
    "BET#2026-03-15T01:08:27.927113#fd3cb91e05ed15d6fa70f51f1d305f3b",  # DeMar DeRozan Over 3.5 Assists
    "BET#2026-03-15T01:08:27.977367#fd3cb91e05ed15d6fa70f51f1d305f3b",  # Precious Achiuwa Over 10.5 Points
    "BET#2026-03-15T13:06:42.478797#689cb75979724773a16b617332228d55",  # Rudy Gobert Over 9.5 Points
    "BET#2026-03-15T13:06:42.669138#689cb75979724773a16b617332228d55",  # Donte DiVincenzo Over 4.5 Assists
    "BET#2026-03-15T20:37:32.893597#6420f72c1e96bb40f11548af8dbb2950",  # Jrue Holiday Over 16.5 Points
    "BET#2026-03-15T20:37:32.936586#6420f72c1e96bb40f11548af8dbb2950",  # VJ Edgecombe Over 5.5 Rebounds
    "BET#2026-03-16T01:04:39.902357#ae243acf61e3bbc8a0fef18df12adf30",  # Isaiah Collier Over 17.5 Points
    "BET#2026-03-16T01:04:39.952305#ae243acf61e3bbc8a0fef18df12adf30",  # DeMar DeRozan Over 4.5 Assists
    "BET#2026-03-16T13:45:40.879633#16a4c04f493443107656ff044ca9f8c0",  # Bilal Coulibaly Over 11.5 Points
    "BET#2026-03-16T13:45:40.917079#ffe5b43309eff2a1e0131998ff33abd6",  # NAW Over 3.5 Assists
    "BET#2026-03-16T13:45:40.962526#16a4c04f493443107656ff044ca9f8c0",  # Brandin Podziemski Over 6.5 Rebounds
    "BET#2026-03-16T13:45:40.997012#ffe5b43309eff2a1e0131998ff33abd6",  # Jonathan Kuminga Over 4.5 Rebounds
]

# All V1 lost prop bets (4)
v1_lost = [
    "BET#2026-03-14T01:09:04.900131#8f70af8b76f27c4f0a7a6957464edf9d",  # Julius Randle Under 19.5 Points
    "BET#2026-03-14T13:08:48.836794#12c0f198cfa33b284457ae31066ace94",  # Quentin Grimes Under 19.5 Points
    "BET#2026-03-15T13:06:42.600424#689cb75979724773a16b617332228d55",  # SGA Under 4.5 Rebounds
    "BET#2026-03-15T20:37:33.024574#6420f72c1e96bb40f11548af8dbb2950",  # Quentin Grimes Under 5.5 Assists
]

# All V3 won prop bets (3)
v3_won = [
    "BET#2026-03-16T17:50:11.985954#ffe5b43309eff2a1e0131998ff33abd6",  # Onyeka Okongwu Over 7.5 Rebounds
    "BET#2026-03-16T17:50:12.372414#16a4c04f493443107656ff044ca9f8c0",  # Brandin Podziemski Over 6.5 Rebounds
    "BET#2026-03-17T01:11:32.281241#e18bb0c990005d46d98ab6ec89f2cfff",  # Amen Thompson Over 6.5 Rebounds
]

# All V3 lost prop bets (1)
v3_lost = [
    "BET#2026-03-17T01:11:32.362361#e18bb0c990005d46d98ab6ec89f2cfff",  # Tari Eason Under 10.5 Points
]

# Track bankroll adjustments
v1_bankroll_adjustment = Decimal("0")
v3_bankroll_adjustment = Decimal("0")


def reset_bet(pk, sk):
    """Reset a bet to pending and return its payout for bankroll adjustment."""
    # First get the current bet to know the payout
    resp = table.get_item(Key={"pk": pk, "sk": sk})
    item = resp.get("Item")
    if not item:
        print(f"  NOT FOUND: {sk}")
        return Decimal("0")

    status = item.get("status")
    payout = Decimal(str(item.get("payout", 0)))
    bet_amount = Decimal(str(item.get("bet_amount", 0)))
    player = item.get("player_name", "?")
    prediction = item.get("prediction", "?")

    # Reset to pending
    table.update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression="SET #s = :pending REMOVE payout, profit, settled_at",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":pending": "pending"},
    )

    # For "won" bets: bankroll was increased by payout, so subtract payout
    # For "lost" bets: bankroll was NOT increased (payout=0), but the bet_amount
    #   was already deducted at placement time, so no bankroll change needed
    # Wait — actually the settlement code does: current_bankroll += payout
    # For won: payout = bet_amount + profit (positive), so bankroll went up by payout
    # For lost: payout = 0, so bankroll didn't change at settlement
    # So we only need to reverse "won" payouts
    adjustment = -payout if status == "won" else Decimal("0")

    print(f"  Reset {pk} | {player} {prediction} | was={status} payout={payout} | bankroll_adj={adjustment}")
    return adjustment


print("=== Resetting V1 WON prop bets (19) ===")
for sk in v1_won:
    v1_bankroll_adjustment += reset_bet("BENNY", sk)

print(f"\n=== Resetting V1 LOST prop bets (4) ===")
for sk in v1_lost:
    v1_bankroll_adjustment += reset_bet("BENNY", sk)

print(f"\n=== Resetting V3 WON prop bets (3) ===")
for sk in v3_won:
    v3_bankroll_adjustment += reset_bet("BENNY_V3", sk)

print(f"\n=== Resetting V3 LOST prop bets (1) ===")
for sk in v3_lost:
    v3_bankroll_adjustment += reset_bet("BENNY_V3", sk)

# Get current bankrolls
print(f"\n=== Bankroll Adjustments ===")
print(f"V1 adjustment: {v1_bankroll_adjustment}")
print(f"V3 adjustment: {v3_bankroll_adjustment}")

for pk, adj in [("BENNY", v1_bankroll_adjustment), ("BENNY_V3", v3_bankroll_adjustment)]:
    resp = table.get_item(Key={"pk": pk, "sk": "BANKROLL"})
    current = Decimal(str(resp["Item"]["amount"]))
    new_amount = current + adj
    print(f"\n{pk} bankroll: {current} + ({adj}) = {new_amount}")

    table.update_item(
        Key={"pk": pk, "sk": "BANKROLL"},
        UpdateExpression="SET amount = :amt, updated_at = :now",
        ExpressionAttributeValues={
            ":amt": new_amount,
            ":now": "2026-03-17T12:38:00Z",
        },
    )
    print(f"  Updated {pk} bankroll to {new_amount}")

print("\nDone! All 27 prop bets reset to pending.")
