import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod';

interface ModelSummary {
  model_name: string;
  total_analyses: number;
  correct_analyses: number;
  incorrect_analyses: number;
  accuracy: number;
  sports_covered: string[];
}

interface BetTypeStats {
  total: number;
  correct: number;
  incorrect: number;
  accuracy: number;
}

interface ConfidenceStats {
  confidence_range: string;
  total: number;
  correct: number;
  accuracy: number;
}

interface TimeSeriesData {
  date: string;
  total: number;
  correct: number;
  accuracy: number;
}

interface ModelAnalyticsProps {
  token: string;
}

const PerformanceChart: React.FC<{ data: TimeSeriesData[] }> = ({ data }) => {
  const width = 800;
  const height = 300;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
  
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  
  const maxAccuracy = 100;
  const minAccuracy = 0;
  
  const xScale = (index: number) => (index / (data.length - 1)) * chartWidth;
  const yScale = (accuracy: number) => chartHeight - ((accuracy - minAccuracy) / (maxAccuracy - minAccuracy)) * chartHeight;
  
  const pathData = data.map((d, i) => {
    const x = xScale(i);
    const y = yScale(d.accuracy);
    return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
  }).join(' ');
  
  return (
    <div style={{ overflowX: 'auto' }}>
      <svg width={width} height={height} style={{ display: 'block', margin: '0 auto' }}>
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map(val => (
            <g key={val}>
              <line
                x1={0}
                y1={yScale(val)}
                x2={chartWidth}
                y2={yScale(val)}
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="1"
              />
              <text
                x={-10}
                y={yScale(val)}
                textAnchor="end"
                alignmentBaseline="middle"
                fill="rgba(255,255,255,0.7)"
                fontSize="12"
              >
                {val}%
              </text>
            </g>
          ))}
          
          {/* Line */}
          <path
            d={pathData}
            fill="none"
            stroke="#00d4ff"
            strokeWidth="2"
          />
          
          {/* Points */}
          {data.map((d, i) => (
            <g key={i}>
              <circle
                cx={xScale(i)}
                cy={yScale(d.accuracy)}
                r="4"
                fill="#00d4ff"
              />
              <title>{`${d.date}: ${d.accuracy}% (${d.correct}/${d.total})`}</title>
            </g>
          ))}
          
          {/* X-axis labels */}
          {data.filter((_, i) => i % Math.ceil(data.length / 6) === 0).map((d, i, arr) => {
            const index = data.indexOf(d);
            return (
              <text
                key={index}
                x={xScale(index)}
                y={chartHeight + 20}
                textAnchor="middle"
                fill="rgba(255,255,255,0.7)"
                fontSize="12"
              >
                {new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </text>
            );
          })}
        </g>
      </svg>
    </div>
  );
};

export const ModelAnalytics: React.FC<ModelAnalyticsProps> = ({ token }) => {
  const [summary, setSummary] = useState<Record<string, ModelSummary>>({});
  const [byBetType, setByBetType] = useState<Record<string, Record<string, BetTypeStats>>>({});
  const [confidence, setConfidence] = useState<Record<string, ConfidenceStats>>({});
  const [overTime, setOverTime] = useState<TimeSeriesData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      fetchAnalytics();
    }
  }, [token]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const headers = { Authorization: `Bearer ${token}` };

      const [summaryRes, betTypeRes, confidenceRes, overTimeRes] = await Promise.all([
        axios.get(`${API_URL}/analytics?type=summary`, { headers }),
        axios.get(`${API_URL}/analytics?type=by_bet_type`, { headers }),
        axios.get(`${API_URL}/analytics?type=confidence&model=consensus`, { headers }),
        axios.get(`${API_URL}/analytics?type=over_time&model=consensus&days=30`, { headers }),
      ]);

      setSummary(summaryRes.data);
      setByBetType(betTypeRes.data);
      setConfidence(confidenceRes.data);
      setOverTime(overTimeRes.data || []);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading analytics...</div>;
  if (error) return <div className="error">{error}</div>;

  const consensusModel = summary['consensus'];
  const consensusBetTypes = byBetType['consensus'] || {};

  return (
    <div className="analytics-container">
      <h2>Model Performance Analytics</h2>

      {/* Overall Summary */}
      {consensusModel && (
        <div className="analytics-card">
          <h3>Overall Performance</h3>
          <div className="stats-grid">
            <div className="stat">
              <div className="stat-value">{consensusModel.accuracy.toFixed(1)}%</div>
              <div className="stat-label">Accuracy</div>
            </div>
            <div className="stat">
              <div className="stat-value">{consensusModel.total_analyses}</div>
              <div className="stat-label">Total Analyses</div>
            </div>
            <div className="stat">
              <div className="stat-value">{consensusModel.correct_analyses}</div>
              <div className="stat-label">Correct</div>
            </div>
            <div className="stat">
              <div className="stat-value">{consensusModel.incorrect_analyses}</div>
              <div className="stat-label">Incorrect</div>
            </div>
          </div>
        </div>
      )}

      {/* By Bet Type */}
      <div className="analytics-card">
        <h3>Performance by Bet Type</h3>
        <div className="bet-type-grid">
          {Object.entries(consensusBetTypes).map(([betType, stats]) => (
            <div key={betType} className="bet-type-card">
              <h4>{betType === 'game' ? 'Game Bets' : 'Prop Bets'}</h4>
              <div className="accuracy-circle" style={{ 
                background: `conic-gradient(#4caf50 ${stats.accuracy * 3.6}deg, #e0e0e0 0deg)` 
              }}>
                <div className="accuracy-text">{stats.accuracy.toFixed(1)}%</div>
              </div>
              <div className="bet-type-stats">
                <div>{stats.correct} / {stats.total} correct</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Confidence Analysis */}
      <div className="analytics-card">
        <h3>Accuracy by Confidence Level</h3>
        <div className="confidence-bars">
          {Object.entries(confidence).map(([level, stats]) => (
            <div key={level} className="confidence-row">
              <div className="confidence-label">
                {level.charAt(0).toUpperCase() + level.slice(1)} ({stats.confidence_range})
              </div>
              <div className="confidence-bar-container">
                <div 
                  className="confidence-bar" 
                  style={{ width: `${stats.accuracy}%`, backgroundColor: getConfidenceColor(stats.accuracy) }}
                />
                {stats.total > 0 && <span className="confidence-percentage">{stats.accuracy.toFixed(1)}%</span>}
              </div>
              <div className="confidence-count">{stats.correct}/{stats.total}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Over Time */}
      {overTime.length > 0 && (
        <div className="analytics-card">
          <h3>Performance Over Time (Last 30 Days)</h3>
          <PerformanceChart data={overTime} />
        </div>
      )}

      <style>{`
        .analytics-container {
          padding: 20px;
          max-width: 1200px;
          margin: 0 auto;
        }

        .analytics-card {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 24px;
          margin-bottom: 24px;
          transition: all 0.3s ease;
        }

        .analytics-card:hover {
          border-color: rgba(0, 212, 255, 0.3);
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .analytics-card h3 {
          margin-top: 0;
          margin-bottom: 20px;
          color: #fff;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 20px;
        }

        .stat {
          text-align: center;
        }

        .stat-value {
          font-size: 32px;
          font-weight: bold;
          color: #00d4ff;
        }

        .stat-label {
          font-size: 14px;
          color: rgba(255, 255, 255, 0.7);
          margin-top: 8px;
        }

        .bet-type-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 24px;
        }

        .bet-type-card {
          text-align: center;
        }

        .bet-type-card h4 {
          margin-top: 0;
          margin-bottom: 16px;
          color: rgba(255, 255, 255, 0.9);
        }

        .accuracy-circle {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          margin: 0 auto 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }

        .accuracy-circle::before {
          content: '';
          position: absolute;
          width: 90px;
          height: 90px;
          background: rgba(26, 26, 46, 0.9);
          border-radius: 50%;
        }

        .accuracy-text {
          position: relative;
          z-index: 1;
          font-size: 24px;
          font-weight: bold;
          color: #fff;
        }

        .bet-type-stats {
          color: rgba(255, 255, 255, 0.7);
          font-size: 14px;
        }

        .confidence-bars {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .confidence-row {
          display: grid;
          grid-template-columns: 150px 1fr 80px;
          gap: 12px;
          align-items: center;
        }

        .confidence-label {
          font-weight: 500;
          color: rgba(255, 255, 255, 0.9);
        }

        .confidence-bar-container {
          background: rgba(255, 255, 255, 0.1);
          height: 32px;
          border-radius: 4px;
          overflow: hidden;
          position: relative;
        }

        .confidence-bar {
          height: 100%;
          transition: width 0.3s ease;
        }

        .confidence-percentage {
          position: absolute;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          font-weight: bold;
          font-size: 14px;
          color: #fff;
        }

        .confidence-count {
          text-align: right;
          color: rgba(255, 255, 255, 0.7);
          font-size: 14px;
        }

        .loading, .error {
          text-align: center;
          padding: 40px;
          font-size: 18px;
          color: rgba(255, 255, 255, 0.9);
        }

        .error {
          color: #ff6b6b;
        }
      `}</style>
    </div>
  );
};

function getConfidenceColor(accuracy: number): string {
  if (accuracy >= 70) return '#4caf50';
  if (accuracy >= 50) return '#ff9800';
  return '#f44336';
}
