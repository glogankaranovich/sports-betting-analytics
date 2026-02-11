import React, { useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'https://ddzbfblwr0.execute-api.us-east-1.amazonaws.com/prod';

interface ModelDetailProps {
  model: any;
  token: string;
  onBack: () => void;
}

interface BacktestResult {
  backtest_id: string;
  accuracy: number;
  roi: number;
  total_predictions: number;
  correct_predictions: number;
  avg_confidence: number;
  start_date: string;
  end_date: string;
  created_at: string;
}

export const ModelDetail: React.FC<ModelDetailProps> = ({ model, token, onBack }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'backtest'>('overview');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [running, setRunning] = useState(false);
  const [backtests, setBacktests] = useState<BacktestResult[]>([]);
  const [loading, setLoading] = useState(false);

  const runBacktest = async () => {
    if (!startDate || !endDate) {
      alert('Please select both start and end dates');
      return;
    }

    try {
      setRunning(true);
      await axios.post(
        `${API_URL}/user-models/${model.model_id}/backtests`,
        { start_date: startDate, end_date: endDate },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      alert('Backtest started! Results will appear below.');
      loadBacktests();
    } catch (error) {
      console.error('Error running backtest:', error);
      alert('Failed to run backtest');
    } finally {
      setRunning(false);
    }
  };

  const loadBacktests = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${API_URL}/user-models/${model.model_id}/backtests`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setBacktests(response.data.backtests || []);
    } catch (error) {
      console.error('Error loading backtests:', error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (activeTab === 'backtest') {
      loadBacktests();
    }
  }, [activeTab]);

  return (
    <div className="modal-overlay" onClick={onBack}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button onClick={onBack} className="close-button">×</button>
        
        <div className="model-header">
          <h2>{model.name}</h2>
          <span className={`status-badge ${model.status}`}>{model.status}</span>
        </div>
        
        <p className="model-description">{model.description}</p>

        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`tab ${activeTab === 'backtest' ? 'active' : ''}`}
          onClick={() => setActiveTab('backtest')}
        >
          Backtest
        </button>
      </div>

      {activeTab === 'overview' && (
        <div className="tab-content">
          <h3>Model Configuration</h3>
          <div className="config-grid">
            <div className="config-item">
              <label>Sport:</label>
              <span>{model.sport}</span>
            </div>
            <div className="config-item">
              <label>Bet Type:</label>
              <span>{model.bet_types?.join(', ') || 'N/A'}</span>
            </div>
            <div className="config-item">
              <label>Created:</label>
              <span>{new Date(model.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          <h3>Model Weights</h3>
          <div className="weights-grid">
            {Object.entries(model.data_sources || {}).map(([key, source]: [string, any]) => (
              <div key={key} className="weight-item">
                <span className="weight-label">{key}:</span>
                <div className="weight-bar">
                  <div className="weight-fill" style={{ width: `${(source.weight || 0) * 100}%` }} />
                </div>
                <span className="weight-value">{((source.weight || 0) * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'backtest' && (
        <div className="tab-content">
          <div className="backtest-controls">
            <h3>Run Backtest</h3>
            <div className="date-inputs">
              <div className="input-group">
                <label>Start Date:</label>
                <input 
                  type="date" 
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                />
              </div>
              <div className="input-group">
                <label>End Date:</label>
                <input 
                  type="date" 
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                />
              </div>
              <button 
                onClick={runBacktest} 
                disabled={running}
                className="btn-primary"
              >
                {running ? 'Running...' : 'Run Backtest'}
              </button>
            </div>
          </div>

          <div className="backtest-results">
            <h3>Previous Backtests</h3>
            {loading ? (
              <div className="loading">Loading...</div>
            ) : backtests.length === 0 ? (
              <p className="empty-message">No backtests yet. Run your first backtest above!</p>
            ) : (
              <div className="results-grid">
                {backtests.map((result) => (
                  <div key={result.backtest_id} className="result-card">
                    <div className="result-header">
                      <span className="result-date">
                        {new Date(result.start_date).toLocaleDateString()} - {new Date(result.end_date).toLocaleDateString()}
                      </span>
                      <span className="result-time">
                        {new Date(result.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="result-metrics">
                      <div className="metric">
                        <label>Accuracy</label>
                        <span className="value">{(result.accuracy * 100).toFixed(1)}%</span>
                      </div>
                      <div className="metric">
                        <label>ROI</label>
                        <span className={`value ${result.roi >= 0 ? 'positive' : 'negative'}`}>
                          {result.roi >= 0 ? '+' : ''}{(result.roi * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="metric">
                        <label>Predictions</label>
                        <span className="value">{result.correct_predictions}/{result.total_predictions}</span>
                      </div>
                      <div className="metric">
                        <label>Avg Confidence</label>
                        <span className="value">{(result.avg_confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <style>{`
        .model-detail {
          padding: 20px;
          max-width: 1200px;
          margin: 0 auto;
        }

        .model-header {
          display: flex;
          align-items: center;
          gap: 15px;
          margin-bottom: 10px;
          margin-right: 50px;
        }

        .model-header h2 {
          margin: 0;
          color: #e2e8f0;
          flex: 1;
        }

        .status-badge {
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
        }

        .status-badge.active {
          background: rgba(72, 187, 120, 0.2);
          color: #48bb78;
        }

        .status-badge.inactive {
          background: rgba(160, 174, 192, 0.2);
          color: #a0aec0;
        }

        .model-description {
          color: #a0aec0;
          margin-bottom: 30px;
        }

        .tabs {
          display: flex;
          gap: 10px;
          border-bottom: 2px solid rgba(255, 255, 255, 0.1);
          margin-bottom: 30px;
        }

        .tab {
          background: none;
          border: none;
          color: #a0aec0;
          padding: 12px 24px;
          cursor: pointer;
          border-bottom: 2px solid transparent;
          margin-bottom: -2px;
          transition: all 0.2s;
        }

        .tab:hover {
          color: #e2e8f0;
        }

        .tab.active {
          color: #667eea;
          border-bottom-color: #667eea;
        }

        .tab-content {
          animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .tab-content h3 {
          color: #e2e8f0;
          margin-bottom: 20px;
        }

        .config-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 20px;
          margin-bottom: 30px;
        }

        .config-item {
          background: rgba(255, 255, 255, 0.05);
          padding: 15px;
          border-radius: 8px;
        }

        .config-item label {
          display: block;
          color: #a0aec0;
          font-size: 12px;
          margin-bottom: 5px;
        }

        .config-item span {
          color: #e2e8f0;
          font-weight: 600;
        }

        .weights-grid {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .weight-item {
          display: grid;
          grid-template-columns: 150px 1fr 60px;
          gap: 15px;
          align-items: center;
        }

        .weight-label {
          color: #e2e8f0;
          font-size: 14px;
        }

        .weight-bar {
          height: 8px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 4px;
          overflow: hidden;
        }

        .weight-fill {
          height: 100%;
          background: linear-gradient(90deg, #667eea, #764ba2);
          transition: width 0.3s;
        }

        .weight-value {
          color: #667eea;
          font-weight: 600;
          text-align: right;
        }

        .backtest-controls {
          background: rgba(255, 255, 255, 0.05);
          padding: 20px;
          border-radius: 12px;
          margin-bottom: 30px;
        }

        .date-inputs {
          display: flex;
          gap: 15px;
          align-items: flex-end;
        }

        .input-group {
          display: flex;
          flex-direction: column;
          gap: 5px;
        }

        .input-group label {
          color: #a0aec0;
          font-size: 14px;
        }

        .input-group input {
          padding: 8px 12px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 6px;
          color: #e2e8f0;
          font-size: 14px;
        }

        .input-group input:focus {
          outline: none;
          border-color: #667eea;
        }

        .btn-primary {
          padding: 8px 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border: none;
          border-radius: 6px;
          color: white;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s;
        }

        .btn-primary:hover:not(:disabled) {
          transform: translateY(-2px);
        }

        .btn-primary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .empty-message {
          color: #a0aec0;
          text-align: center;
          padding: 40px;
        }

        .results-grid {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .result-card {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 20px;
        }

        .result-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 15px;
          padding-bottom: 15px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .result-date {
          color: #e2e8f0;
          font-weight: 600;
        }

        .result-time {
          color: #a0aec0;
          font-size: 12px;
        }

        .result-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 20px;
        }

        .metric {
          display: flex;
          flex-direction: column;
          gap: 5px;
        }

        .metric label {
          color: #a0aec0;
          font-size: 12px;
        }

        .metric .value {
          color: #e2e8f0;
          font-size: 20px;
          font-weight: 700;
        }

        .metric .value.positive {
          color: #48bb78;
        }

        .metric .value.negative {
          color: #f56565;
        }

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
          max-width: 1000px;
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

        @media (max-width: 768px) {
          .date-inputs {
            flex-direction: column;
            align-items: stretch;
          }

          .result-metrics {
            grid-template-columns: 1fr 1fr;
          }

          .modal-content {
            padding: 20px;
            max-height: 95vh;
          }
        }
      `}</style>
      </div>
    </div>
  );
};
