import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'https://ddzbfblwr0.execute-api.us-east-1.amazonaws.com/prod';

interface Bet {
  bet_id: string;
  game: string;
  prediction: string;
  ensemble_confidence: number;
  final_confidence: number;
  ai_reasoning: string;
  ai_key_factors: string[];
  bet_amount: number;
  status: string;
  payout: number;
  placed_at: string;
}

interface DashboardData {
  current_bankroll: number;
  weekly_budget: number;
  total_bets: number;
  pending_bets: number;
  win_rate: number;
  roi: number;
  sports_performance: {
    [sport: string]: {
      record: string;
      win_rate: number;
      roi: number;
    };
  };
  confidence_accuracy: {
    [bucket: string]: {
      actual_win_rate: number;
      count: number;
    };
  };
  best_bet: {
    game: string;
    profit: number;
  } | null;
  worst_bet: {
    game: string;
    loss: number;
  } | null;
  ai_impact: {
    win_rate: number | null;
    bets_count: number;
  };
  bankroll_history: Array<{
    timestamp: string;
    amount: number;
  }>;
  recent_bets: Bet[];
}

export const BennyDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedBet, setExpandedBet] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/benny/dashboard`);
      setData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="loading">Loading Benny's dashboard...</div>
  );
  if (error) return (
    <div className="error">{error}</div>
  );
  if (!data) return null;

  const bankrollPercent = (data.current_bankroll / data.weekly_budget) * 100;

  return (
    <div className="benny-dashboard">
      <div className="benny-header">
        <h2>🤖 Benny's Trading Dashboard</h2>
        <p>Autonomous AI trader making virtual bets with a $100/week budget</p>
      </div>

      <div className="benny-stats">
        <div className="stat-card">
          <div className="stat-label">Current Bankroll</div>
          <div className="stat-value">${data.current_bankroll.toFixed(2)}</div>
          <div className="stat-progress">
            <div className="progress-bar" style={{ width: `${Math.min(bankrollPercent, 100)}%` }} />
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Win Rate</div>
          <div className="stat-value">{(data.win_rate * 100).toFixed(1)}%</div>
          <div className="stat-subtitle">{data.total_bets - data.pending_bets} settled</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">ROI</div>
          <div className={`stat-value ${data.roi >= 0 ? 'positive' : 'negative'}`}>
            {data.roi >= 0 ? '+' : ''}{(data.roi * 100).toFixed(1)}%
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Total Bets</div>
          <div className="stat-value">{data.total_bets}</div>
          <div className="stat-subtitle">{data.pending_bets} pending</div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="performance-section">
        <h3>Performance Analytics</h3>

        {/* Bankroll Chart */}
        {data.bankroll_history.length > 1 && (
          <div className="bankroll-chart">
            <h4>Bankroll Over Time</h4>
            <div className="chart-container">
              <svg viewBox="0 0 800 200" className="chart-svg">
                {/* Grid lines */}
                <line x1="50" y1="20" x2="50" y2="180" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                <line x1="50" y1="180" x2="780" y2="180" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                
                {/* Bankroll line */}
                <polyline
                  points={data.bankroll_history.map((point, i) => {
                    const x = 50 + (i / (data.bankroll_history.length - 1)) * 730;
                    const y = 180 - ((point.amount / data.weekly_budget) * 160);
                    return `${x},${y}`;
                  }).join(' ')}
                  fill="none"
                  stroke="#667eea"
                  strokeWidth="2"
                />
                
                {/* Data points */}
                {data.bankroll_history.map((point, i) => {
                  const x = 50 + (i / (data.bankroll_history.length - 1)) * 730;
                  const y = 180 - ((point.amount / data.weekly_budget) * 160);
                  return <circle key={i} cx={x} cy={y} r="3" fill="#667eea" />;
                })}
                
                {/* Labels */}
                <text x="25" y="25" fill="#a0aec0" fontSize="12">${data.weekly_budget}</text>
                <text x="25" y="185" fill="#a0aec0" fontSize="12">$0</text>
                <text x="750" y="195" fill="#a0aec0" fontSize="12">Now</text>
              </svg>
            </div>
          </div>
        )}
        
        <div className="metrics-grid">
          {/* By Sport */}
          {Object.keys(data.sports_performance).length > 0 && (
            <div className="metric-card">
              <h4>Performance by Sport</h4>
              {Object.entries(data.sports_performance).map(([sport, stats]) => (
                <div key={sport} className="sport-stat">
                  <span className="sport-name">{sport.replace('_', ' ').toUpperCase()}</span>
                  <span className="sport-record">{stats.record}</span>
                  <span className="sport-winrate">{(stats.win_rate * 100).toFixed(0)}%</span>
                  <span className={`sport-roi ${stats.roi >= 0 ? 'positive' : 'negative'}`}>
                    {stats.roi >= 0 ? '+' : ''}{(stats.roi * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Confidence Calibration */}
          {Object.keys(data.confidence_accuracy).length > 0 && (
            <div className="metric-card">
              <h4>Confidence Calibration</h4>
              {Object.entries(data.confidence_accuracy).map(([bucket, stats]) => (
                <div key={bucket} className="confidence-stat">
                  <span className="conf-bucket">{bucket}</span>
                  <span className="conf-actual">{(stats.actual_win_rate * 100).toFixed(0)}% actual</span>
                  <span className="conf-count">({stats.count} bets)</span>
                </div>
              ))}
            </div>
          )}

          {/* Best/Worst Bets */}
          <div className="metric-card">
            <h4>Notable Bets</h4>
            {data.best_bet && (
              <div className="notable-bet best">
                <span className="label">🏆 Best:</span>
                <span className="game">{data.best_bet.game}</span>
                <span className="amount positive">+${data.best_bet.profit.toFixed(2)}</span>
              </div>
            )}
            {data.worst_bet && (
              <div className="notable-bet worst">
                <span className="label">💔 Worst:</span>
                <span className="game">{data.worst_bet.game}</span>
                <span className="amount negative">-${data.worst_bet.loss.toFixed(2)}</span>
              </div>
            )}
          </div>

          {/* AI Impact */}
          {data.ai_impact.win_rate !== null && (
            <div className="metric-card">
              <h4>AI Reasoning Impact</h4>
              <div className="ai-stat">
                <div className="ai-winrate">
                  <span className="label">Win Rate with AI:</span>
                  <span className="value">{(data.ai_impact.win_rate * 100).toFixed(1)}%</span>
                </div>
                <div className="ai-count">{data.ai_impact.bets_count} bets analyzed</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="benny-bets">
        <h3>Recent Bets</h3>
        <div className="bets-table">
          {data.recent_bets.map((bet) => (
            <div key={bet.bet_id} className={`bet-card ${bet.status}`}>
              <div 
                className={`bet-row ${bet.status}`}
                onClick={() => setExpandedBet(expandedBet === bet.bet_id ? null : bet.bet_id)}
              >
                <div className="bet-game">{bet.game}</div>
                <div className="bet-prediction">{bet.prediction}</div>
                <div className="bet-confidence">
                  {bet.ensemble_confidence !== bet.final_confidence ? (
                    <>
                      <span className="ensemble">{(bet.ensemble_confidence * 100).toFixed(0)}%</span>
                      <span className="arrow">→</span>
                      <span className="final">{(bet.final_confidence * 100).toFixed(0)}%</span>
                    </>
                  ) : (
                    <span>{(bet.final_confidence * 100).toFixed(0)}%</span>
                  )}
                </div>
                <div className="bet-amount">${bet.bet_amount.toFixed(2)}</div>
                <div className={`bet-status ${bet.status}`}>
                  {bet.status === 'won' && `+$${bet.payout.toFixed(2)}`}
                  {bet.status === 'lost' && `-$${bet.bet_amount.toFixed(2)}`}
                  {bet.status === 'pending' && 'Pending'}
                </div>
                <div className="expand-icon">{expandedBet === bet.bet_id ? '▼' : '▶'}</div>
              </div>
              
              {expandedBet === bet.bet_id && bet.ai_reasoning && (
                <div className="bet-reasoning">
                  <div className="reasoning-header">🤖 Benny's Analysis</div>
                  <p className="reasoning-text">{bet.ai_reasoning}</p>
                  {bet.ai_key_factors && bet.ai_key_factors.length > 0 && (
                    <div className="key-factors">
                      <strong>Key Factors:</strong>
                      <ul>
                        {bet.ai_key_factors.map((factor, idx) => (
                          <li key={idx}>{factor}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .benny-dashboard {
          padding: 20px;
          max-width: 1400px;
          margin: 0 auto;
        }

        .benny-header {
          margin-bottom: 30px;
        }

        .benny-header h2 {
          color: #e2e8f0;
          margin: 0 0 8px 0;
          font-size: 28px;
        }

        .benny-header p {
          color: #a0aec0;
          margin: 0;
        }

        .benny-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 20px;
          margin-bottom: 40px;
        }

        .stat-card {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 20px;
          transition: all 0.3s ease;
        }

        .stat-card:hover {
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(102, 126, 234, 0.3);
          transform: translateY(-2px);
        }

        .stat-label {
          color: #a0aec0;
          font-size: 14px;
          margin-bottom: 8px;
        }

        .stat-value {
          color: #e2e8f0;
          font-size: 32px;
          font-weight: 700;
          margin-bottom: 8px;
        }

        .stat-value.positive {
          color: #48bb78;
        }

        .stat-value.negative {
          color: #f56565;
        }

        .stat-subtitle {
          color: #718096;
          font-size: 12px;
        }

        .stat-progress {
          height: 4px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 2px;
          overflow: hidden;
          margin-top: 8px;
        }

        .progress-bar {
          height: 100%;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          transition: width 0.3s;
        }

        .benny-bets h3 {
          color: #e2e8f0;
          margin-bottom: 20px;
        }

        .performance-section {
          margin-bottom: 40px;
        }

        .performance-section h3 {
          color: #e2e8f0;
          margin-bottom: 20px;
        }

        .bankroll-chart {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 20px;
        }

        .bankroll-chart h4 {
          color: #e2e8f0;
          font-size: 16px;
          margin-bottom: 15px;
        }

        .chart-container {
          width: 100%;
          height: 200px;
        }

        .chart-svg {
          width: 100%;
          height: 100%;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 20px;
        }

        .metric-card {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 20px;
        }

        .metric-card h4 {
          color: #e2e8f0;
          font-size: 16px;
          margin-bottom: 15px;
        }

        .sport-stat {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr 1fr;
          gap: 10px;
          padding: 10px 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          align-items: center;
        }

        .sport-stat:last-child {
          border-bottom: none;
        }

        .sport-name {
          color: #e2e8f0;
          font-weight: 600;
          font-size: 12px;
        }

        .sport-record {
          color: #a0aec0;
          font-size: 14px;
        }

        .sport-winrate {
          color: #667eea;
          font-weight: 600;
        }

        .sport-roi {
          font-weight: 600;
          text-align: right;
        }

        .confidence-stat {
          display: flex;
          justify-content: space-between;
          padding: 10px 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .confidence-stat:last-child {
          border-bottom: none;
        }

        .conf-bucket {
          color: #e2e8f0;
          font-weight: 600;
        }

        .conf-actual {
          color: #667eea;
        }

        .conf-count {
          color: #718096;
          font-size: 12px;
        }

        .notable-bet {
          display: grid;
          grid-template-columns: auto 1fr auto;
          gap: 10px;
          padding: 10px 0;
          align-items: center;
        }

        .notable-bet .label {
          color: #a0aec0;
          font-size: 14px;
        }

        .notable-bet .game {
          color: #e2e8f0;
          font-size: 13px;
        }

        .notable-bet .amount {
          font-weight: 600;
        }

        .ai-stat {
          padding: 10px 0;
        }

        .ai-winrate {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
        }

        .ai-winrate .label {
          color: #a0aec0;
        }

        .ai-winrate .value {
          color: #667eea;
          font-weight: 600;
          font-size: 18px;
        }

        .ai-count {
          color: #718096;
          font-size: 12px;
        }

        .bets-table {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .bet-card {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          overflow: hidden;
          transition: all 0.3s ease;
        }

        .bet-card:hover {
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(102, 126, 234, 0.3);
        }

        .bet-row {
          display: grid;
          grid-template-columns: 2fr 1.5fr 1fr 0.8fr 1fr 0.3fr;
          gap: 15px;
          padding: 15px;
          align-items: center;
          cursor: pointer;
          transition: background 0.2s;
        }

        .bet-row:hover {
          background: rgba(255, 255, 255, 0.08);
        }

        .bet-card.won .bet-row {
          border-left: 3px solid #48bb78;
        }

        .bet-card.lost .bet-row {
          border-left: 3px solid #f56565;
        }

        .bet-card.pending .bet-row {
          border-left: 3px solid #ed8936;
        }

        .bet-game {
          color: #e2e8f0;
          font-weight: 600;
        }

        .bet-prediction {
          color: #a0aec0;
        }

        .bet-confidence {
          color: #667eea;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 5px;
        }

        .bet-confidence .ensemble {
          color: #a0aec0;
          font-size: 12px;
        }

        .bet-confidence .arrow {
          color: #718096;
          font-size: 12px;
        }

        .bet-confidence .final {
          color: #667eea;
        }

        .expand-icon {
          color: #718096;
          font-size: 12px;
          text-align: center;
        }

        .bet-reasoning {
          padding: 20px;
          background: rgba(102, 126, 234, 0.1);
          border-top: 1px solid rgba(102, 126, 234, 0.2);
        }

        .reasoning-header {
          color: #667eea;
          font-weight: 600;
          margin-bottom: 10px;
          font-size: 14px;
        }

        .reasoning-text {
          color: #e2e8f0;
          line-height: 1.6;
          margin-bottom: 15px;
        }

        .key-factors {
          color: #a0aec0;
          font-size: 14px;
        }

        .key-factors strong {
          color: #e2e8f0;
        }

        .key-factors ul {
          margin: 8px 0 0 20px;
          padding: 0;
        }

        .key-factors li {
          margin: 4px 0;
        }

        .bet-amount {
          color: #e2e8f0;
        }

        .bet-status {
          font-weight: 600;
          text-align: right;
        }

        .bet-status.won {
          color: #48bb78;
        }

        .bet-status.lost {
          color: #f56565;
        }

        .bet-status.pending {
          color: #ed8936;
        }

        @media (max-width: 768px) {
          .benny-stats {
            grid-template-columns: 1fr;
          }

          .bet-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }

          .bet-status {
            text-align: left;
          }
        }
      `}</style>
    </div>
  );
};
