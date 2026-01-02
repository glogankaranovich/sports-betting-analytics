import React, { useState, useEffect } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { bettingApi } from './services/api';
import { Game } from './types/betting';
import PlayerProps from './components/PlayerProps';
import './amplifyConfig'; // Initialize Amplify
import '@aws-amplify/ui-react/styles.css';
import './App.css';

function Dashboard({ user, signOut }: { user: any; signOut?: () => void }) {
  const [games, setGames] = useState<Game[]>([]);
  const [gamePredictions, setGamePredictions] = useState<any[]>([]);
  const [propPredictions, setPropPredictions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sportFilter, setSportFilter] = useState<string>('all');
  const [bookmakerFilter, setBookmakerFilter] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<'games' | 'game-predictions' | 'prop-predictions' | 'player-props'>('games');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;
  const [marketFilter, setMarketFilter] = useState<string>('all');
  const [token, setToken] = useState<string>('');

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
    fetchGamePredictions();
    fetchPropPredictions();
  }, []);

  const fetchGames = async () => {
    try {
      setLoading(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const data = await bettingApi.getGames(token);
        setGames(data.games || []);
      }
    } catch (err) {
      setError('Failed to fetch games');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchGamePredictions = async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const data = await bettingApi.getGamePredictions(token);
        setGamePredictions(data.predictions || []);
      }
    } catch (err) {
      console.error('Error fetching game predictions:', err);
    }
  };

  const fetchPropPredictions = async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const data = await bettingApi.getPropPredictions(token, 1000); // Fetch up to 1000 prop predictions
        setPropPredictions(data.predictions || []);
      }
    } catch (err) {
      console.error('Error fetching prop predictions:', err);
    }
  };

  // Games are already grouped by game_id from the API
  let filteredGames = games.filter(game => {
    // Skip games with invalid team names
    if (!game.home_team || !game.away_team || game.home_team.trim() === '' || game.away_team.trim() === '') {
      return false;
    }
    return true;
  });

  // Apply sport filter
  if (sportFilter !== 'all') {
    filteredGames = filteredGames.filter(game => game.sport === sportFilter);
  }

  // Apply bookmaker filter
  if (bookmakerFilter !== 'all') {
    filteredGames = filteredGames.filter(game => 
      Object.keys(game.odds || {}).includes(bookmakerFilter)
    );
  }

  // Get unique sports and bookmakers for filter options
  const uniqueSports = Array.from(new Set(games.map(game => game.sport).filter(Boolean)));
  const uniqueBookmakers = Array.from(new Set(
    games.flatMap(game => Object.keys(game.odds || {}))
  ));


  const formatSport = (sport: string) => {
    if (!sport) return 'UNKNOWN';
    return sport.replace('americanfootball_', '').toUpperCase();
  };

  // Separate game and prop predictions using new schema
  const filteredGamePredictions = gamePredictions.filter(p => 
    p.home_team && p.away_team && p.sport
  );
  const filteredPropPredictions = propPredictions.filter(p => 
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
    return filteredGames.flatMap((game) => {
      const availableBookmakers = Object.keys(game.odds || {});
      const displayBookmakers = bookmakerFilter === 'all' 
        ? availableBookmakers 
        : availableBookmakers.filter(bookmaker => bookmaker === bookmakerFilter);
      
      const markets = ['h2h', 'spreads', 'totals'] as const;
      const marketLabels: Record<string, string> = { h2h: 'Moneyline', spreads: 'Spread', totals: 'Total' };
      const filteredMarkets = marketFilter === 'all' ? markets : markets.filter(market => market === marketFilter);
      
      return filteredMarkets.map(market => {
        const bookmakerOdds = displayBookmakers
          .map(bookmaker => ({ name: bookmaker, odds: game.odds[bookmaker]?.[market] }))
          .filter(item => item.odds);
        
        if (bookmakerOdds.length === 0) return null;
        
        return { game, market, bookmakerOdds, key: `${game.game_id}-${market}` };
      }).filter(Boolean);
    }).filter(Boolean);
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
            fetchGamePredictions();
            fetchPropPredictions();
          }}>
            Refresh Data
          </button>
          <button className="btn btn-primary" onClick={signOut}>
            Sign Out
          </button>
        </div>
      </header>
      
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
            className={`tab-button ${activeTab === 'game-predictions' ? 'active' : ''}`}
            onClick={() => handleTabChange('game-predictions')}
          >
            Game Predictions ({filteredGamePredictions.length})
          </button>
          <button 
            className={`tab-button ${activeTab === 'prop-predictions' ? 'active' : ''}`}
            onClick={() => handleTabChange('prop-predictions')}
          >
            Prop Predictions ({filteredPropPredictions.length})
          </button>
        </div>

        {activeTab === 'games' && (
          <>
            <div className="games-header">
              <h2>Available Games</h2>
              <div className="filters">
                <select 
                  className="filter-select"
                  value={sportFilter} 
                  onChange={(e) => setSportFilter(e.target.value)}
                >
                  <option key="all-sports" value="all">All Sports</option>
                  {uniqueSports.map((sport, index) => (
                    <option key={`sport-${sport}-${index}`} value={sport}>
                      {formatSport(sport)}
                    </option>
                  ))}
                </select>
                <select 
                  className="filter-select"
                  value={bookmakerFilter} 
                  onChange={(e) => setBookmakerFilter(e.target.value)}
                >
                  <option key="all-bookmakers" value="all">All Bookmakers</option>
                  {uniqueBookmakers.map((bookmaker, index) => (
                    <option key={`bookmaker-${bookmaker}-${index}`} value={bookmaker}>
                      {bookmaker}
                    </option>
                  ))}
                </select>
                
                <select 
                  className="filter-select"
                  value={marketFilter} 
                  onChange={(e) => setMarketFilter(e.target.value)}
                >
                  <option key="all-markets" value="all">All Markets</option>
                  <option key="h2h" value="h2h">Moneyline</option>
                  <option key="spreads" value="spreads">Spread</option>
                  <option key="totals" value="totals">Total</option>
                </select>
              </div>
            </div>
            
            <div className="games-grid">
              {(() => {
                const allGameCards = generateGameCards();
                if (allGameCards.length === 0) {
                  return <div className="no-data">No games found for current filters</div>;
                }
                
                return paginateItems(allGameCards, currentPage).map((cardData: any) => {
                  const { game, market, bookmakerOdds, key } = cardData;
                  const marketLabels: Record<string, string> = { h2h: 'Moneyline', spreads: 'Spread', totals: 'Total' };
                  
                  return (
                    <div key={key} className="game-card">
                      <div className="game-header">
                        <div className="teams">
                          <h3>{game.away_team} @ {game.home_team}</h3>
                          <div className="sport-tag">{formatSport(game.sport)}</div>
                        </div>
                        <div className="game-meta">
                          <div className="bookmaker-count">{bookmakerOdds.length} bookmaker{bookmakerOdds.length !== 1 ? 's' : ''}</div>
                        </div>
                      </div>
                      
                      <div className="odds-section">
                        <div className="odds-header">
                          <span className="odds-label">{marketLabels[market]} Odds</span>
                        </div>
                        <div className="bookmaker-odds">
                          {bookmakerOdds.map((bookmaker: any) => (
                            <div key={`${game.game_id}-${bookmaker.name}`} className="bookmaker-row">
                              <div className="bookmaker-name">{bookmaker.name}</div>
                              <div className="odds-values">
                                {bookmaker.odds.outcomes?.map((outcome: any) => (
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
          </>
        )}

        {activeTab === 'game-predictions' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>Game Predictions</h2>
              <p className="predictions-subtitle">AI-powered predictions for game outcomes</p>
            </div>
            <div className="games-grid">
              {filteredGamePredictions.length > 0 ? (
                paginateItems(filteredGamePredictions, currentPage).map((prediction, index) => (
                  <div key={index} className="game-card">
                    <div className="game-info">
                      <div className="teams">
                        <h3>{prediction.away_team} @ {prediction.home_team}</h3>
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
                      <span className="sport">{formatSport(prediction.sport)}</span>
                      <span className="model">Model: {prediction.model_version}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-data">No game predictions found for current filters</div>
              )}
            </div>
            {filteredGamePredictions.length > itemsPerPage && (
              <div className="pagination">
                <button 
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </button>
                <span>Page {currentPage} of {getTotalPages(filteredGamePredictions)}</span>
                <button 
                  onClick={() => setCurrentPage(Math.min(getTotalPages(filteredGamePredictions), currentPage + 1))}
                  disabled={currentPage === getTotalPages(filteredGamePredictions)}
                >
                  Next
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'prop-predictions' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>Player Prop Predictions</h2>
              <p className="predictions-subtitle">AI-powered predictions for player performance props</p>
            </div>
            <div className="games-grid">
              {filteredPropPredictions.length > 0 ? (
                paginateItems(filteredPropPredictions, currentPage).map((prediction, index) => (
                  <div key={index} className="game-card">
                    <div className="game-info">
                      <div className="teams">
                        <h3>{prediction.player_name} - {prediction.prop_type}</h3>
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
                      <span className="model">Model: {prediction.model_version}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-data">No prop predictions found for current filters</div>
              )}
            </div>
            {filteredPropPredictions.length > itemsPerPage && (
              <div className="pagination">
                <button 
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </button>
                <span>Page {currentPage} of {getTotalPages(filteredPropPredictions)}</span>
                <button 
                  onClick={() => setCurrentPage(Math.min(getTotalPages(filteredPropPredictions), currentPage + 1))}
                  disabled={currentPage === getTotalPages(filteredPropPredictions)}
                >
                  Next
                </button>
              </div>
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
          />
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <Authenticator>
      {({ signOut, user }) => (
        <Dashboard user={user} signOut={signOut} />
      )}
    </Authenticator>
  );
}

export default App;
