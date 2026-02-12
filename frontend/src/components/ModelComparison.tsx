import React, { useEffect, useState } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import './ModelComparison.css';

const getApiUrl = (): string => {
  const defaultUrl = 'https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod';
  return process.env.REACT_APP_API_URL || defaultUrl;
};

const API_BASE_URL = getApiUrl();

interface ModelComparison {
  model: string;
  model_id?: string;
  bet_type: string;
  is_user_model?: boolean;
  sample_size: number;
  original_accuracy: number;
  original_correct: number;
  original_total: number;
  inverse_accuracy: number;
  inverse_correct: number;
  inverse_total: number;
  recommendation: 'ORIGINAL' | 'INVERSE' | 'AVOID';
  accuracy_diff: number;
}

interface ComparisonData {
  sport: string;
  days: number;
  models: ModelComparison[];
  summary: {
    total_models: number;
    inverse_recommended: number;
    original_recommended: number;
    avoid: number;
  };
}

export const ModelComparison: React.FC = () => {
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [sport, setSport] = useState('basketball_nba');
  const [days, setDays] = useState(90);  // Default to 90 days for better sample size
  const [includeUserModels, setIncludeUserModels] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const getUserId = async () => {
      try {
        const { tokens } = await fetchAuthSession();
        const idToken = tokens?.idToken?.payload;
        const uid = (idToken?.sub || idToken?.['cognito:username']) as string | undefined;
        setUserId(uid || null);
      } catch (error) {
        console.error('Error getting user ID:', error);
      }
    };
    getUserId();
  }, []);

  useEffect(() => {
    if (userId || !includeUserModels) {
      fetchComparison();
    }
  }, [sport, days, includeUserModels, userId]);

  const fetchComparison = async () => {
    setLoading(true);
    try {
      const { tokens } = await fetchAuthSession();
      const token = tokens?.idToken?.toString();
      
      if (!token) {
        console.error('No auth token available');
        setLoading(false);
        return;
      }
      
      let url = `${API_BASE_URL}/model-comparison?sport=${sport}&days=${days}`;
      if (includeUserModels && userId) {
        url += `&user_id=${userId}`;
      }
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching model comparison:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

  if (loading) {
    return <div className="loading-state">Loading model comparison...</div>;
  }

  if (!data) {
    return <div className="loading-state">No data available</div>;
  }

  return (
    <div className="model-comparison">
      <div className="comparison-header">
        <h2>Model Performance Comparison</h2>
        
        <div className="filters">
          <select value={sport} onChange={(e) => setSport(e.target.value)} className="filter-select">
            <option value="basketball_nba">NBA</option>
            <option value="americanfootball_nfl">NFL</option>
          </select>

          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="filter-select">
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 6 months</option>
            <option value={365}>Last year</option>
            <option value={9999}>All time</option>
          </select>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeUserModels}
              onChange={(e) => setIncludeUserModels(e.target.checked)}
            />
            <span>Include My Models</span>
          </label>
        </div>

        <div className="summary-cards">
          <div className="summary-card">
            <div className="card-label">Total Models</div>
            <div className="card-value">{data.summary.total_models}</div>
          </div>
          <div className="summary-card success">
            <div className="card-label">Use Original</div>
            <div className="card-value">{data.summary.original_recommended}</div>
          </div>
          <div className="summary-card warning">
            <div className="card-label">Bet Against (Inverse)</div>
            <div className="card-value">{data.summary.inverse_recommended}</div>
          </div>
          <div className="summary-card danger">
            <div className="card-label">Avoid</div>
            <div className="card-value">{data.summary.avoid}</div>
          </div>
        </div>
      </div>

      <div className="comparison-table-container">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Sample Size</th>
              <th>Original Accuracy</th>
              <th>Inverse Accuracy</th>
              <th>Difference</th>
              <th>Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {data.models.map((model, index) => (
              <tr key={`${model.model_id || model.model}-${model.bet_type}-${index}`}>
                <td>
                  <div className="model-name">
                    {model.model}
                    <span className="badge bet-type">{model.bet_type === 'game' ? 'Games' : 'Props'}</span>
                    {model.is_user_model && <span className="badge">My Model</span>}
                  </div>
                </td>
                <td>{model.sample_size}</td>
                <td>
                  <div className="accuracy-cell">
                    <div className="accuracy-value">{formatPercent(model.original_accuracy)}</div>
                    <div className="accuracy-detail">{model.original_correct}/{model.original_total}</div>
                  </div>
                </td>
                <td>
                  <div className="accuracy-cell">
                    <div className="accuracy-value">{formatPercent(model.inverse_accuracy)}</div>
                    <div className="accuracy-detail">{model.inverse_correct}/{model.inverse_total}</div>
                  </div>
                </td>
                <td>
                  <span className={`diff ${model.accuracy_diff > 0 ? 'positive' : 'negative'}`}>
                    {model.accuracy_diff > 0 ? '+' : ''}{formatPercent(model.accuracy_diff)}
                  </span>
                </td>
                <td>
                  <span className={`recommendation-badge ${model.recommendation.toLowerCase()}`}>
                    {model.recommendation}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="help-section">
        <h3>How to Read This:</h3>
        <ul>
          <li><span className="success">ORIGINAL:</span> Model predictions are accurate - use them as-is</li>
          <li><span className="warning">INVERSE:</span> Model consistently predicts wrong - bet against it</li>
          <li><span className="danger">AVOID:</span> Neither original nor inverse is profitable</li>
          <li><strong>Difference:</strong> Positive means inverse performs better</li>
        </ul>
      </div>
    </div>
  );
};
