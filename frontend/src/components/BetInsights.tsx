import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';

interface Insight {
  game_id: string;
  sport: string;
  model: string;
  analysis_type: string;
  bookmaker: string;
  prediction: string;
  confidence: number;
  reasoning: string;
  home_team?: string;
  away_team?: string;
  player_name?: string;
  created_at: string;
  commence_time: string;
}

interface BetInsightsProps {
  token: string;
  settings: {
    sport: string;
    bookmaker: string;
    model: string;
    riskTolerance: string;
  };
}

const BetInsights: React.FC<BetInsightsProps> = ({ token, settings }) => {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastEvaluatedKey, setLastEvaluatedKey] = useState<string | null>(null);

  useEffect(() => {
    fetchInsights();
  }, [settings]);

  const fetchInsights = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getInsights(token, {
        sport: settings.sport,
        model: settings.model,
        bookmaker: settings.bookmaker,
        type: 'game',
        limit: 20
      });
      setInsights(data.insights || []);
      setLastEvaluatedKey(data.lastEvaluatedKey || null);
    } catch (err) {
      setError('Failed to fetch insights');
      console.error('Error fetching insights:', err);
    } finally {
      setLoading(false);
    }
  }, [token, settings]);

  const loadMore = async () => {
    if (!lastEvaluatedKey || loadingMore) return;
    
    try {
      setLoadingMore(true);
      const data = await apiService.getInsights(token, {
        sport: settings.sport,
        model: settings.model,
        bookmaker: settings.bookmaker,
        type: 'game',
        limit: 20,
        lastEvaluatedKey
      });
      setInsights(prev => [...prev, ...(data.insights || [])]);
      setLastEvaluatedKey(data.lastEvaluatedKey || null);
    } catch (err) {
      console.error('Error loading more insights:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`;

  if (loading) return <div className="no-data">Loading insights...</div>;
  if (error) return <div className="no-data">{error}</div>;

  return (
    <div className="predictions-section">
      <div className="games-header">
        <h2>Insights</h2>
      </div>

      {/* All Insights */}
      <div className="games-grid">
        {insights.map((insight: Insight, index: number) => (
            <div key={`${insight.game_id}-${index}`} className="game-card">
              <div className="game-info">
                <div className="teams">
                  <h3>{insight.home_team && insight.away_team ? `${insight.away_team} @ ${insight.home_team}` : insight.player_name}</h3>
                  <div className="sport-tag">{insight.sport}</div>
                </div>
              </div>
              <div className="prediction-info">
                <div className="probabilities">
                  <div className="prob-item">
                    <span className="prob-label">Insight</span>
                    <span className="prob-value home">{insight.prediction}</span>
                  </div>
                </div>
                <div className="confidence">
                  <span className="confidence-label">Confidence</span>
                  <span className="confidence-value">{formatPercentage(insight.confidence)}</span>
                </div>
              </div>
              {insight.reasoning && (
                <div className="reasoning">{insight.reasoning}</div>
              )}
              <div className="game-meta">
                <span className="model">Model: {insight.model}</span>
                <span className="game-time">{new Date(insight.commence_time).toLocaleString()}</span>
              </div>
            </div>
          ))
        }
      </div>
      
      {insights.length === 0 && (
        <div className="no-data">No insights available for the selected filters.</div>
      )}

      {lastEvaluatedKey && (
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <button 
            onClick={loadMore} 
            disabled={loadingMore}
            style={{
              padding: '10px 20px',
              fontSize: '16px',
              cursor: loadingMore ? 'not-allowed' : 'pointer',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px'
            }}
          >
            {loadingMore ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
};

export default BetInsights;
