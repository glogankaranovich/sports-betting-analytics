import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AnalysisHistory from '../components/AnalysisHistory';
import { bettingApi } from '../services/api';

// Mock the API
jest.mock('../services/api', () => ({
  bettingApi: {
    getAnalysisHistory: jest.fn(),
  },
}));

const mockBettingApi = bettingApi as jest.Mocked<typeof bettingApi>;

describe('AnalysisHistory', () => {
  const defaultProps = {
    token: 'test-token',
    settings: {
      sport: 'basketball_nba',
      model: 'consensus',
      bookmaker: 'fanduel',
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockBettingApi.getAnalysisHistory.mockImplementation(() => new Promise(() => {}));
    
    render(<AnalysisHistory {...defaultProps} />);
    
    expect(screen.getByText('Loading analysis history...')).toBeInTheDocument();
  });

  it('renders analysis history data', async () => {
    const mockData = {
      analyses: [
        {
          pk: 'ANALYSIS#basketball_nba#game123#fanduel',
          sk: 'consensus#game#LATEST',
          game_id: 'game123',
          model: 'consensus',
          analysis_type: 'game',
          sport: 'basketball_nba',
          home_team: 'Lakers',
          away_team: 'Warriors',
          prediction: 'Lakers +2.5',
          confidence: 0.75,
          reasoning: 'Strong consensus across bookmakers',
          created_at: '2026-01-13T10:00:00Z',
          analysis_correct: true,
          outcome_verified_at: '2026-01-14T10:00:00Z',
        },
      ],
    };

    mockBettingApi.getAnalysisHistory.mockResolvedValue(mockData);

    render(<AnalysisHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Analysis History')).toBeInTheDocument();
    });

    expect(screen.getByText('Lakers vs Warriors')).toBeInTheDocument();
    expect(screen.getByText('Lakers +2.5')).toBeInTheDocument();
    expect(screen.getByText('✓ Correct')).toBeInTheDocument();
    expect(screen.getByText('consensus')).toBeInTheDocument();
  });

  it('renders prop analysis correctly', async () => {
    const mockData = {
      analyses: [
        {
          pk: 'ANALYSIS#basketball_nba#game123#fanduel',
          sk: 'value#prop#LATEST',
          game_id: 'game123',
          model: 'value',
          analysis_type: 'prop',
          sport: 'basketball_nba',
          player_name: 'LeBron James',
          prediction: 'Over 25.5 Points',
          confidence: 0.68,
          reasoning: 'Value opportunity identified',
          created_at: '2026-01-13T10:00:00Z',
          analysis_correct: false,
          outcome_verified_at: '2026-01-14T10:00:00Z',
        },
      ],
    };

    mockBettingApi.getAnalysisHistory.mockResolvedValue(mockData);

    render(<AnalysisHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('LeBron James - NBA')).toBeInTheDocument();
    });

    expect(screen.getByText('Over 25.5 Points')).toBeInTheDocument();
    expect(screen.getByText('✗ Incorrect')).toBeInTheDocument();
    expect(screen.getByText('value')).toBeInTheDocument();
  });

  it('displays accuracy statistics', async () => {
    const mockData = {
      analyses: [
        {
          pk: 'test1',
          sk: 'test1',
          analysis_correct: true,
          outcome_verified_at: '2026-01-14T10:00:00Z',
          game_id: 'game1',
          model: 'consensus',
          analysis_type: 'game',
          sport: 'basketball_nba',
          prediction: 'Test 1',
          confidence: 0.7,
          reasoning: 'Test',
          created_at: '2026-01-13T10:00:00Z',
        },
        {
          pk: 'test2',
          sk: 'test2',
          analysis_correct: false,
          outcome_verified_at: '2026-01-14T10:00:00Z',
          game_id: 'game2',
          model: 'consensus',
          analysis_type: 'game',
          sport: 'basketball_nba',
          prediction: 'Test 2',
          confidence: 0.6,
          reasoning: 'Test',
          created_at: '2026-01-13T10:00:00Z',
        },
      ],
    };

    mockBettingApi.getAnalysisHistory.mockResolvedValue(mockData);

    render(<AnalysisHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument(); // Total analyses
      expect(screen.getByText('50.0%')).toBeInTheDocument(); // Accuracy (1/2)
    });
  });

  it('handles API errors gracefully', async () => {
    mockBettingApi.getAnalysisHistory.mockRejectedValue(new Error('API Error'));

    render(<AnalysisHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load analysis history')).toBeInTheDocument();
    });
  });

  it('calls API with correct parameters', async () => {
    mockBettingApi.getAnalysisHistory.mockResolvedValue({ analyses: [] });

    render(<AnalysisHistory {...defaultProps} />);

    await waitFor(() => {
      expect(mockBettingApi.getAnalysisHistory).toHaveBeenCalledWith('test-token', {
        sport: 'basketball_nba',
        model: 'consensus',
        bookmaker: 'fanduel',
      });
    });
  });

  it('shows no data message when empty', async () => {
    mockBettingApi.getAnalysisHistory.mockResolvedValue({ analyses: [] });

    render(<AnalysisHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('No analysis history found')).toBeInTheDocument();
    });
  });
});
