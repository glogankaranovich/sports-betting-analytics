/**
 * Platform-wide constants for sports, models, bookmakers, etc.
 * These are passed as environment variables to Lambda functions.
 */

export const PLATFORM_CONSTANTS = {
  SUPPORTED_SPORTS: 'basketball_nba,americanfootball_nfl,baseball_mlb,icehockey_nhl,soccer_epl,basketball_mens-college-basketball,basketball_womens-college-basketball,football_college-football',
  SYSTEM_MODELS: 'consensus,value,momentum,contrarian,hot_cold,rest_schedule,matchup,injury_aware,news,player_stats,ensemble,fundamentals',
  SUPPORTED_BOOKMAKERS: 'draftkings,fanduel,betmgm,caesars',
  TIME_RANGES: '30,90,180,365',
};

/**
 * Get environment variables object for Lambda functions
 */
export function getPlatformEnvironment(): Record<string, string> {
  return {
    SUPPORTED_SPORTS: PLATFORM_CONSTANTS.SUPPORTED_SPORTS,
    SYSTEM_MODELS: PLATFORM_CONSTANTS.SYSTEM_MODELS,
    SUPPORTED_BOOKMAKERS: PLATFORM_CONSTANTS.SUPPORTED_BOOKMAKERS,
    TIME_RANGES: PLATFORM_CONSTANTS.TIME_RANGES,
  };
}
