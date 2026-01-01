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

  if (loading) return <div>Loading games...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="App">
      <header className="App-header">
        <h1>Carpool Bets Dashboard</h1>
        <p>Stage: {process.env.REACT_APP_STAGE}</p>
        <p>Welcome {user?.signInDetails?.loginId}!</p>
        <button onClick={signOut}>Sign out</button>
        <button onClick={fetchGames}>Refresh Data</button>
      </header>
      <main>
        <h2>Available Games ({games.length})</h2>
        {games.map((game, index) => (
          <div key={index} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
            <h3>{game.away_team} @ {game.home_team}</h3>
            <p>Sport: {game.sport}</p>
            <p>Bookmaker: {game.bookmaker}</p>
            <p>Date: {new Date(game.commence_time).toLocaleDateString()}</p>
            {game.markets?.h2h && (
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
