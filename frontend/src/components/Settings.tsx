import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod';

interface SettingsProps {
  settings: {
    sport: string;
    bookmaker: string;
    model: string;
  };
  onSettingsChange: (settings: any) => void;
  availableSports: string[];
  availableBookmakers: string[];
  token: string;
}

interface ModelWeights {
  model_weights: {
    [model: string]: {
      weight: number;
      recent_accuracy: number | null;
      recent_brier_score: number | null;
    };
  };
}

const Settings: React.FC<SettingsProps> = ({
  settings,
  onSettingsChange,
  availableSports,
  availableBookmakers,
  token
}) => {
  const [weights, setWeights] = useState<ModelWeights | null>(null);

  useEffect(() => {
    if (token && settings.sport !== 'all') {
      fetchWeights();
    }
  }, [token, settings.sport]);

  const fetchWeights = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const sport = settings.sport === 'all' ? 'basketball_nba' : settings.sport;
      const res = await axios.get(`${API_URL}/analytics?type=weights&sport=${sport}&bet_type=game`, { headers });
      setWeights(res.data);
    } catch (err) {
      console.error('Failed to fetch model weights:', err);
    }
  };

  const handleChange = (key: string, value: string) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  const modelDescriptions: Record<string, string> = {
    consensus: 'Average across all bookmakers - balanced approach',
    value: 'Finds odds discrepancies and value opportunities',
    momentum: 'Tracks line movement and sharp action'
  };

  return (
    <div className="predictions-section">
      <div className="settings-grid">
        <div className="setting-item">
          <label>Preferred Sport:</label>
          <select 
            value={settings.sport} 
            onChange={(e) => handleChange('sport', e.target.value)}
          >
            <option value="all">All Sports</option>
            {availableSports.map(sport => (
              <option key={sport} value={sport}>{sport.replace('_', ' ').toUpperCase()}</option>
            ))}
          </select>
        </div>

        <div className="setting-item">
          <label>Preferred Bookmaker:</label>
          <select 
            value={settings.bookmaker} 
            onChange={(e) => handleChange('bookmaker', e.target.value)}
          >
            <option value="all">All Bookmakers</option>
            {availableBookmakers.map(bookmaker => (
              <option key={bookmaker} value={bookmaker}>{bookmaker}</option>
            ))}
          </select>
        </div>

        <div className="setting-item">
          <label>Model:</label>
          <select 
            value={settings.model} 
            onChange={(e) => handleChange('model', e.target.value)}
          >
            <option value="consensus">Consensus</option>
            <option value="value">Value</option>
            <option value="momentum">Momentum</option>
          </select>
          <div className="model-description">
            {modelDescriptions[settings.model]}
          </div>
        </div>
      </div>

      {weights && (
        <div className="model-performance">
          <h3>Recent Model Performance (Last 30 Days)</h3>
          <div className="performance-grid">
            {Object.entries(weights.model_weights).map(([model, data]) => (
              <div key={model} className={`performance-card ${settings.model === model ? 'selected' : ''}`}>
                <div className="model-name">{model.charAt(0).toUpperCase() + model.slice(1)}</div>
                {data.recent_accuracy !== null ? (
                  <>
                    <div className="accuracy">{(data.recent_accuracy * 100).toFixed(1)}%</div>
                    <div className="weight">Weight: {(data.weight * 100).toFixed(1)}%</div>
                  </>
                ) : (
                  <div className="no-data">No recent data</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .model-description {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 4px;
          font-style: italic;
        }
        .model-performance {
          margin-top: 30px;
          padding: 20px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
        }
        .model-performance h3 {
          margin: 0 0 15px 0;
          font-size: 16px;
          color: rgba(255, 255, 255, 0.9);
        }
        .performance-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 15px;
        }
        .performance-card {
          padding: 15px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 6px;
          border: 2px solid transparent;
          text-align: center;
        }
        .performance-card.selected {
          border-color: #4CAF50;
          background: rgba(76, 175, 80, 0.1);
        }
        .model-name {
          font-weight: bold;
          margin-bottom: 8px;
          color: rgba(255, 255, 255, 0.9);
        }
        .accuracy {
          font-size: 24px;
          font-weight: bold;
          color: #4CAF50;
          margin-bottom: 4px;
        }
        .weight {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
        }
        .no-data {
          font-size: 14px;
          color: rgba(255, 255, 255, 0.4);
          font-style: italic;
        }
      `}</style>
    </div>
  );
};

export default Settings;
