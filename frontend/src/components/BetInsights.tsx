import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';

interface Recommendation {
  game_id: string;
  sport: string;
  bet_type: string;
  team_or_player: string;
  market: string;
  predicted_probability: number;
  confidence_score: number;
  expected_value: number;
  risk_level: string;
  recommended_bet_amount: number;
  potential_payout: number;
  bookmaker: string;
  odds: number;
  reasoning: string;
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
  const [insights, setInsights] = useState<Recommendation[]>([]);
  const [topInsight, setTopInsight] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInsights();
    fetchTopInsight();
  }, [settings]);

  const fetchInsights = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getRecommendations(token, settings);
      setInsights(data.recommendations || []);
    } catch (err) {
      setError('Failed to fetch insights');
      console.error('Error fetching insights:', err);
    } finally {
      setLoading(false);
    }
  }, [token, settings]);

  const fetchTopInsight = useCallback(async () => {
    try {
      const data = await apiService.getTopRecommendation(token, settings);
      setTopInsight(data.recommendation);
    } catch (err) {
      console.error('Error fetching top insight:', err);
    }
  }, [token, settings]);

  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;
  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`;
  const formatOdds = (odds: number) => odds > 0 ? `+${odds}` : `${odds}`;

  // const getRiskColor = (riskLevel: string) => {
  //   switch (riskLevel) {
  //     case 'conservative': return 'text-green-600';
  //     case 'moderate': return 'text-yellow-600';
  //     case 'aggressive': return 'text-red-600';
  //     default: return 'text-gray-600';
  //   }
  // };

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
              <div className="sport-tag">{topInsight.team_or_player}</div>
              <p className="game-time">{topInsight.market} • {topInsight.bookmaker}</p>
            </div>
          </div>
          <div className="prediction-info">
            <div className="probabilities">
              <div className="prob-item">
                <span className="prob-label">Bet Amount</span>
                <span className="prob-value home">{formatCurrency(topInsight.recommended_bet_amount)}</span>
              </div>
              <div className="prob-item">
                <span className="prob-label">Potential Payout</span>
                <span className="prob-value away">{formatCurrency(topInsight.potential_payout)}</span>
              </div>
            </div>
            <div className="confidence">
              <span className="confidence-label">Edge</span>
              <span className="confidence-value">{formatPercentage(topInsight.expected_value)}</span>
            </div>
          </div>
          <div className="game-meta">
            <span className="model">Confidence: {formatPercentage(topInsight.confidence_score)}</span>
            <span className="sport">Odds: {formatOdds(topInsight.odds)}</span>
          </div>
          {topInsight.reasoning && (
            <div className="reasoning">{topInsight.reasoning}</div>
          )}
        </div>
      )}

      {/* All Insights */}
      <div className="games-grid">
        {insights.map((rec: any, index: number) => (
            <div key={`${rec.game_id}-${index}`} className="game-card">
              <div className="game-info">
                <div className="teams">
                  <h3>{rec.team_or_player}</h3>
                  <div className="sport-tag">{rec.market}</div>
                  <p className="game-time">{rec.bookmaker} • {rec.bet_type}</p>
                </div>
              </div>
              <div className="prediction-info">
                <div className="probabilities">
                  <div className="prob-item">
                    <span className="prob-label">Bet Amount</span>
                    <span className="prob-value home">{formatCurrency(rec.recommended_bet_amount)}</span>
                  </div>
                  <div className="prob-item">
                    <span className="prob-label">Potential Payout</span>
                    <span className="prob-value away">{formatCurrency(rec.potential_payout)}</span>
                  </div>
                </div>
                <div className="confidence">
                  <span className="confidence-label">Edge</span>
                  <span className="confidence-value">{formatPercentage(rec.expected_value)}</span>
                </div>
              </div>
              <div className="game-meta">
                <span className="model">Confidence: {formatPercentage(rec.confidence_score)}</span>
                <span className="sport">Odds: {formatOdds(rec.odds)} • {rec.risk_level}</span>
              </div>
              {rec.reasoning && (
                <div className="reasoning">{rec.reasoning}</div>
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
