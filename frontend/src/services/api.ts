import axios from 'axios';
import { Sport, Bookmaker, ApiResponse, PlayerPropsResponse } from '../types/betting';

// Get API URL based on environment
const getApiUrl = (): string => {
  // Default to dev URL, will be overridden by environment variables in Amplify
  const defaultUrl = 'https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod';
  
  // Use environment-specific URL if provided, otherwise fall back to default
  return process.env.REACT_APP_API_URL || defaultUrl;
};

const api = axios.create({
  baseURL: getApiUrl(),
  timeout: 30000, // 30 seconds for large prop datasets
});

export const bettingApi = {
  async getHealth(): Promise<{ status: string }> {
    const response = await api.get('/health');
    return response.data;
  },

  async getGames(token?: string, sport?: string, bookmaker?: string): Promise<ApiResponse> {
    const params = new URLSearchParams();
    if (sport) params.append('sport', sport);
    if (bookmaker) params.append('bookmaker', bookmaker);
    
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    
    const response = await api.get(`/games?${params.toString()}`, { headers });
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

  async getStoredPredictions(token: string, limit = 50): Promise<any> {
    const response = await api.get(`/stored-predictions?limit=${limit}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getRecommendations(token: string, filters: { sport?: string; model?: string; risk_level?: string; limit?: number } = {}): Promise<any> {
    const params = new URLSearchParams();
    if (filters.sport) params.append('sport', filters.sport);
    if (filters.model) params.append('model', filters.model);
    if (filters.risk_level) params.append('risk_level', filters.risk_level);
    if (filters.limit) params.append('limit', filters.limit.toString());
    
    const response = await api.get(`/recommendations?${params.toString()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getTopRecommendation(token: string, filters: { sport?: string; model?: string; risk_level?: string } = {}): Promise<any> {
    const params = new URLSearchParams();
    if (filters.sport) params.append('sport', filters.sport);
    if (filters.model) params.append('model', filters.model);
    if (filters.risk_level) params.append('risk_level', filters.risk_level);
    
    const response = await api.get(`/top-recommendation?${params.toString()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getGamePredictions(token: string, limit?: number): Promise<any> {
    const url = limit ? `/game-predictions?limit=${limit}` : '/game-predictions';
    const response = await api.get(url, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getPropPredictions(token: string, limit?: number): Promise<any> {
    const url = limit ? `/prop-predictions?limit=${limit}` : '/prop-predictions';
    const response = await api.get(url, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getPlayerProps(token: string, filters?: {
    sport?: string;
    bookmaker?: string;
    player?: string;
    prop_type?: string;
    limit?: number;
  }): Promise<PlayerPropsResponse> {
    const params = new URLSearchParams();
    if (filters?.sport) params.append('sport', filters.sport);
    if (filters?.bookmaker) params.append('bookmaker', filters.bookmaker);
    if (filters?.player) params.append('player', filters.player);
    if (filters?.prop_type) params.append('prop_type', filters.prop_type);
    if (filters?.limit) params.append('limit', filters.limit.toString());
    
    const response = await api.get(`/player-props?${params.toString()}`, {
      headers: { Authorization: token }
    });
    return response.data;
  },
};

export const apiService = bettingApi;
