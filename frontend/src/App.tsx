import React, { useState, useEffect, useCallback } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { bettingApi } from './services/api';
import { Game } from './types/betting';
import PlayerProps from './components/PlayerProps';
import BetInsights from './components/BetInsights';
import Settings from './components/Settings';
import ComplianceWrapper from './components/ComplianceWrapper';
import { ModelAnalytics } from './components/ModelAnalytics';
import Models from './components/Models';
import TermsOfService from './components/TermsOfService';
import PrivacyPolicy from './components/PrivacyPolicy';
import logo from './assets/carpool_bets_2.png';
import './amplifyConfig'; // Initialize Amplify
import '@aws-amplify/ui-react/styles.css';
import './amplify-theme.css';
import './App.css';

function Dashboard({ user, signOut }: { user: any; signOut?: () => void }) {
  const [games, setGames] = useState<Game[]>([]);
  const [gameAnalysis, setGameAnalysis] = useState<any[]>([]);
  const [propAnalysis, setPropAnalysis] = useState<any[]>([]);
  const [topInsight, setTopInsight] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'games' | 'game-analysis' | 'prop-analysis' | 'player-props' | 'insights' | 'models'>('games');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;
  const [marketFilter, setMarketFilter] = useState<string>('all');
  const [token, setToken] = useState<string>('');
  const [settings, setSettings] = useState({
    sport: 'basketball_nba',
    bookmaker: 'fanduel',
    model: 'consensus'
  });
  const [gameAnalysisKey, setGameAnalysisKey] = useState<string | null>(null);
  const [propAnalysisKey, setPropAnalysisKey] = useState<string | null>(null);
  const [loadingMoreGame, setLoadingMoreGame] = useState(false);
  const [loadingMoreProp, setLoadingMoreProp] = useState(false);
  const [gamesKey, setGamesKey] = useState<string | null>(null);
  const [loadingMoreGames, setLoadingMoreGames] = useState(false);

  useEffect(() => {
    const initializeData = async () => {
      try {
        const session = await fetchAuthSession();
        const idToken = session.tokens?.idToken?.toString();
        if (idToken) {
          setToken(idToken);
          // Only fetch data after token is set
          fetchGames();
          fetchGameAnalysis();
          fetchPropAnalysis();
          fetchTopInsight();
        }
      } catch (error) {
        console.error('Error getting auth session:', error);
      }
    };
    
    initializeData();
  }, []);

  // Refetch data when settings change
  useEffect(() => {
    if (token) {
      fetchGames();
      fetchGameAnalysis();
      fetchPropAnalysis();
      fetchTopInsight();
    }
  }, [settings, token]);

  const fetchGames = useCallback(async () => {
    try {
      setLoading(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const bookmaker = settings.bookmaker;
        const data = await bettingApi.getGames(token, sport, bookmaker);
        setGames(data.games || []);
        setGamesKey(data.lastEvaluatedKey || null);
      }
    } catch (err) {
      setError('Failed to fetch games');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [settings.sport, settings.bookmaker]);

  const loadMoreGames = async () => {
    if (!gamesKey || loadingMoreGames) return;
    
    try {
      setLoadingMoreGames(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const bookmaker = settings.bookmaker;
        const data = await bettingApi.getGames(token, sport, bookmaker, gamesKey);
        setGames(prev => [...prev, ...(data.games || [])]);
        setGamesKey(data.lastEvaluatedKey || null);
      }
    } catch (err) {
      console.error('Error loading more games:', err);
    } finally {
      setLoadingMoreGames(false);
    }
  };

  const fetchGameAnalysis = useCallback(async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const model = settings.model !== 'all' ? settings.model : undefined;
        const bookmaker = settings.bookmaker;
        const data = await bettingApi.getAnalyses(token, { sport, model, bookmaker, type: 'game', limit: 20 });
        setGameAnalysis(data.analyses || []);
        setGameAnalysisKey(data.lastEvaluatedKey || null);
      }
    } catch (err) {
      console.error('Error fetching game analysis:', err);
    }
  }, [settings.sport, settings.model, settings.bookmaker]);

  const fetchPropAnalysis = useCallback(async () => {
    try {
      console.log('fetchPropAnalysis called');
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const model = settings.model !== 'all' ? settings.model : undefined;
        const bookmaker = settings.bookmaker;
        console.log('Fetching prop analyses with:', { sport, model, bookmaker, type: 'prop' });
        const data = await bettingApi.getAnalyses(token, { sport, model, bookmaker, type: 'prop', limit: 20 });
        console.log('Prop analyses response:', data);
        setPropAnalysis(data.analyses || []);
        setPropAnalysisKey(data.lastEvaluatedKey || null);
      }
    } catch (err) {
      console.error('Error fetching prop analysis:', err);
      setPropAnalysis([]);
    }
  }, [settings.sport, settings.model, settings.bookmaker]);

  const loadMoreGameAnalysis = async () => {
    if (!gameAnalysisKey || loadingMoreGame) return;
    
    try {
      setLoadingMoreGame(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const model = settings.model !== 'all' ? settings.model : undefined;
        const bookmaker = settings.bookmaker;
        const data = await bettingApi.getAnalyses(token, { sport, model, bookmaker, type: 'game', limit: 20, lastEvaluatedKey: gameAnalysisKey });
        setGameAnalysis(prev => [...prev, ...(data.analyses || [])]);
        setGameAnalysisKey(data.lastEvaluatedKey || null);
      }
    } catch (err) {
      console.error('Error loading more game analysis:', err);
    } finally {
      setLoadingMoreGame(false);
    }
  };

  const loadMorePropAnalysis = async () => {
    if (!propAnalysisKey || loadingMoreProp) return;
    
    try {
      setLoadingMoreProp(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const model = settings.model !== 'all' ? settings.model : undefined;
        const bookmaker = settings.bookmaker;
        const data = await bettingApi.getAnalyses(token, { sport, model, bookmaker, type: 'prop', limit: 20, lastEvaluatedKey: propAnalysisKey });
        setPropAnalysis(prev => [...prev, ...(data.analyses || [])]);
        setPropAnalysisKey(data.lastEvaluatedKey || null);
      }
    } catch (err) {
      console.error('Error loading more prop analysis:', err);
    } finally {
      setLoadingMoreProp(false);
    }
  };

  const fetchTopInsight = useCallback(async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const bookmaker = settings.bookmaker;
        // No model filter - get top insight across all models
        const data = await bettingApi.getTopInsight(token, { sport, bookmaker, type: 'game' });
        setTopInsight(data.top_insight);
      }
    } catch (err) {
      console.error('Error fetching top insight:', err);
    }
  }, [settings.sport, settings.bookmaker]);

  // Games are already grouped by game_id from the API
  let filteredGames = games.filter(game => {
    // Skip games with invalid team names
    if (!game.home_team || !game.away_team || game.home_team.trim() === '' || game.away_team.trim() === '') {
      return false;
    }
    return true;
  });

  // Apply sport and bookmaker filters
  filteredGames = filteredGames.filter(game => 
    game.sport === settings.sport && 
    Object.keys(game.odds || {}).includes(settings.bookmaker)
  );

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
  const filteredGameAnalysis = gameAnalysis.filter((a: any) => 
    a.analysis_type === 'game' && a.home_team && a.away_team
  );
  const filteredPropAnalysis = propAnalysis.filter((p: any) => 
    p.player_name && p.prediction
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
    const result = games.map((game) => {
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
          <img src={logo} alt="Carpool Bets" className="logo" />
          <div className="header-info">
            <span>Welcome, {user?.signInDetails?.loginId}</span>
            <span>Environment: {process.env.REACT_APP_STAGE}</span>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => {
            fetchGames();
            fetchGameAnalysis();
            fetchPropAnalysis();
            fetchTopInsight();
          }}>
            Refresh Data
          </button>
          <button className="btn btn-primary" onClick={signOut}>
            Sign Out
          </button>
        </div>
      </header>
      
      {topInsight && (
        <div className="top-insight-banner">
          <div className="top-insight-header">
            <h2>🎯 Top Insight</h2>
            <span className="insight-badge">Highest Confidence</span>
          </div>
          <div className="top-insight-content">
            <div className="insight-game-info">
              <h3>{topInsight.away_team} @ {topInsight.home_team}</h3>
              <p className="game-time">{new Date(topInsight.commence_time).toLocaleString()}</p>
            </div>
            <div className="insight-prediction">
              <div className="prediction-box">
                <span className="prediction-label">Analysis Outcome: </span>
                <span className="prediction-value">{topInsight.prediction}</span>
              </div>
              <div className="confidence">
                <span className="confidence-label">Confidence</span>
                <span className="confidence-value">{(topInsight.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
            <div className="insight-details">
              <p className="reasoning">{topInsight.reasoning}</p>
              <div className="insight-meta">
                <span>Model: {topInsight.model}</span>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <Settings 
        settings={settings}
        onSettingsChange={setSettings}
        availableSports={['basketball_nba', 'americanfootball_nfl', 'baseball_mlb', 'icehockey_nhl', 'soccer_epl']}
        availableBookmakers={['draftkings', 'fanduel', 'betmgm', 'caesars']}
        token={token}
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
          <button 
            className={`tab-button ${activeTab === 'models' ? 'active' : ''}`}
            onClick={() => handleTabChange('models')}
          >
            Models
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
                return allGameCards.map((cardData: any) => {
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
            
            {gamesKey && (
              <div style={{ textAlign: 'center', marginTop: '20px' }}>
                <button 
                  onClick={loadMoreGames} 
                  disabled={loadingMoreGames}
                  style={{
                    padding: '10px 20px',
                    fontSize: '16px',
                    cursor: loadingMoreGames ? 'not-allowed' : 'pointer',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px'
                  }}
                >
                  {loadingMoreGames ? 'Loading...' : 'Load More'}
                </button>
              </div>
            )}
            
            {games.length === 0 && (
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
              {gameAnalysis.length > 0 ? (
                gameAnalysis.map((analysis: any, index: number) => (
                  <div key={index} className="game-card">
                    <div className="game-info">
                      <div className="teams">
                        <h3>{analysis.away_team} @ {analysis.home_team}</h3>
                        <div className="sport-tag">{formatSport(analysis.sport)}</div>
                      </div>
                    </div>
                    <div className="analysis-info">
                      <div className="analysis-row">
                        <span className="analysis-label">Analysis Outcome: </span>
                        <span className="analysis-value">{analysis.prediction}</span>
                      </div>
                      <div className="confidence-row">
                        <span className="confidence-label">Confidence: </span>
                        <span className="confidence-value">{(analysis.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div className="reasoning">
                        <span className="reasoning-label">Reasoning: </span>
                        <span className="reasoning-value">{analysis.reasoning}</span>
                      </div>
                    </div>
                    <div className="game-meta">
                      <span className="model">Model: {analysis.model}</span>
                      <span className="game-time">{new Date(analysis.commence_time).toLocaleString()}</span>
                    </div>
                  </div>
                ))
              ) : null
              }
            </div>
            
            {gameAnalysisKey && (
              <div style={{ textAlign: 'center', marginTop: '20px' }}>
                <button 
                  onClick={loadMoreGameAnalysis} 
                  disabled={loadingMoreGame}
                  style={{
                    padding: '10px 20px',
                    fontSize: '16px',
                    cursor: loadingMoreGame ? 'not-allowed' : 'pointer',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px'
                  }}
                >
                  {loadingMoreGame ? 'Loading...' : 'Load More'}
                </button>
              </div>
            )}
            
            {gameAnalysis.length === 0 && (
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
              {propAnalysis.length > 0 ? (
                propAnalysis.map((analysis: any, index: number) => (
                  <div key={index} className="game-card">
                    <div className="game-info">
                      <div className="teams">
                        <h3>{analysis.player_name}</h3>
                        <div className="sport-tag">{formatSport(analysis.sport)}</div>
                        <p className="game-time">{new Date(analysis.commence_time).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="prediction-info">
                      <div className="prediction-box">
                        <span className="prediction-label">Analysis Outcome: </span>
                        <span className="prediction-value">{analysis.prediction}</span>
                      </div>
                      <div className="confidence">
                        <span className="confidence-label">Confidence</span>
                        <span className="confidence-value">{(analysis.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="reasoning">
                      <span className="reasoning-label">Reasoning: </span>
                      <span>{analysis.reasoning}</span>
                    </div>
                    <div className="game-meta">
                      <span className="model">Model: {analysis.model}</span>
                      <span className="game-time">{new Date(analysis.commence_time).toLocaleString()}</span>
                    </div>
                  </div>
                ))
              ) : null
              }
            </div>
            
            {propAnalysisKey && (
              <div style={{ textAlign: 'center', marginTop: '20px' }}>
                <button 
                  onClick={loadMorePropAnalysis} 
                  disabled={loadingMoreProp}
                  style={{
                    padding: '10px 20px',
                    fontSize: '16px',
                    cursor: loadingMoreProp ? 'not-allowed' : 'pointer',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px'
                  }}
                >
                  {loadingMoreProp ? 'Loading...' : 'Load More'}
                </button>
              </div>
            )}
            
            {propAnalysis.length === 0 && (
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

        {activeTab === 'models' && (
          <Models token={token} settings={settings} />
        )}
      </main>
    </div>
  );
}

function App() {
  // Simple routing based on URL path
  const path = window.location.pathname;
  
  if (path === '/terms') {
    return <TermsOfService />;
  }
  
  if (path === '/privacy') {
    return <PrivacyPolicy />;
  }
  
  if (path === '/responsible-gambling') {
    return <ResponsibleGamblingPage />;
  }
  
  return (
    <Authenticator
      hideSignUp={true}
      loginMechanisms={['email']}
      components={{
        Header() {
          return (
            <img 
              src={logo} 
              alt="Carpool Bets" 
              style={{ 
                height: '160px',
                filter: 'drop-shadow(0 4px 16px rgba(0, 212, 255, 0.3))',
                opacity: '0.95',
                display: 'block',
                margin: '3rem auto 2rem'
              }} 
            />
          );
        },
        Footer() {
          return null;
        },
      }}
    >
      {({ signOut, user }) => (
        <ComplianceWrapper>
          <Dashboard user={user} signOut={signOut} />
        </ComplianceWrapper>
      )}
    </Authenticator>
  );
}

// Standalone Responsible Gambling page
function ResponsibleGamblingPage() {
  return (
    <div className="legal-page">
      <div className="legal-container">
        <h1>Responsible Gambling</h1>
        
        <section>
          <h2>⚠️ Important Gambling Warnings</h2>
          <ul>
            <li>Gambling can be addictive and harmful</li>
            <li>Never bet more than you can afford to lose</li>
            <li>Set limits on time and money spent gambling</li>
            <li>Don't chase losses with bigger bets</li>
            <li>Gambling is not a way to make money or solve financial problems</li>
          </ul>
        </section>

        <section>
          <h2>Get Help</h2>
          <div style={{ background: 'rgba(74, 158, 255, 0.1)', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
            <h3>National Problem Gambling Helpline</h3>
            <p style={{ fontSize: '2rem', color: '#4a9eff', fontWeight: 'bold', margin: '10px 0' }}>1-800-522-4700</p>
            <p>24/7 confidential support</p>
          </div>
          
          <h3>Additional Resources:</h3>
          <ul>
            <li><a href="https://www.ncpgambling.org" target="_blank" rel="noopener noreferrer">National Council on Problem Gambling</a></li>
            <li><a href="https://www.gamblersanonymous.org" target="_blank" rel="noopener noreferrer">Gamblers Anonymous</a></li>
            <li><a href="https://www.responsiblegambling.org" target="_blank" rel="noopener noreferrer">Responsible Gambling Council</a></li>
          </ul>
        </section>

        <section>
          <h2>Self-Help Tools</h2>
          <p>Consider using these tools to maintain control:</p>
          <ul>
            <li>Set daily, weekly, or monthly spending limits</li>
            <li>Use time limits for gambling sessions</li>
            <li>Take regular breaks from gambling</li>
            <li>Self-exclude from gambling sites if needed</li>
          </ul>
        </section>

        <section>
          <h2>Warning Signs of Problem Gambling</h2>
          <ul>
            <li>Spending more money or time gambling than you can afford</li>
            <li>Having arguments with family or friends about money and gambling</li>
            <li>Losing interest in usual activities or hobbies</li>
            <li>Feeling guilty or anxious about gambling</li>
            <li>Borrowing money or selling possessions to gamble</li>
            <li>Trying unsuccessfully to cut down or stop gambling</li>
          </ul>
        </section>

        <div style={{ textAlign: 'center', marginTop: '40px' }}>
          <a href="/" style={{ color: '#4a9eff', textDecoration: 'none', fontSize: '1.1rem' }}>← Back to Home</a>
        </div>
      </div>
    </div>
  );
}

export default App;
