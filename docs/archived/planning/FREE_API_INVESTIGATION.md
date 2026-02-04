# Free Sports Data API Investigation

## 🎯 **Objective**
Replace paid SportsData.io ($100-200/month) with free alternatives while maintaining the same rich ML data for predictions.

## 🔍 **Investigation Status**
**Date**: December 29, 2025  
**Status**: Research phase - identifying truly free alternatives  
**Next**: Implementation planning

## ❌ **Ruled Out Options**

### MySportsFeeds
- **Initially Considered**: Appeared to have "free tier" 
- **Reality**: Personal use costs $3-15/month per league
- **Total Cost**: $12-60/month for 4 leagues (NFL, NBA, MLB, NHL)
- **Decision**: Too expensive, not truly free

## ✅ **Viable FREE Alternatives**

### 1. ESPN Hidden API ⭐ **PRIMARY**
- **Cost**: 100% FREE
- **Coverage**: NFL, NBA, MLB, NHL, Soccer, College
- **Data Available**:
  - Real-time scores and standings
  - Team information and detailed stats
  - Player data and profiles
  - News and updates
  - Historical game data

**Key Endpoints Documented**:
```
# Scores
https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard
https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard
https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard

# Teams & Stats
https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/:team

# News
https://site.api.espn.com/apis/site/v2/sports/football/nfl/news
```

**Quality**: ESPN's own data (very reliable)  
**Risk**: Unofficial API (could change without notice)  
**Mitigation**: Multiple fallback sources

### 2. API-SPORTS ⭐ **NEW DISCOVERY**
- **Cost**: FREE forever plan (upon registration)
- **Coverage**: 2,000+ competitions (Soccer, NBA, NFL, Formula 1)
- **Data Available**: All endpoints accessible
- **Quality**: Professional API with documentation
- **Advantage**: Official free tier vs unofficial ESPN API

### 3. TheSportsDB ⭐ **SUPPLEMENTARY**
- **Cost**: FREE (open, crowd-sourced)
- **Coverage**: Wide range of sports
- **API Key**: Test key "123" available
- **Data Available**:
  - Team rosters and information
  - Player profiles and stats
  - Event statistics
- **Quality**: Community-driven, good coverage

### 4. Sports Reference Scraping ⭐ **ADVANCED STATS**
- **Cost**: 100% FREE (web scraping)
- **Coverage**: NBA, NFL, MLB, NHL, College
- **Data Available**:
  - Historical statistics and trends
  - Advanced metrics and analytics
  - Player career profiles
  - Team performance data
  - Head-to-head records

**Python Libraries Available**:
- `sportsipy` - Scrapes Sports-Reference.com (NFL, NBA, MLB, NHL)
- `pybaseball` - Advanced baseball data (Statcast, Baseball-Reference, FanGraphs)
- Custom scrapers for other sports

**Quality**: Most comprehensive stats available  
**Risk**: Rate limiting, site changes  
**Mitigation**: Respectful scraping, caching

### 5. Football-Data.org ⭐ **SOCCER SPECIALIST**
- **Cost**: FREE tier available
- **Coverage**: Major European soccer leagues
- **Data Available**:
  - Fixtures and results
  - League tables and standings
  - Team and player statistics
- **Quality**: Specialized soccer data

## 🔄 **Proposed Hybrid Strategy**

### Data Source Mapping
| Data Type | Primary Source | Backup Source | Alternative | Current Source |
|-----------|---------------|---------------|-------------|----------------|
| **Betting Odds** | **The Odds API** ✅ | API-SPORTS | SportsGameOdds | The Odds API ✅ |
| **Real-time Scores** | ESPN Hidden API | API-SPORTS | TheSportsDB | None |
| **Team Stats** | ESPN Hidden API | API-SPORTS | Sports Reference | None |
| **Player Data** | Sports Reference | ESPN Hidden API | API-SPORTS | None |
| **Advanced Metrics** | Sports Reference (sportsipy) | ESPN Hidden API | PyBaseball | None |
| **Soccer Data** | Football-Data.org | API-SPORTS | ESPN Hidden API | None |
| **Injuries** | ESPN Hidden API | API-SPORTS | Sports Reference | None |
| **Weather** | ESPN Hidden API | OpenWeather API | - | None |
| **Referee Bias** | **Existing System** | - | - | ✅ 99.3% real data |

### Betting Odds Options Comparison
| API | Free Tier | Coverage | Bookmakers | Best For |
|-----|-----------|----------|------------|----------|
| **The Odds API** ✅ | 500 credits/month | 70+ sports | 40+ (DraftKings, FanDuel, BetMGM) | **Current choice - keep** |
| **API-SPORTS** | Free forever | 2,000+ competitions | Included in endpoints | Backup/expansion |
| **SportsGameOdds** | Free trial | 25+ sports, 55+ leagues | Multiple bookmakers | Alternative |
| **Sportmonks** | Free developer plan | Real-time scores + odds | Multiple | Testing |

### Implementation Priority
1. **API-SPORTS** - Test official free tier (reliable, 2,000+ competitions)
2. **TheSportsDB** - Implement stable backup (test key "123")
3. **Sports Reference (sportsipy)** - Implement advanced metrics (stable library)
4. **Football-Data.org** - Implement soccer data (official API)
5. **Fallback system** - ESPN Hidden API as emergency backup only
6. **Unified Client** - Combine all sources with reliability tiers
7. **Replace SportsData.io** - Remove paid dependency

## 🎯 **RELIABLE STRATEGY: Official APIs + Backups**

### Primary Sources (Official/Reliable) ⭐
1. **The Odds API** ✅ - Keep existing (500 credits/month, official)
2. **API-SPORTS** 🆓 - Free forever plan (official, 2,000+ competitions)
3. **TheSportsDB** 🆓 - Open API with test key "123" (stable)
4. **Football-Data.org** 🆓 - Official soccer API (free tier)
5. **Sports Reference (sportsipy)** 🆓 - Python library (stable scraping)

### Backup Sources (Use if needed) ⚠️
6. **ESPN Hidden API** - Unofficial (use as last resort)
7. **SportsGameOdds** - Free trial (backup for odds)
8. **Sportmonks** - Free developer plan (backup)

### Data Source Priority Matrix
| Data Type | Primary | Secondary | Tertiary | Risk Level |
|-----------|---------|-----------|----------|------------|
| **Betting Odds** | The Odds API ✅ | SportsGameOdds | API-SPORTS | LOW |
| **Team Stats** | API-SPORTS | TheSportsDB | ESPN Hidden | LOW |
| **Player Data** | API-SPORTS | sportsipy | ESPN Hidden | LOW |
| **Scores** | API-SPORTS | TheSportsDB | ESPN Hidden | LOW |
| **Soccer Data** | Football-Data.org | API-SPORTS | ESPN Hidden | LOW |
| **Advanced Stats** | sportsipy | API-SPORTS | ESPN Hidden | LOW |
| **Injuries** | API-SPORTS | ESPN Hidden | Manual scraping | MEDIUM |
| **Weather** | OpenWeather API | ESPN Hidden | Manual lookup | MEDIUM |
| **Referee Bias** | **Existing System** ✅ | - | - | NONE |

## 🛡️ **Reliability Strategy**

### Tier 1: Official APIs (Highest Reliability)
- **API-SPORTS**: Official free forever plan
- **The Odds API**: Official paid service (already using)
- **TheSportsDB**: Established open API
- **Football-Data.org**: Official soccer API

### Tier 2: Stable Libraries (High Reliability)  
- **sportsipy**: Mature Python library for Sports Reference
- **pybaseball**: Established baseball data library

### Tier 3: Unofficial/Backup (Use Sparingly)
- **ESPN Hidden API**: Only as fallback
- **Manual scraping**: Emergency backup only

## 📋 **Implementation Priority (Reliability-First)**

1. **API-SPORTS Integration** - Primary free source (official)
2. **TheSportsDB Integration** - Backup team/player data  
3. **sportsipy Integration** - Advanced stats (stable library)
4. **Football-Data.org** - Soccer specialization
5. **Fallback Logic** - ESPN Hidden API as last resort only

## 💰 **Updated Cost Analysis**

| Component | Current Cost | Enhanced Cost | Savings vs SportsData.io |
|-----------|-------------|---------------|-------------------------|
| **Betting Odds** | The Odds API | The Odds API | Keep existing |
| **Team/Player Data** | None | FREE (API-SPORTS) | $100-200/month saved |
| **Advanced Stats** | None | FREE (sportsipy) | Included above |
| **Referee Data** | FREE ✅ | FREE ✅ | Already have |
| **Total** | Current spend | **$0 additional** | **$1,200-2,400/year** |

## 📋 **Next Steps When Resuming**

### Immediate Tasks
1. **Complete Task 1**: Document this research (✅ DONE)
2. **Start Task 2**: Implement ESPN Hidden API client
3. **Test ESPN endpoints**: Verify data quality and structure
4. **Create data mapping**: Map ESPN data to our enhanced schema

### Implementation Plan
1. **Phase 1**: ESPN Hidden API integration
2. **Phase 2**: Sports Reference scraping
3. **Phase 3**: Unified data aggregator
4. **Phase 4**: Replace SportsData.io completely
5. **Phase 5**: Clean up and testing

## 🎯 **Expected Outcome**
- ✅ **$1,200-2,400/year savings**
- ✅ Same rich ML data (team stats, injuries, weather)
- ✅ Multiple data sources for reliability
- ✅ No vendor lock-in
- ✅ Enhanced data for better predictions

## 📝 **Current TODO Status**
**TODO ID**: 1767046314408  
**Progress**: 1/8 tasks completed  
**Next Task**: Implement ESPN Hidden API client

---
*Investigation paused - ready to resume implementation when you return!*
