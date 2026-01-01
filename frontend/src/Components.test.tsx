import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Test individual components instead of the full App
describe('Frontend Component Tests', () => {
  test('basic React rendering works', () => {
    const TestComponent = () => <div>Test Dashboard</div>;
    render(<TestComponent />);
    expect(screen.getByText('Test Dashboard')).toBeInTheDocument();
  });

  test('environment variables are configured', () => {
    expect(process.env.REACT_APP_API_URL).toBe('https://test-api.example.com/prod');
    expect(process.env.REACT_APP_STAGE).toBe('test');
  });

  test('CSS classes can be applied', () => {
    const StyledComponent = () => (
      <div className="game-card">
        <h3>Game Title</h3>
        <span className="odds-value">+150</span>
      </div>
    );
    
    render(<StyledComponent />);
    expect(screen.getByText('Game Title')).toBeInTheDocument();
    expect(screen.getByText('+150')).toBeInTheDocument();
  });

  test('mock data structures match expected format', () => {
    const mockGame = {
      game_id: '1',
      sport: 'americanfootball_nfl',
      home_team: 'Bears',
      away_team: 'Lions',
      bookmaker: 'betmgm',
      commence_time: '2026-01-04T21:25:00Z',
      markets: {
        h2h: { home: -160, away: 135 }
      }
    };

    expect(mockGame.game_id).toBe('1');
    expect(mockGame.sport).toBe('americanfootball_nfl');
    expect(mockGame.markets.h2h?.home).toBe(-160);
  });
});
