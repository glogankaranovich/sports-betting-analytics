import React, { useState, useEffect, useCallback } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { bettingApi } from './services/api';
import { Game } from './types/betting';
import PlayerProps from './components/PlayerProps';
import BetInsights from './components/BetInsights';
import Settings from './components/Settings';
import ComplianceWrapper from './components/ComplianceWrapper';
import './amplifyConfig'; // Initialize Amplify
import '@aws-amplify/ui-react/styles.css';
import './App.css';

function Dashboard({ user, signOut }: { user: any; signOut?: () => void }) {
  const [games, setGames] = useState<Game[]>([]);
  const [gameAnalysis, setGameAnalysis] = useState<any[]>([]);
  const [propAnalysis, setPropAnalysis] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'games' | 'game-analysis' | 'prop-analysis' | 'player-props' | 'insights'>('games');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;
  const [marketFilter, setMarketFilter] = useState<string>('all');
  const [token, setToken] = useState<string>('');
  const [settings, setSettings] = useState({
    sport: 'basketball_nba',
    bookmaker: 'fanduel',
    model: 'consensus',
    riskTolerance: 'moderate'
  });

  useEffect(() => {
    const getToken = async () => {
      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken?.toString();
      if (idToken) {
        setToken(idToken);
      }
    };
    
    getToken();
    fetchGames();
    fetchGameAnalysis();
    fetchPropAnalysis();
  }, []);

  // Refetch data when settings change
  useEffect(() => {
    if (token) {
      fetchGames();
      fetchGameAnalysis();
      fetchPropAnalysis();
    }
  }, [settings, token]);

  const fetchGames = useCallback(async () => {
    try {
      setLoading(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport !== 'all' ? settings.sport : undefined;
        const bookmaker = settings.bookmaker !== 'all' ? settings.bookmaker : undefined;
        const data = await bettingApi.getGames(token, sport, bookmaker);
        setGames(data.games || []);
      }
    } catch (err) {
      setError('Failed to fetch games');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [settings.sport, settings.bookmaker]);

  const fetchGameAnalysis = useCallback(async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport !== 'all' ? settings.sport : undefined;
        const bookmaker = settings.bookmaker !== 'all' ? settings.bookmaker : 'fanduel';
        const data = await bettingApi.getGamePredictions(token, sport, bookmaker);
        setGameAnalysis(data.predictions || []);
      }
    } catch (err) {
      console.error('Error fetching game analysis:', err);
    }
  }, [settings.sport, settings.bookmaker]);

  const fetchPropAnalysis = useCallback(async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport !== 'all' ? settings.sport : undefined;
        const data = await bettingApi.getPropPredictions(token, sport);
        setPropAnalysis(data.predictions || []);
      }
    } catch (err) {
      console.error('Error fetching prop analysis:', err);
    }
  }, [settings.sport]);

  // Games are already grouped by game_id from the API
  let filteredGames = games.filter(game => {
    // Skip games with invalid team names
    if (!game.home_team || !game.away_team || game.home_team.trim() === '' || game.away_team.trim() === '') {
      return false;
    }
    return true;
  });

  // Apply sport filter using settings
  if (settings.sport !== 'all') {
    filteredGames = filteredGames.filter(game => game.sport === settings.sport);
  }

  // Apply bookmaker filter using settings
  if (settings.bookmaker !== 'all') {
    filteredGames = filteredGames.filter(game => 
      Object.keys(game.odds || {}).includes(settings.bookmaker)
    );
  }

  // Get unique sports and bookmakers for filter options (keeping for potential future use)
  // const uniqueSports = Array.from(new Set(games.map(game => game.sport).filter(Boolean)));
  // const uniqueBookmakers = Array.from(new Set(
  //   games.flatMap(game => Object.keys(game.odds || {}))
  // ));


  const formatSport = (sport: string) => {
    if (!sport) return 'UNKNOWN';
    return sport.replace('americanfootball_', '').toUpperCase();
  };

  // Separate game and prop analysis using new schema
  const filteredGameAnalysis = gameAnalysis.filter((p: any) => 
    p.home_team && p.away_team && p.sport
  );
  const filteredPropAnalysis = propAnalysis.filter((p: any) => 
    p.player_name && p.prop_type
  );

  // Pagination logic
  const paginateItems = (items: any[], page: number) => {
    const startIndex = (page - 1) * itemsPerPage;
    return items.slice(startIndex, startIndex + itemsPerPage);
  };

  const getTotalPages = (items: any[]) => Math.ceil(items.length / itemsPerPage);

  // Reset to page 1 when switching tabs
  const handleTabChange = (tab: typeof activeTab) => {
    setActiveTab(tab);
    setCurrentPage(1);
  };

  // Generate all game cards for pagination
  const generateGameCards = () => {
    const result = filteredGames.map((game) => {
      const availableBookmakers = Object.keys(game.odds || {});
      
      const displayBookmakers = availableBookmakers.filter(bookmaker => bookmaker === settings.bookmaker);
      
      if (displayBookmakers.length === 0) return null;

      // Collect all bet types data for this game
      const allMarkets = ['h2h', 'spreads', 'totals'] as const;
      const marketsToShow = marketFilter === 'all' ? allMarkets : [marketFilter as any];
      
      const gameMarkets: any = {};
      marketsToShow.forEach(market => {
        const bookmakerOdds = displayBookmakers
          .map(bookmaker => ({ name: bookmaker, odds: game.odds[bookmaker]?.[market] }))
          .filter(item => item.odds);
        
        if (bookmakerOdds.length > 0) {
          gameMarkets[market] = bookmakerOdds;
        }
      });

      // Only return if we have at least one market with data
      if (Object.keys(gameMarkets).length === 0) return null;

      return { game, markets: gameMarkets, key: game.game_id };
    }).filter(Boolean);
    
    return result;
  };

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : `${odds}`;
  };

  if (loading) return <div className="loading">Loading games...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-left">
          <h1>Carpool Bets</h1>
          <div className="header-info">
            <span>Welcome {user?.signInDetails?.loginId}</span>
            <span>•</span>
            <span>Stage: {process.env.REACT_APP_STAGE}</span>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => {
            fetchGames();
            fetchGameAnalysis();
            fetchPropAnalysis();
          }}>
            Refresh Data
          </button>
          <button className="btn btn-primary" onClick={signOut}>
            Sign Out
          </button>
        </div>
      </header>
      
      <Settings 
        settings={settings}
        onSettingsChange={setSettings}
        availableSports={['basketball_nba', 'americanfootball_nfl']}
        availableBookmakers={['draftkings', 'fanduel', 'betmgm', 'caesars']}
      />
      
      <main>
        <div className="tab-navigation">
          <button 
            className={`tab-button ${activeTab === 'games' ? 'active' : ''}`}
            onClick={() => handleTabChange('games')}
          >
            Game Bets
          </button>
          <button 
            className={`tab-button ${activeTab === 'player-props' ? 'active' : ''}`}
            onClick={() => handleTabChange('player-props')}
          >
            Prop Bets
          </button>
          <button 
            className={`tab-button ${activeTab === 'game-analysis' ? 'active' : ''}`}
            onClick={() => handleTabChange('game-analysis')}
          >
            Game Analysis
          </button>
          <button 
            className={`tab-button ${activeTab === 'prop-analysis' ? 'active' : ''}`}
            onClick={() => handleTabChange('prop-analysis')}
          >
            Prop Analysis
          </button>
          <button 
            className={`tab-button ${activeTab === 'insights' ? 'active' : ''}`}
            onClick={() => handleTabChange('insights')}
          >
            Insights
          </button>
        </div>

        {activeTab === 'games' && (
          <>
            <div className="games-header">
              <h2>Available Games</h2>
              <div className="filters">
                <select 
                  className="filter-select"
                  value={marketFilter} 
                  onChange={(e) => setMarketFilter(e.target.value)}
                >
                  <option key="all-markets" value="all">All Bet Types</option>
                  <option key="h2h" value="h2h">Moneyline</option>
                  <option key="spreads" value="spreads">Spread</option>
                  <option key="totals" value="totals">Total</option>
                </select>
              </div>
            </div>
            
            <div className="games-grid">
              {(() => {
                const allGameCards = generateGameCards();
                return paginateItems(allGameCards, currentPage).map((cardData: any) => {
                  const { game, markets, key } = cardData;
                  const marketLabels: Record<string, string> = { h2h: 'Moneyline', spreads: 'Spread', totals: 'Total' };
                  
                  return (
                    <div key={key} className="game-card">
                      <div className="game-header">
                        <div className="teams">
                          <h3>{game.away_team} @ {game.home_team}</h3>
                          <div className="sport-tag">{formatSport(game.sport)}</div>
                          <p className="game-time">{new Date(game.commence_time).toLocaleString()}</p>
                        </div>
                      </div>
                      
                      {Object.entries(markets).map(([market, bookmakerOdds]: [string, any]) => (
                        <div key={market} className="odds-section">
                          <div className="odds-header">
                            <span className="odds-label">{marketLabels[market]} Odds</span>
                          </div>
                          <div className="bookmaker-odds">
                            {bookmakerOdds.map((bookmaker: any) => (
                              <div key={`${game.game_id}-${bookmaker.name}-${market}`} className="bookmaker-row">
                                <div className="odds-values">
                                  {bookmaker.odds?.map((outcome: any) => (
                                    <span key={outcome.name} className={`odds-value ${outcome.name === game.home_team ? 'home' : 'away'}`}>
                                      {outcome.name}: {formatOdds(outcome.price)}
                                      {outcome.point && ` (${outcome.point > 0 ? '+' : ''}${outcome.point})`}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                });
              })()}
            </div>
            {(() => {
              const allGameCards = generateGameCards();
              return allGameCards.length > itemsPerPage && (
                <div className="pagination">
                  <button 
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </button>
                  <span>Page {currentPage} of {getTotalPages(allGameCards)}</span>
                  <button 
                    onClick={() => setCurrentPage(Math.min(getTotalPages(allGameCards), currentPage + 1))}
                    disabled={currentPage === getTotalPages(allGameCards)}
                  >
                    Next
                  </button>
                </div>
              );
            })()}
            
            {filteredGames.length === 0 && (
              <div className="no-data">No games found for current filters</div>
            )}
          </>
        )}

        {activeTab === 'game-analysis' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>Game Analysis</h2>

            </div>
            <div className="games-grid">
              {filteredGameAnalysis.length > 0 ? (
                paginateItems(filteredGameAnalysis, currentPage).map((prediction: any, index: number) => (
                  <div key={index} className="game-card">
                    <div className="game-info">
                      <div className="teams">
                        <h3>{prediction.away_team} @ {prediction.home_team}</h3>
                        <div className="sport-tag">{formatSport(prediction.sport)}</div>
                        <p className="game-time">{new Date(prediction.commence_time).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="prediction-info">
                      <div className="probabilities">
                        <div className="prob-item">
                          <span className="prob-label">Home Win</span>
                          <span className="prob-value home">{(prediction.home_win_probability * 100).toFixed(1)}%</span>
                        </div>
                        <div className="prob-item">
                          <span className="prob-label">Away Win</span>
                          <span className="prob-value away">{(prediction.away_win_probability * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                      <div className="confidence">
                        <span className="confidence-label">Confidence</span>
                        <span className="confidence-value">{(prediction.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="game-meta">
                      <span className="model">Model: {prediction.model}</span>
                    </div>
                  </div>
                ))
              ) : null
              }
            </div>
            {filteredGameAnalysis.length > itemsPerPage && (
              <div className="pagination">
                <button 
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </button>
                <span>Page {currentPage} of {getTotalPages(filteredGameAnalysis)}</span>
                <button 
                  onClick={() => setCurrentPage(Math.min(getTotalPages(filteredGameAnalysis), currentPage + 1))}
                  disabled={currentPage === getTotalPages(filteredGameAnalysis)}
                >
                  Next
                </button>
              </div>
            )}
            
            {filteredGameAnalysis.length === 0 && (
              <div className="no-data">No game analysis items found for current filters</div>
            )}
          </div>
        )}

        {activeTab === 'prop-analysis' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>Player Prop Analysis</h2>

            </div>
            <div className="games-grid">
              {filteredPropAnalysis.length > 0 ? (
                paginateItems(filteredPropAnalysis, currentPage).map((prediction: any, index: number) => (
                  <div key={index} className="game-card">
                    <div className="game-info">
                      <div className="teams">
                        <h3>{prediction.player_name} - {prediction.prop_type}</h3>
                        <div className="sport-tag">{prediction.gameMatchup || formatSport(prediction.sport)}</div>
                        <p className="game-time">{new Date(prediction.commence_time).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="prediction-info">
                      <div className="probabilities">
                        <div className="prob-item">
                          <span className="prob-label">Over {prediction.predicted_value}</span>
                          <span className="prob-value home">{(prediction.over_probability * 100).toFixed(1)}%</span>
                        </div>
                        <div className="prob-item">
                          <span className="prob-label">Under {prediction.predicted_value}</span>
                          <span className="prob-value away">{(prediction.under_probability * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                      <div className="confidence">
                        <span className="confidence-label">Confidence</span>
                        <span className="confidence-value">{(prediction.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="game-meta">
                      <span className="model">Model: {prediction.model}</span>
                    </div>
                  </div>
                ))
              ) : null
              }
            </div>
            {filteredPropAnalysis.length > itemsPerPage && (
              <div className="pagination">
                <button 
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </button>
                <span>Page {currentPage} of {getTotalPages(filteredPropAnalysis)}</span>
                <button 
                  onClick={() => setCurrentPage(Math.min(getTotalPages(filteredPropAnalysis), currentPage + 1))}
                  disabled={currentPage === getTotalPages(filteredPropAnalysis)}
                >
                  Next
                </button>
              </div>
            )}
            
            {filteredPropAnalysis.length === 0 && (
              <div className="no-data">No prop analysis items found for current filters</div>
            )}
          </div>
        )}

        {activeTab === 'player-props' && (
          <PlayerProps 
            token={token} 
            games={games}
            currentPage={currentPage}
            itemsPerPage={itemsPerPage}
            onPageChange={setCurrentPage}
            settings={settings}
          />
        )}

        {activeTab === 'insights' && (
          <BetInsights token={token} settings={settings} />
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <ComplianceWrapper>
      <Authenticator>
        {({ signOut, user }) => (
          <Dashboard user={user} signOut={signOut} />
        )}
      </Authenticator>
    </ComplianceWrapper>
  );
}

export default App;
