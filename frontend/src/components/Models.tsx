import React, { useState, useEffect } from 'react';
import { ModelAnalytics } from './ModelAnalytics';
import { bettingApi } from '../services/api';

const API_URL = process.env.REACT_APP_API_URL || 'https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod';

interface ModelsProps {
  token: string;
  settings: {
    sport: string;
  };
}

const Models: React.FC<ModelsProps> = ({ token, settings }) => {
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [modelStats, setModelStats] = useState<Record<string, any>>({});

  useEffect(() => {
    if (token) {
      fetchModelStats();
    }
  }, [token]);

  const fetchModelStats = async () => {
    try {
      const data = await bettingApi.getAnalytics(token);
      setModelStats(data);
    } catch (error) {
      console.error('Error fetching model stats:', error);
    }
  };

  const modelInfo: Record<string, { name: string; description: string; methodology: string }> = {
    consensus: {
      name: 'Consensus Model',
      description: 'Balanced approach using bookmaker consensus',
      methodology: 'Averages odds across all bookmakers to identify market consensus. Higher confidence when bookmakers agree strongly.'
    },
    ensemble: {
      name: 'Ensemble Model',
      description: 'Intelligent combination of all models using dynamic weighting',
      methodology: 'Combines predictions from all models weighted by their recent 30-day performance. Automatically adjusts weights based on accuracy. Uses the highest-weighted model\'s prediction with ensemble confidence.'
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
    },
    rest_schedule: {
      name: 'Rest/Schedule Model',
      description: 'Rest days, back-to-backs, and home/away splits',
      methodology: 'Evaluates days of rest between games. Penalizes back-to-back situations. Factors in home court advantage and travel fatigue.'
    },
    matchup: {
      name: 'Matchup Model',
      description: 'Head-to-head history and style matchups',
      methodology: 'Analyzes historical performance between teams. Evaluates offensive vs defensive matchups. Combines H2H records (60%) with style analysis (40%).'
    },
    injury_aware: {
      name: 'Injury-Aware Model',
      description: 'Adjusts predictions based on player injuries',
      methodology: 'Queries injury reports from ESPN. Calculates injury impact scores for each team. Warns against props for injured players (Out/Doubtful). Factors team injury differentials into game predictions.'
    }
  };

  if (selectedModel) {
    return (
      <div className="modal-overlay" onClick={() => setSelectedModel(null)}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <button onClick={() => setSelectedModel(null)} className="close-button">×</button>
          <ModelAnalytics token={token} selectedModel={selectedModel} />
        </div>
      </div>
    );
  }

  return (
    <div className="models-container">
      <h2>System Models</h2>
      <p style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '30px' }}>
        Built-in prediction models with proven track records. View detailed analytics and performance metrics for each model.
      </p>

      <div className="models-grid">
        {Object.entries(modelInfo).map(([modelKey, info]) => {
          const stats = modelStats[modelKey];
          const accuracy = stats?.accuracy ? stats.accuracy.toFixed(1) : null;
          
          return (
            <div key={modelKey} className="model-card">
              <h3>{info.name}</h3>
              <p className="model-desc">{info.description}</p>
              <p className="model-method">{info.methodology}</p>
              {accuracy && (
                <div className="model-stats">
                  <span className="accuracy">{accuracy}% Overall Accuracy</span>
                </div>
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
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 20px;
        }
        .modal-content {
          background: rgba(26, 32, 44, 0.95);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          max-width: 1400px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          padding: 30px;
          position: relative;
        }
        .close-button {
          position: absolute;
          top: 15px;
          right: 15px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 50%;
          color: #fff;
          cursor: pointer;
          font-size: 24px;
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }
        .close-button:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: rotate(90deg);
        }
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
          border-color: rgba(0, 212, 255, 0.5);
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 212, 255, 0.2);
        }
        .model-card h3 {
          margin: 0 0 12px 0;
          color: #00d4ff;
          font-size: 20px;
        }
        .model-stats {
          display: flex;
          justify-content: center;
          margin-bottom: 12px;
          padding: 8px 0;
        }
        .accuracy {
          font-size: 16px;
          font-weight: 700;
          color: #00d4ff;
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
        .stat-section {
          margin-bottom: 12px;
        }
        .stat-section:last-child {
          margin-bottom: 0;
        }
        .stat-section-title {
          color: rgba(255, 255, 255, 0.9);
          font-size: 12px;
          font-weight: bold;
          text-transform: uppercase;
          margin-bottom: 8px;
          padding-bottom: 4px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
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
          background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
          border: none;
          border-radius: 6px;
          color: white;
          font-weight: bold;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        .view-details-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
        }
          box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
        }
      `}</style>
    </div>
  );
};

export default Models;
