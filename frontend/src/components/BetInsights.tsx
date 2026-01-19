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
  const [topInsight, setTopInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInsights();
    fetchTopInsight();
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
    } catch (err) {
      setError('Failed to fetch insights');
      console.error('Error fetching insights:', err);
    } finally {
      setLoading(false);
    }
  }, [token, settings]);

  const fetchTopInsight = useCallback(async () => {
    try {
      const data = await apiService.getTopInsight(token, {
        sport: settings.sport,
        model: settings.model,
        bookmaker: settings.bookmaker,
        type: 'game'
      });
      setTopInsight(data.top_insight);
    } catch (err) {
      console.error('Error fetching top insight:', err);
    }
  }, [token, settings]);

  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`;

  if (loading) return <div className="no-data">Loading insights...</div>;
  if (error) return <div className="no-data">{error}</div>;

  return (
    <div className="predictions-section">
      <div className="games-header">
        <h2>Insights</h2>
      </div>

      {/* Top Insight */}
      {topInsight && (
        <div className="game-card featured-recommendation">
          <div className="game-info">
            <div className="teams">
              <h3>🎯 Top Insight</h3>
              <div className="sport-tag">{topInsight.home_team && topInsight.away_team ? `${topInsight.away_team} @ ${topInsight.home_team}` : topInsight.player_name}</div>
              <p className="game-time">{topInsight.bookmaker} • {new Date(topInsight.commence_time).toLocaleString()}</p>
            </div>
          </div>
          <div className="prediction-info">
            <div className="probabilities">
              <div className="prob-item">
                <span className="prob-label">Insight</span>
                <span className="prob-value home">{topInsight.prediction}</span>
              </div>
            </div>
            <div className="confidence">
              <span className="confidence-label">Confidence</span>
              <span className="confidence-value">{formatPercentage(topInsight.confidence)}</span>
            </div>
          </div>
          <div className="game-meta">
            <span className="model">Model: {topInsight.model}</span>
          </div>
          {topInsight.reasoning && (
            <div className="reasoning">{topInsight.reasoning}</div>
          )}
        </div>
      )}

      {/* All Insights */}
      <div className="games-grid">
        {insights.map((insight: Insight, index: number) => (
            <div key={`${insight.game_id}-${index}`} className="game-card">
              <div className="game-info">
                <div className="teams">
                  <h3>{insight.home_team && insight.away_team ? `${insight.away_team} @ ${insight.home_team}` : insight.player_name}</h3>
                  <div className="sport-tag">{insight.sport}</div>
                  <p className="game-time">{insight.bookmaker} • {new Date(insight.commence_time).toLocaleString()}</p>
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
              <div className="game-meta">
                <span className="model">Model: {insight.model}</span>
              </div>
              {insight.reasoning && (
                <div className="reasoning">{insight.reasoning}</div>
              )}
            </div>
          ))
        }
      </div>
      
      {insights.length === 0 && (
        <div className="no-data">No insights available for the selected filters.</div>
      )}
    </div>
  );
};

export default BetInsights;
