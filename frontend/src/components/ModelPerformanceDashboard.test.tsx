import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ModelPerformanceDashboard from './ModelPerformanceDashboard';
import { bettingApi } from '../services/api';

jest.mock('../services/api', () => ({
  bettingApi: {
    getAnalysisHistory: jest.fn()
  }
}));

const mockBettingApi = bettingApi as jest.Mocked<typeof bettingApi>;

describe('ModelPerformanceDashboard', () => {
  const defaultProps = {
    token: 'test-token',
    settings: {
      bookmaker: 'draftkings',
      sport: 'americanfootball_nfl',
      model: 'all'
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockBettingApi.getAnalysisHistory.mockImplementation(() => new Promise(() => {}));
    
    render(<ModelPerformanceDashboard {...defaultProps} />);
    
    expect(screen.getByText('Loading model performance data...')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    mockBettingApi.getAnalysisHistory.mockRejectedValue(new Error('API Error'));
    
    render(<ModelPerformanceDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Error: Failed to load model performance data')).toBeInTheDocument();
    });
  });

  it('renders no data message when no analyses exist', async () => {
    mockBettingApi.getAnalysisHistory.mockResolvedValue({
      success: true,
      data: []
    });
    
    render(<ModelPerformanceDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('No model performance data available yet.')).toBeInTheDocument();
    });
  });
});
