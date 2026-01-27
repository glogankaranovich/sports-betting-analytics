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

  async getGames(token?: string, sport?: string, bookmaker?: string, fetchAll: boolean = true): Promise<ApiResponse> {
    const params = new URLSearchParams();
    if (sport) params.append('sport', sport);
    if (bookmaker) params.append('bookmaker', bookmaker);
    if (fetchAll) params.append('fetch_all', 'true');
    
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

  async getAnalyses(token: string, filters: { sport?: string; model?: string; bookmaker?: string; type?: string; fetchAll?: boolean } = {}): Promise<any> {
    const params = new URLSearchParams();
    if (filters.sport) params.append('sport', filters.sport);
    if (filters.model) params.append('model', filters.model);
    if (filters.bookmaker) params.append('bookmaker', filters.bookmaker);
    if (filters.type) params.append('type', filters.type);
    if (filters.fetchAll) params.append('fetch_all', 'true');
    
    const headers = { Authorization: `Bearer ${token}` };
    
    const response = await api.get(`/analyses?${params.toString()}`, { headers });
    return response.data;
  },

  async getInsights(token: string, filters: { sport?: string; model?: string; bookmaker?: string; type?: string; fetchAll?: boolean } = {}): Promise<any> {
    const params = new URLSearchParams();
    if (filters.sport) params.append('sport', filters.sport);
    if (filters.model) params.append('model', filters.model);
    if (filters.bookmaker) params.append('bookmaker', filters.bookmaker);
    if (filters.type) params.append('type', filters.type);
    if (filters.fetchAll) params.append('fetch_all', 'true');
    
    const headers = { Authorization: `Bearer ${token}` };
    
    const response = await api.get(`/insights?${params.toString()}`, { headers });
    return response.data;
  },

  async getTopInsight(token: string, filters: { sport?: string; model?: string; bookmaker?: string; type?: string } = {}): Promise<any> {
    const params = new URLSearchParams();
    if (filters.sport) params.append('sport', filters.sport);
    if (filters.model) params.append('model', filters.model);
    if (filters.bookmaker) params.append('bookmaker', filters.bookmaker);
    if (filters.type) params.append('type', filters.type);
    
    const headers = { Authorization: `Bearer ${token}` };
    
    const response = await api.get(`/top-insight?${params.toString()}`, { headers });
    return response.data;
  },

  async getGamePredictions(token: string, sport?: string, bookmaker?: string): Promise<any> {
    const params = new URLSearchParams();
    if (sport) params.append('sport', sport);
    if (bookmaker) params.append('bookmaker', bookmaker);
    params.append('limit', '500');
    
    const url = `/game-predictions?${params.toString()}`;
    const response = await api.get(url, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getPropPredictions(token: string, sport?: string): Promise<any> {
    const url = sport ? `/prop-predictions?sport=${sport}&limit=500` : '/prop-predictions?limit=500';
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
    fetchAll?: boolean;
  }): Promise<PlayerPropsResponse> {
    const params = new URLSearchParams();
    if (filters?.sport) params.append('sport', filters.sport);
    if (filters?.bookmaker) params.append('bookmaker', filters.bookmaker);
    if (filters?.player) params.append('player', filters.player);
    if (filters?.prop_type) params.append('prop_type', filters.prop_type);
    if (filters?.fetchAll) params.append('fetch_all', 'true');
    
    const response = await api.get(`/player-props?${params.toString()}`, {
      headers: { Authorization: token }
    });
    return response.data;
  },
};

export const apiService = bettingApi;
