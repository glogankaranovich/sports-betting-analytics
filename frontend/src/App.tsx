import React, { useState, useEffect } from 'react';
import { bettingApi } from './services/api';
import { Game } from './types/betting';
import './App.css';

function App() {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGames = async () => {
      try {
        const data = await bettingApi.getGames();
        console.log('API Response:', data); // Debug log
        setGames(data.games || []);
      } catch (err) {
        setError('Failed to fetch games');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchGames();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="App">
      <header className="App-header">
        <h1>Carpool Bets Dashboard</h1>
        <p>Stage: {process.env.REACT_APP_STAGE}</p>
        <p>API: {process.env.REACT_APP_API_URL}</p>
      </header>
      <main>
        <h2>Available Games ({games.length})</h2>
        {games.map((game) => (
          <div key={`${game.game_id}-${game.bookmaker}`} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
            <h3>{game.away_team} @ {game.home_team}</h3>
            <p>Sport: {game.sport}</p>
            <p>Bookmaker: {game.bookmaker}</p>
            <p>Date: {new Date(game.commence_time).toLocaleDateString()}</p>
            {game.markets.h2h && (
              <div>
                <strong>Moneyline:</strong> {game.away_team} {game.markets.h2h.away} | {game.home_team} {game.markets.h2h.home}
              </div>
            )}
          </div>
        ))}
      </main>
    </div>
  );
}

export default App;
