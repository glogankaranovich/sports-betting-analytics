import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../services/api';

interface ModelRanking {
  model: string;
  model_id: string;
  mode: string;
  is_user_model: boolean;
  total_bets: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_odds: number;
  profit: number;
  roi: number;
  sharpe_ratio: number;
}

const ModelRankings: React.FC = () => {
  const [rankings, setRankings] = useState<ModelRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [sport, setSport] = useState('basketball_nba');
  const [days, setDays] = useState(30);
  const [mode, setMode] = useState('both');
  const [includeUserModels, setIncludeUserModels] = useState(false);

  useEffect(() => {
    loadRankings();
  }, [sport, days, mode, includeUserModels]);

  const loadRankings = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ sport, days: days.toString(), mode });
      if (includeUserModels) {
        const userId = localStorage.getItem('userId');
        if (userId) params.append('user_id', userId);
      }
      const data = await fetchWithAuth(`/model-rankings?${params}`);
      setRankings(data.rankings || []);
    } catch (error) {
      console.error('Error loading rankings:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getROIColor = (roi: number) => {
    if (roi > 0.1) return 'text-green-600 font-semibold';
    if (roi > 0) return 'text-green-500';
    if (roi < -0.1) return 'text-red-600 font-semibold';
    return 'text-red-500';
  };

  const summary = rankings.length > 0 ? {
    profitable: rankings.filter(r => r.roi > 0).length,
    unprofitable: rankings.filter(r => r.roi < 0).length,
    avgROI: rankings.reduce((sum, r) => sum + r.roi, 0) / rankings.length,
  } : null;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Model Rankings by ROI</h2>
      </div>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <select
          value={sport}
          onChange={(e) => setSport(e.target.value)}
          className="px-3 py-2 border rounded"
        >
          <option value="basketball_nba">NBA</option>
          <option value="basketball_ncaab">NCAAB</option>
          <option value="americanfootball_nfl">NFL</option>
        </select>

        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-2 border rounded"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>

        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="px-3 py-2 border rounded"
        >
          <option value="both">Original & Inverse</option>
          <option value="original">Original Only</option>
          <option value="inverse">Inverse Only</option>
        </select>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={includeUserModels}
            onChange={(e) => setIncludeUserModels(e.target.checked)}
            className="rounded"
          />
          <span>Include My Models</span>
        </label>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Profitable Models</div>
            <div className="text-2xl font-bold text-green-600">{summary.profitable}</div>
          </div>
          <div className="bg-red-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Unprofitable Models</div>
            <div className="text-2xl font-bold text-red-600">{summary.unprofitable}</div>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-sm text-gray-600">Average ROI</div>
            <div className={`text-2xl font-bold ${getROIColor(summary.avgROI)}`}>
              {formatPercent(summary.avgROI)}
            </div>
          </div>
        </div>
      )}

      {/* Rankings Table */}
      {loading ? (
        <div className="text-center py-8">Loading rankings...</div>
      ) : rankings.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No data available</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">Rank</th>
                <th className="px-4 py-2 text-left">Model</th>
                <th className="px-4 py-2 text-left">Mode</th>
                <th className="px-4 py-2 text-right">Bets</th>
                <th className="px-4 py-2 text-right">Win Rate</th>
                <th className="px-4 py-2 text-right">Avg Odds</th>
                <th className="px-4 py-2 text-right">Profit</th>
                <th className="px-4 py-2 text-right">ROI</th>
                <th className="px-4 py-2 text-right">Sharpe</th>
              </tr>
            </thead>
            <tbody>
              {rankings.map((ranking, index) => (
                <tr key={`${ranking.model_id}-${ranking.mode}`} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2">{index + 1}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      {ranking.model}
                      {ranking.is_user_model && (
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                          My Model
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 text-xs rounded ${
                      ranking.mode === 'inverse' 
                        ? 'bg-orange-100 text-orange-800' 
                        : 'bg-green-100 text-green-800'
                    }`}>
                      {ranking.mode}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">{ranking.total_bets}</td>
                  <td className="px-4 py-2 text-right">{formatPercent(ranking.win_rate)}</td>
                  <td className="px-4 py-2 text-right">{ranking.avg_odds > 0 ? '+' : ''}{ranking.avg_odds}</td>
                  <td className={`px-4 py-2 text-right ${ranking.profit > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(ranking.profit)}
                  </td>
                  <td className={`px-4 py-2 text-right ${getROIColor(ranking.roi)}`}>
                    {formatPercent(ranking.roi)}
                  </td>
                  <td className="px-4 py-2 text-right">{ranking.sharpe_ratio.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ModelRankings;
