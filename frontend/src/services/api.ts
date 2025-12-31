import axios from 'axios';
import { Game, Sport, Bookmaker, ApiResponse } from '../types/betting';

// Get API URL based on environment
const getApiUrl = (): string => {
  // Amplify sets REACT_APP_STAGE based on branch
  const stage = process.env.REACT_APP_STAGE || 'dev';
  
  // Default to dev URL, will be overridden by environment variables in Amplify
  const defaultUrl = 'https://pylcs4ypld.execute-api.us-east-1.amazonaws.com/prod';
  
  // Use environment-specific URL if provided, otherwise fall back to default
  return process.env.REACT_APP_API_URL || defaultUrl;
};

const api = axios.create({
  baseURL: getApiUrl(),
  timeout: 10000,
});

export const bettingApi = {
  async getHealth(): Promise<{ status: string }> {
    const response = await api.get('/health');
    return response.data;
  },

  async getGames(sport?: string, bookmaker?: string): Promise<ApiResponse> {
    const params = new URLSearchParams();
    if (sport) params.append('sport', sport);
    if (bookmaker) params.append('bookmaker', bookmaker);
    
    const response = await api.get(`/games?${params.toString()}`);
    return response.data;
  },

  async getSports(): Promise<Sport[]> {
    const response = await api.get('/sports');
    return response.data;
  },

  async getBookmakers(): Promise<Bookmaker[]> {
    const response = await api.get('/bookmakers');
    return response.data;
  },
};
