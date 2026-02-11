import React, { useEffect, useState } from 'react';

// Get API URL based on environment
const getApiUrl = (): string => {
  const defaultUrl = 'https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod';
  return process.env.REACT_APP_API_URL || defaultUrl;
};

const API_BASE_URL = getApiUrl();

interface ModelComparison {
  model: string;
  model_id?: string;
  is_user_model?: boolean;
  sample_size: number;
  original_accuracy: number;
  original_correct: number;
  inverse_accuracy: number;
  inverse_correct: number;
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
  const [days, setDays] = useState(30);
  const [includeUserModels, setIncludeUserModels] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);

  // Get user ID from auth
  useEffect(() => {
    const getUserId = async () => {
      try {
        const { tokens } = await (window as any).fetchAuthSession();
        const idToken = tokens?.idToken?.payload;
        const uid = idToken?.sub || idToken?.['cognito:username'];
        setUserId(uid);
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
      let url = `${API_BASE_URL}/model-comparison?sport=${sport}&days=${days}`;
      if (includeUserModels && userId) {
        url += `&user_id=${userId}`;
      }
      
      const response = await fetch(url);
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching model comparison:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'ORIGINAL':
        return 'text-green-600 bg-green-50';
      case 'INVERSE':
        return 'text-orange-600 bg-orange-50';
      case 'AVOID':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

  if (loading) {
    return <div className="p-4">Loading model comparison...</div>;
  }

  if (!data) {
    return <div className="p-4">No data available</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-4">Model Performance Comparison</h1>
        
        <div className="flex gap-4 mb-4">
          <select
            value={sport}
            onChange={(e) => setSport(e.target.value)}
            className="px-4 py-2 border rounded"
          >
            <option value="basketball_nba">NBA</option>
            <option value="americanfootball_nfl">NFL</option>
            <option value="baseball_mlb">MLB</option>
            <option value="icehockey_nhl">NHL</option>
            <option value="soccer_epl">EPL</option>
          </select>

          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-4 py-2 border rounded"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>

          <label className="flex items-center gap-2 px-4 py-2 border rounded bg-white cursor-pointer">
            <input
              type="checkbox"
              checked={includeUserModels}
              onChange={(e) => setIncludeUserModels(e.target.checked)}
              className="cursor-pointer"
            />
            <span>Include My Models</span>
          </label>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Total Models</div>
            <div className="text-2xl font-bold">{data.summary.total_models}</div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg shadow">
            <div className="text-sm text-green-600">Use Original</div>
            <div className="text-2xl font-bold text-green-600">
              {data.summary.original_recommended}
            </div>
          </div>
          <div className="bg-orange-50 p-4 rounded-lg shadow">
            <div className="text-sm text-orange-600">Bet Against (Inverse)</div>
            <div className="text-2xl font-bold text-orange-600">
              {data.summary.inverse_recommended}
            </div>
          </div>
          <div className="bg-red-50 p-4 rounded-lg shadow">
            <div className="text-sm text-red-600">Avoid</div>
            <div className="text-2xl font-bold text-red-600">
              {data.summary.avoid}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Model
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Sample Size
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Original Accuracy
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Inverse Accuracy
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Difference
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Recommendation
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.models.map((model) => (
              <tr key={model.model_id || model.model} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="font-medium">{model.model}</div>
                  {model.is_user_model && (
                    <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                      My Model
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {model.sample_size}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium">
                    {formatPercent(model.original_accuracy)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {model.original_correct}/{model.sample_size}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium">
                    {formatPercent(model.inverse_accuracy)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {model.inverse_correct}/{model.sample_size}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`text-sm font-medium ${
                      model.accuracy_diff > 0 ? 'text-orange-600' : 'text-green-600'
                    }`}
                  >
                    {model.accuracy_diff > 0 ? '+' : ''}
                    {formatPercent(model.accuracy_diff)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${getRecommendationColor(
                      model.recommendation
                    )}`}
                  >
                    {model.recommendation}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-semibold mb-2">How to Read This:</h3>
        <ul className="text-sm space-y-1">
          <li>
            <span className="font-medium text-green-600">ORIGINAL:</span> Model predictions
            are accurate - use them as-is
          </li>
          <li>
            <span className="font-medium text-orange-600">INVERSE:</span> Model consistently
            predicts wrong - bet against it
          </li>
          <li>
            <span className="font-medium text-red-600">AVOID:</span> Neither original nor
            inverse is profitable
          </li>
          <li>
            <span className="font-medium">Difference:</span> Positive means inverse performs
            better
          </li>
        </ul>
      </div>
    </div>
  );
};
