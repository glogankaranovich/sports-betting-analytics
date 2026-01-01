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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sportFilter, setSportFilter] = useState<string>('all');
  const [bookmakerFilter, setBookmakerFilter] = useState<string>('all');

  useEffect(() => {
    fetchGames();
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

  // Group games by game_id and aggregate bookmaker odds
  const groupedGames = games.reduce((acc, game) => {
    if (!acc[game.game_id]) {
      acc[game.game_id] = {
        ...game,
        bookmakers: []
      };
    }
    acc[game.game_id].bookmakers.push({
      name: game.bookmaker,
      markets: game.markets
    });
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
          <button className="btn btn-secondary" onClick={fetchGames}>
            Refresh Data
          </button>
          <button className="btn btn-primary" onClick={signOut}>
            Sign Out
          </button>
        </div>
      </header>
      
      <main>
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
                      ? bookmaker.markets.find(market => market.key === 'h2h')
                      : bookmaker.markets.h2h ? { outcomes: [
                          { name: game.away_team, price: bookmaker.markets.h2h.away },
                          { name: game.home_team, price: bookmaker.markets.h2h.home }
                        ]} : null;
                    
                    if (!h2hMarket || !h2hMarket.outcomes) return null;
                    
                    const awayOdds = h2hMarket.outcomes.find((o: any) => o.name === game.away_team)?.price;
                    const homeOdds = h2hMarket.outcomes.find((o: any) => o.name === game.home_team)?.price;
                    
                    return (
                      <div key={idx} className="bookmaker-row">
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
                  })}
                </div>
              </div>
            </div>
            );
          })}
        </div>
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
