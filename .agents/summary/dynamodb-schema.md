# DynamoDB Schema

> Single table design: `carpool-bets-v2-{env}`

## Key Patterns

### Bets
| pk | sk | Description |
|----|-----|-------------|
| `BENNY` | `BET#<timestamp>#<game_id>` | V1 bet record |
| `BENNY_V3` | `BET#<timestamp>#<game_id>` | V3 bet record |
| `BENNY` | `BET#<timestamp>#PARLAY` | V1 parlay bet |

Fields: `status` (pending/won/lost), `bet_amount`, `profit`, `confidence`, `prediction`, `ai_reasoning`, `ai_key_factors`, `sport`, `market_key`, `odds`, `settled_at`, `created_at`

### Bankroll
| pk | sk | Description |
|----|-----|-------------|
| `BENNY` | `BANKROLL` | V1 bankroll |
| `BENNY_V3` | `BANKROLL` | V3 bankroll |

Fields: `amount`, `updated_at`, `last_reset`

### Learning Data
| pk | sk | Description |
|----|-----|-------------|
| `{PK}#LEARNING` | `PARAMS` | Learning engine parameters |
| `{PK}#LEARNING` | `COACHING_MEMO` | Coaching memo + cooldowns map |
| `{PK}#LEARNING` | `FEATURES` | Feature importance insights |
| `{PK}#LEARNING` | `CALIBRATION` | Confidence calibration data |
| `{PK}#LEARNING` | `VARIANCE` | Variance tracking metrics |
| `{PK}#LEARNING` | `THRESHOLDS` | Adaptive confidence thresholds |

### System
| pk | sk | Description |
|----|-----|-------------|
| `SYSTEM` | `BENNY_LOCK` | Distributed execution lock |

### Odds
| pk | sk | Description |
|----|-----|-------------|
| `ODDS#{sport}` | `{game_id}#{bookmaker}#{market}` | Raw odds data |

### Player Stats
| pk | sk | Description |
|----|-----|-------------|
| `PLAYER_STATS#{sport}` | `{player_id}#{game_date}` | Per-game player stats |
