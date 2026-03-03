# Sports Coverage

**Last Updated:** March 3, 2026

## Supported Sports

The platform supports **10 sports** across multiple leagues:

### Basketball (4 leagues)
- **NBA** - National Basketball Association
- **WNBA** - Women's National Basketball Association  
- **NCAAB** - NCAA Men's Basketball
- **WNCAAB** - NCAA Women's Basketball

### Football (2 leagues)
- **NFL** - National Football League
- **NCAAF** - NCAA Football

### Other Sports (4 leagues)
- **MLB** - Major League Baseball
- **NHL** - National Hockey League
- **EPL** - English Premier League (Soccer)
- **MLS** - Major League Soccer

## Sport Keys

Internal sport identifiers used throughout the system:

| Sport | Key | Type |
|-------|-----|------|
| NBA | `basketball_nba` | Basketball |
| WNBA | `basketball_wnba` | Basketball |
| NCAA Men's Basketball | `basketball_ncaab` | Basketball |
| NCAA Women's Basketball | `basketball_wncaab` | Basketball |
| NFL | `americanfootball_nfl` | Football |
| NCAA Football | `americanfootball_ncaaf` | Football |
| MLB | `baseball_mlb` | Baseball |
| NHL | `icehockey_nhl` | Hockey |
| EPL | `soccer_epl` | Soccer |
| MLS | `soccer_usa_mls` | Soccer |

## Data Collection Coverage

### Odds Collection
All 10 sports have:
- ✅ Moneyline (h2h) odds
- ✅ Point spreads
- ✅ Totals (over/under)
- ✅ Multiple bookmakers (DraftKings, FanDuel, BetMGM, Caesars)

### Player Statistics
- ✅ **NBA** - Full player stats via ESPN API
- ✅ **NFL** - Full player stats via ESPN API
- ⚠️ **Other sports** - Limited or no player stats currently

### Team Statistics
- ✅ **All 10 sports** - Team-level statistics via ESPN API

### Injury Reports
- ✅ **All 10 sports** - Injury tracking and impact analysis
- Supported by `injury_collector.py`
- Used by `InjuryAwareModel` for predictions

### Schedule & Results
- ✅ **All 10 sports** - Game schedules and outcomes
- Collected via The Odds API

## Model Support by Sport

### Game Predictions
All 12 ML models support all 10 sports:
- ✅ Fundamentals Model
- ✅ Matchup Model
- ✅ Momentum Model
- ✅ Value Model
- ✅ HotCold Model
- ✅ RestSchedule Model
- ✅ InjuryAware Model
- ✅ Contrarian Model
- ✅ News Model
- ✅ Ensemble Model
- ✅ Consensus Model
- ✅ PlayerStats Model (game analysis only)

### Prop Predictions
Player prop predictions currently supported for:
- ✅ **NBA** - Points, rebounds, assists, threes, etc.
- ✅ **NFL** - Passing yards, rushing yards, touchdowns, etc.
- ⚠️ **Other sports** - Limited prop support

Models supporting props:
- PlayerStats Model (NBA/NFL only)
- HotCold Model (all sports with player data)
- InjuryAware Model (all sports)
- Contrarian Model (all sports)

## Benny Trading Agent

Benny supports all 10 sports:
- ✅ Analyzes games across all leagues
- ✅ Places virtual bets on any sport
- ✅ Tracks performance by sport
- ✅ AI reasoning via Claude 3.5 Sonnet

## Season Coverage

Active seasons by sport (approximate):

| Sport | Season | Months |
|-------|--------|--------|
| NBA | October - June | 10-6 |
| WNBA | May - October | 5-10 |
| NCAAB | November - April | 11-4 |
| WNCAAB | November - April | 11-4 |
| NFL | September - February | 9-2 |
| NCAAF | August - January | 8-1 |
| MLB | March - October | 3-10 |
| NHL | October - June | 10-6 |
| EPL | August - May | 8-5 |
| MLS | February - November | 2-11 |

## Future Expansion

Potential sports to add:
- 🔮 **NCAAW** - NCAA Women's Softball
- 🔮 **CFL** - Canadian Football League
- 🔮 **La Liga** - Spanish Soccer
- 🔮 **Bundesliga** - German Soccer
- 🔮 **Serie A** - Italian Soccer
- 🔮 **Ligue 1** - French Soccer
- 🔮 **Champions League** - European Soccer
- 🔮 **UFC/MMA** - Mixed Martial Arts
- 🔮 **Tennis** - ATP/WTA Tours
- 🔮 **Golf** - PGA Tour

## Configuration

Sports are configured in `backend/constants.py`:

```python
SUPPORTED_SPORTS = [
    "basketball_nba",
    "basketball_wnba", 
    "basketball_ncaab",
    "basketball_wncaab",
    "americanfootball_nfl",
    "americanfootball_ncaaf",
    "baseball_mlb",
    "icehockey_nhl",
    "soccer_epl",
    "soccer_usa_mls"
]
```

## API Endpoints

All API endpoints support filtering by sport:
- `GET /games?sport=basketball_nba`
- `GET /odds?sport=americanfootball_nfl`
- `GET /analyses?sport=baseball_mlb`
- `GET /benny/dashboard` (shows all sports)

## Notes

- Injury collection was expanded to all 10 sports in March 2026
- InjuryAware model now has team ID mappings for all 10 sports
- Player prop support is limited to NBA/NFL due to data availability
- All game-level predictions work across all 10 sports
