"""Reset all prop bets and prop parlays back to pending for re-settlement"""
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("carpool-bets-v2-dev")

# All prop bets to reset (pk, sk)
items_to_reset = [
    # V1 standalone props (23)
    ("BENNY", "BET#2026-03-12T13:39:06.709778#05abd26b6e3a0a9e4317e3948c06a097"),
    ("BENNY", "BET#2026-03-12T13:39:06.773144#934acadeb7fcd3d3c1d79fd8b324040c"),
    ("BENNY", "BET#2026-03-12T21:08:16.870603#05abd26b6e3a0a9e4317e3948c06a097"),
    ("BENNY", "BET#2026-03-12T21:08:16.923677#cd2e1d8b7576bcfeb478f6e35d9b3981"),
    ("BENNY", "BET#2026-03-13T13:08:19.948773#9f90f0cfcf3b921f77ede1f83724a96f"),
    ("BENNY", "BET#2026-03-13T13:08:19.990688#fff92660471a227787e69030342c161a"),
    ("BENNY", "BET#2026-03-14T01:09:04.900131#8f70af8b76f27c4f0a7a6957464edf9d"),
    ("BENNY", "BET#2026-03-14T01:09:04.955665#8f70af8b76f27c4f0a7a6957464edf9d"),
    ("BENNY", "BET#2026-03-14T13:08:48.836794#12c0f198cfa33b284457ae31066ace94"),
    ("BENNY", "BET#2026-03-15T01:08:27.927113#fd3cb91e05ed15d6fa70f51f1d305f3b"),
    ("BENNY", "BET#2026-03-15T01:08:27.977367#fd3cb91e05ed15d6fa70f51f1d305f3b"),
    ("BENNY", "BET#2026-03-15T13:06:42.478797#689cb75979724773a16b617332228d55"),
    ("BENNY", "BET#2026-03-15T13:06:42.600424#689cb75979724773a16b617332228d55"),
    ("BENNY", "BET#2026-03-15T13:06:42.669138#689cb75979724773a16b617332228d55"),
    ("BENNY", "BET#2026-03-15T20:37:32.893597#6420f72c1e96bb40f11548af8dbb2950"),
    ("BENNY", "BET#2026-03-15T20:37:32.936586#6420f72c1e96bb40f11548af8dbb2950"),
    ("BENNY", "BET#2026-03-15T20:37:33.024574#6420f72c1e96bb40f11548af8dbb2950"),
    ("BENNY", "BET#2026-03-16T01:04:39.902357#ae243acf61e3bbc8a0fef18df12adf30"),
    ("BENNY", "BET#2026-03-16T01:04:39.952305#ae243acf61e3bbc8a0fef18df12adf30"),
    ("BENNY", "BET#2026-03-16T13:45:40.879633#16a4c04f493443107656ff044ca9f8c0"),
    ("BENNY", "BET#2026-03-16T13:45:40.917079#ffe5b43309eff2a1e0131998ff33abd6"),
    ("BENNY", "BET#2026-03-16T13:45:40.962526#16a4c04f493443107656ff044ca9f8c0"),
    ("BENNY", "BET#2026-03-16T13:45:40.997012#ffe5b43309eff2a1e0131998ff33abd6"),
    # V3 standalone props (4 lost ones)
    ("BENNY_V3", "BET#2026-03-16T17:50:11.985954#ffe5b43309eff2a1e0131998ff33abd6"),
    ("BENNY_V3", "BET#2026-03-16T17:50:12.372414#16a4c04f493443107656ff044ca9f8c0"),
    ("BENNY_V3", "BET#2026-03-17T01:11:32.281241#e18bb0c990005d46d98ab6ec89f2cfff"),
    ("BENNY_V3", "BET#2026-03-17T01:11:32.362361#e18bb0c990005d46d98ab6ec89f2cfff"),
    # V1 parlay
    ("BENNY", "BET#2026-03-16T13:05:58.218508#PARLAY"),
    # V3 parlay
    ("BENNY_V3", "BET#2026-03-16T15:34:29.651702#PARLAY"),
]

reset_count = 0
for pk, sk in items_to_reset:
    try:
        table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression="SET #s = :pending REMOVE payout, settled_at",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":pending": "pending"},
        )
        reset_count += 1
        print(f"Reset: {pk} | {sk}")
    except Exception as e:
        print(f"ERROR: {pk} | {sk} -> {e}")

print(f"\nDone. Reset {reset_count}/{len(items_to_reset)} items to pending.")
