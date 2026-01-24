import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ModelAnalytics } from './ModelAnalytics';

const API_URL = process.env.REACT_APP_API_URL || 'https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod';

interface ModelsProps {
  token: string;
  settings: {
    sport: string;
  };
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

const Models: React.FC<ModelsProps> = ({ token, settings }) => {
  const [weights, setWeights] = useState<ModelWeights | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      fetchWeights();
    }
  }, [token, settings.sport]);

  const fetchWeights = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.get(`${API_URL}/analytics?type=weights&sport=${settings.sport}&bet_type=game`, { headers });
      setWeights(res.data);
    } catch (err) {
      console.error('Failed to fetch model weights:', err);
    }
  };

  const modelInfo: Record<string, { name: string; description: string; methodology: string }> = {
    consensus: {
      name: 'Consensus Model',
      description: 'Balanced approach using bookmaker consensus',
      methodology: 'Averages odds across all bookmakers to identify market consensus. Higher confidence when bookmakers agree strongly.'
    },
    value: {
      name: 'Value Model',
      description: 'Finds odds discrepancies and value opportunities',
      methodology: 'Identifies bets where odds differ significantly from consensus. Focuses on low-vig markets and favorable odds.'
    },
    momentum: {
      name: 'Momentum Model',
      description: 'Tracks line movement and sharp action',
      methodology: 'Detects significant line movement and betting patterns. Identifies sharp action based on odds imbalances.'
    },
    contrarian: {
      name: 'Contrarian Model',
      description: 'Fades the public, follows sharp money',
      methodology: 'Identifies reverse line movement and odds imbalances. Bets against public favorites and with sharp action.'
    },
    hot_cold: {
      name: 'Hot/Cold Model',
      description: 'Recent form and performance trends',
      methodology: 'Analyzes last 10 games for teams and players. Identifies hot streaks and cold slumps. Weights recent performance heavily.'
    }
  };

  if (selectedModel) {
    return (
      <div>
        <button onClick={() => setSelectedModel(null)} className="back-button">
          ← Back to Models
        </button>
        <ModelAnalytics token={token} />
        <style>{`
          .back-button {
            margin-bottom: 20px;
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
          }
          .back-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="models-container">
      <h2>Model Comparison</h2>
      <p style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '30px' }}>
        Compare different analysis models and their recent performance
      </p>

      <div className="models-grid">
        {Object.entries(modelInfo).map(([modelKey, info]) => {
          const modelData = weights?.model_weights[modelKey];
          
          return (
            <div key={modelKey} className="model-card">
              <h3>{info.name}</h3>
              <p className="model-desc">{info.description}</p>
              <p className="model-method">{info.methodology}</p>
              
              {modelData && modelData.recent_accuracy !== null ? (
                <div className="model-stats">
                  <div className="stat-row">
                    <span className="stat-label">Recent Accuracy:</span>
                    <span className="stat-value">{(modelData.recent_accuracy * 100).toFixed(1)}%</span>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">Current Weight:</span>
                    <span className="stat-value">{(modelData.weight * 100).toFixed(1)}%</span>
                  </div>
                </div>
              ) : (
                <div className="no-data">No recent performance data</div>
              )}
              
              <button 
                className="view-details-btn"
                onClick={() => setSelectedModel(modelKey)}
              >
                View Detailed Analytics
              </button>
            </div>
          );
        })}
      </div>

      <style>{`
        .models-container {
          padding: 20px;
        }
        .models-container h2 {
          margin-bottom: 10px;
        }
        .models-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
          margin-top: 20px;
        }
        .model-card {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 12px;
          padding: 24px;
          border: 2px solid rgba(255, 255, 255, 0.1);
          transition: all 0.3s ease;
          display: flex;
          flex-direction: column;
          min-height: 320px;
        }
        .model-card:hover {
          border-color: rgba(76, 175, 80, 0.5);
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        .model-card h3 {
          margin: 0 0 12px 0;
          color: #4CAF50;
          font-size: 20px;
        }
        .model-desc {
          color: rgba(255, 255, 255, 0.8);
          margin: 0 0 12px 0;
          font-size: 14px;
          min-height: 40px;
        }
        .model-method {
          color: rgba(255, 255, 255, 0.6);
          margin: 0 0 20px 0;
          font-size: 13px;
          font-style: italic;
          line-height: 1.5;
          min-height: 60px;
          flex-grow: 1;
        }
        .model-stats {
          background: rgba(0, 0, 0, 0.2);
          padding: 16px;
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .stat-row {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
        }
        .stat-row:last-child {
          margin-bottom: 0;
        }
        .stat-label {
          color: rgba(255, 255, 255, 0.7);
          font-size: 13px;
        }
        .stat-value {
          color: #4CAF50;
          font-weight: bold;
          font-size: 14px;
        }
        .no-data {
          color: rgba(255, 255, 255, 0.4);
          font-style: italic;
          text-align: center;
          padding: 20px 0;
        }
        .view-details-btn {
          width: 100%;
          padding: 10px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border: none;
          border-radius: 6px;
          color: white;
          font-weight: bold;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        .view-details-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
        }
      `}</style>
    </div>
  );
};

export default Models;
