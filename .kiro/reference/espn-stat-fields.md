# ESPN Stat Fields by Sport

## Basketball (NBA)
- 3PT
- Assists
- Blocks
- Defensive Rebounds
- FG
- FT
- Fast Break Points
- Field Goal %
- Flagrant Fouls
- Fouls
- Free Throw %
- Largest Lead
- Lead Changes
- Offensive Rebounds
- Percent Led
- Points Conceded Off Turnovers
- Points in Paint
- Rebounds
- Steals
- Team Turnovers
- Technical Fouls
- Three Point %
- Total Technical Fouls
- Total Turnovers
- Turnovers

**Used by Matchup Model:** Field Goal %, Defensive Rebounds

## Ice Hockey (NHL)
- Blocked Shots
- Faceoff Win Percent
- Faceoffs Won
- Giveaways
- Hits
- Penalty Minutes
- Power Play Goals
- Power Play Opportunities
- Power Play Percentage
- Shootout Goals
- Short Handed Goals
- Shots
- Takeaways
- Total Penalties

**Used by Matchup Model:** Shots, Power Play Percentage

## Soccer (EPL)
- Accurate Crosses
- Accurate Long Balls
- Accurate Passes
- Blocked Shots
- Clearances
- Corner Kicks
- Cross %
- Crosses
- Effective Clearances
- Effective Tackles
- Fouls
- Interceptions
- Long Balls
- Long Balls %
- ON GOAL (shots on goal)
- Offsides
- On Target %
- Pass Completion %
- Passes
- Penalty Goals
- Penalty Kicks Taken
- Possession
- Red Cards
- SHOTS
- Saves
- Tackle %
- Tackles
- Yellow Cards

**Used by Matchup Model:** ON GOAL, Effective Tackles

## American Football (NFL)
**Status:** No team stats collected yet

**Assumed fields for Matchup Model:** Total Yards, Turnovers

## Baseball (MLB)
**Status:** No team stats collected yet

**Assumed fields for Matchup Model:** Batting Average, ERA

## NCAA Basketball (NCAAB, WNCAAB)
**Status:** No team stats collected yet

**Assumed fields for Matchup Model:** Field Goal %, Defensive Rebounds (same as NBA)

## NCAA Football (NCAAF)
**Status:** No team stats collected yet

**Assumed fields for Matchup Model:** Total Yards, Turnovers (same as NFL)

## MLS Soccer
**Status:** No team stats collected yet

**Assumed fields for Matchup Model:** ON GOAL, Effective Tackles (same as EPL)

## WNBA Basketball
**Status:** No team stats collected yet

**Assumed fields for Matchup Model:** Field Goal %, Defensive Rebounds (same as NBA)

## Notes
- All stats are stored in a nested `stats` field in DynamoDB
- ESPN returns stats with exact label names (case-sensitive)
- Matchup model needs to be updated if ESPN uses different field names for NFL/MLB/NCAA
- Once games complete for missing sports, verify actual field names match assumptions
