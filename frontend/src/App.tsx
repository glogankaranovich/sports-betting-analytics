import React, { useState, useEffect } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { bettingApi } from './services/api';
import { Game } from './types/betting';
import './amplifyConfig'; // Initialize Amplify
import '@aws-amplify/ui-react/styles.css';
import './App.css';

function Dashboard({ user, signOut }: { user: any; signOut?: () => void }) {
  const [games, setGames] = useState<Game[]>([]);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sportFilter, setSportFilter] = useState<string>('all');
  const [bookmakerFilter, setBookmakerFilter] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<'games' | 'predictions'>('games');

  useEffect(() => {
    fetchGames();
    fetchPredictions();
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

  const fetchPredictions = async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const data = await bettingApi.getStoredPredictions(token, 25);
        setPredictions(data.predictions || []);
      }
    } catch (err) {
      console.error('Error fetching predictions:', err);
    }
  };

  // Group games by game_id and aggregate bookmaker odds
  const groupedGames = games.reduce((acc, game) => {
    const gameKey = `${game.home_team}_vs_${game.away_team}`;
    if (!acc[gameKey]) {
      acc[gameKey] = {
        game_id: game.pk || game.game_id || '',
        home_team: game.home_team,
        away_team: game.away_team,
        sport: game.sport,
        commence_time: game.commence_time,
        bookmaker: '', // Not used in grouped structure
        markets: {}, // Not used in grouped structure
        bookmakers: []
      };
    }
    
    // Add this bookmaker's odds to the game
    if (game.markets && Array.isArray(game.markets)) {
      const h2hMarket = game.markets.find(market => market && market.key === 'h2h');
      if (h2hMarket && h2hMarket.outcomes && Array.isArray(h2hMarket.outcomes)) {
        acc[gameKey].bookmakers.push({
          name: game.sk || game.bookmaker || 'unknown',
          markets: game.markets
        });
      }
    }
    
    return acc;
  }, {} as Record<string, Game & { bookmakers: Array<{ name: string; markets: Game['markets'] }> }>);

  let filteredGames = Object.values(groupedGames);

  // Apply sport filter
  if (sportFilter !== 'all') {
    filteredGames = filteredGames.filter(game => game.sport === sportFilter);
  }

  // Apply bookmaker filter
  if (bookmakerFilter !== 'all') {
    filteredGames = filteredGames.filter(game => 
      game.bookmakers.some(bookmaker => bookmaker.name === bookmakerFilter)
    );
  }

  // Get unique sports and bookmakers for filter options
  const uniqueSports = Array.from(new Set(games.map(game => game.sport)));
  const uniqueBookmakers = Array.from(new Set(games.map(game => game.bookmaker)));

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  const formatSport = (sport: string) => {
    return sport.replace('americanfootball_', '').toUpperCase();
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
            fetchPredictions();
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
            onClick={() => setActiveTab('games')}
          >
            Games ({filteredGames.length})
          </button>
          <button 
            className={`tab-button ${activeTab === 'predictions' ? 'active' : ''}`}
            onClick={() => setActiveTab('predictions')}
          >
            AI Predictions ({predictions.length})
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
                  <option value="all">All Sports</option>
                  {uniqueSports.map(sport => (
                    <option key={sport} value={sport}>
                      {formatSport(sport)}
                    </option>
                  ))}
                </select>
                <select 
                  className="filter-select"
                  value={bookmakerFilter} 
                  onChange={(e) => setBookmakerFilter(e.target.value)}
            >
              <option value="all">All Bookmakers</option>
              {uniqueBookmakers.map(bookmaker => (
                <option key={bookmaker} value={bookmaker}>
                  {bookmaker}
                </option>
              ))}
            </select>
          </div>
          <span className="games-count">{filteredGames.length} games</span>
        </div>
        
        <div className="games-grid">
          {filteredGames.map((game) => {
            // Filter bookmakers within each game based on bookmaker filter
            const displayBookmakers = bookmakerFilter === 'all' 
              ? game.bookmakers 
              : game.bookmakers.filter(bookmaker => bookmaker.name === bookmakerFilter);
            
            return (
            <div key={game.game_id} className="game-card">
              <div className="game-header">
                <div className="teams">
                  <h3>{game.away_team} @ {game.home_team}</h3>
                  <div className="sport-tag">{formatSport(game.sport)}</div>
                </div>
                <div className="game-meta">
                  <div>{formatDate(game.commence_time)}</div>
                  <div className="bookmaker-count">{displayBookmakers.length} bookmaker{displayBookmakers.length !== 1 ? 's' : ''}</div>
                </div>
              </div>
              
              <div className="odds-section">
                <div className="odds-header">
                  <span className="odds-label">Moneyline Odds</span>
                </div>
                <div className="bookmaker-odds">
                  {displayBookmakers.map((bookmaker, idx) => {
                    // Find the h2h market in the markets array
                    const h2hMarket = Array.isArray(bookmaker.markets) 
                      ? bookmaker.markets.find(market => market && market.key === 'h2h')
                      : null;
                    
                    if (!h2hMarket || !h2hMarket.outcomes || !Array.isArray(h2hMarket.outcomes)) return null;
                    
                    const awayOdds = h2hMarket.outcomes.find((o: any) => o && o.name === game.away_team)?.price;
                    const homeOdds = h2hMarket.outcomes.find((o: any) => o && o.name === game.home_team)?.price;
                    
                    if (!awayOdds || !homeOdds) return null;
                    
                    return (
                      <div key={`${game.game_id}-${bookmaker.name}`} className="bookmaker-row">
                        <div className="bookmaker-name">{bookmaker.name}</div>
                        <div className="odds-values">
                          <span className="odds-value away">
                            {game.away_team}: {formatOdds(awayOdds)}
                          </span>
                          <span className="odds-value home">
                            {game.home_team}: {formatOdds(homeOdds)}
                          </span>
                        </div>
                      </div>
                    );
                  }).filter(Boolean)}
                </div>
              </div>
            </div>
            );
          })}
        </div>
          </>
        )}

        {activeTab === 'predictions' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>AI Predictions</h2>
              <p className="predictions-subtitle">Consensus-based predictions from multiple bookmakers</p>
            </div>
            <div className="games-grid">
              {predictions.map((prediction, index) => (
                <div key={index} className="game-card prediction-card">
                  <div className="game-info">
                    <div className="teams">
                      <span className="away-team">{prediction.away_team}</span>
                      <span className="vs">@</span>
                      <span className="home-team">{prediction.home_team}</span>
                    </div>
                    <div className="game-meta">
                      <span className="sport">{formatSport(prediction.sport)}</span>
                      <span className="model">Model: {prediction.model_version}</span>
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
                    {prediction.value_bets && prediction.value_bets.length > 0 && (
                      <div className="value-bets">
                        <span className="value-label">Value Bets: {prediction.value_bets.length}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
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
