import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Test utility functions and components separately
describe('App Utilities', () => {
  test('date formatting works correctly', () => {
    const testDate = '2026-01-04T21:25:00Z';
    const formatted = new Date(testDate).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short', 
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
    
    expect(formatted).toContain('Jan');
    expect(formatted).toContain('4');
  });

  test('sport formatting works correctly', () => {
    const formatSport = (sport: string) => sport.replace('americanfootball_', '').toUpperCase();
    
    expect(formatSport('americanfootball_nfl')).toBe('NFL');
    expect(formatSport('basketball_nba')).toBe('BASKETBALL_NBA');
  });

  test('odds formatting works correctly', () => {
    const formatOdds = (odds: number) => odds > 0 ? `+${odds}` : `${odds}`;
    
    expect(formatOdds(150)).toBe('+150');
    expect(formatOdds(-160)).toBe('-160');
  });

  test('game data grouping logic', () => {
    const mockGames = [
      { game_id: '1', bookmaker: 'betmgm', sport: 'nfl' },
      { game_id: '1', bookmaker: 'draftkings', sport: 'nfl' },
      { game_id: '2', bookmaker: 'betmgm', sport: 'nba' }
    ];

    const grouped = mockGames.reduce((acc: any, game) => {
      if (!acc[game.game_id]) {
        acc[game.game_id] = { ...game, bookmakers: [] };
      }
      acc[game.game_id].bookmakers.push({ name: game.bookmaker });
      return acc;
    }, {});

    expect(Object.keys(grouped)).toHaveLength(2);
    expect(grouped['1'].bookmakers).toHaveLength(2);
    expect(grouped['2'].bookmakers).toHaveLength(1);
  });
});
