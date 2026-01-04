import React, { useState, useEffect } from 'react';
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

interface RecommendationsProps {
  token: string;
}

const Recommendations: React.FC<RecommendationsProps> = ({ token }) => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [topRecommendation, setTopRecommendation] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    sport: 'NBA',
    model: 'consensus',
    risk_level: 'moderate'
  });

  useEffect(() => {
    fetchRecommendations();
    fetchTopRecommendation();
  }, [filters]);

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      const data = await apiService.getRecommendations(token, filters);
      setRecommendations(data.recommendations || []);
    } catch (err) {
      setError('Failed to fetch recommendations');
      console.error('Error fetching recommendations:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTopRecommendation = async () => {
    try {
      const data = await apiService.getTopRecommendation(token, filters);
      setTopRecommendation(data.recommendation);
    } catch (err) {
      console.error('Error fetching top recommendation:', err);
    }
  };

  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;
  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`;
  const formatOdds = (odds: number) => odds > 0 ? `+${odds}` : `${odds}`;

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'conservative': return 'text-green-600';
      case 'moderate': return 'text-yellow-600';
      case 'aggressive': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  if (loading) return <div className="no-data">Loading recommendations...</div>;
  if (error) return <div className="no-data">{error}</div>;

  return (
    <div className="predictions-section">
      <div className="games-header">
        <h2>Recommendations</h2>
        <p className="predictions-subtitle">Smart betting recommendations based on AI analysis</p>
      </div>
      
      <div className="filters">
        <select 
          className="filter-select"
          value={filters.sport}
          onChange={(e) => setFilters({...filters, sport: e.target.value})}
        >
          <option value="NBA">NBA</option>
          <option value="NFL">NFL</option>
        </select>
        <select 
          className="filter-select"
          value={filters.model}
          onChange={(e) => setFilters({...filters, model: e.target.value})}
        >
          <option value="consensus">Consensus</option>
        </select>
        <select 
          className="filter-select"
          value={filters.risk_level}
          onChange={(e) => setFilters({...filters, risk_level: e.target.value})}
        >
          <option value="conservative">Conservative</option>
          <option value="moderate">Moderate</option>
          <option value="aggressive">Aggressive</option>
        </select>
      </div>

      {/* Top Recommendation */}
      {topRecommendation && (
        <div className="game-card featured-recommendation">
          <div className="game-info">
            <div className="teams">
              <h3>🎯 Top Recommendation</h3>
              <div className="sport-tag">{topRecommendation.team_or_player}</div>
              <p className="game-time">{topRecommendation.market} • {topRecommendation.bookmaker}</p>
            </div>
          </div>
          <div className="prediction-info">
            <div className="probabilities">
              <div className="prob-item">
                <span className="prob-label">Bet Amount</span>
                <span className="prob-value home">{formatCurrency(topRecommendation.recommended_bet_amount)}</span>
              </div>
              <div className="prob-item">
                <span className="prob-label">Potential Payout</span>
                <span className="prob-value away">{formatCurrency(topRecommendation.potential_payout)}</span>
              </div>
            </div>
            <div className="confidence">
              <span className="confidence-label">Edge</span>
              <span className="confidence-value">{formatPercentage(topRecommendation.expected_value)}</span>
            </div>
          </div>
          <div className="game-meta">
            <span className="model">Confidence: {formatPercentage(topRecommendation.confidence_score)}</span>
            <span className="sport">Odds: {formatOdds(topRecommendation.odds)}</span>
          </div>
          {topRecommendation.reasoning && (
            <div className="reasoning">{topRecommendation.reasoning}</div>
          )}
        </div>
      )}

      {/* All Recommendations */}
      <div className="games-grid">
        {recommendations.length === 0 ? (
          <div className="no-data">No recommendations available for the selected filters.</div>
        ) : (
          recommendations.map((rec, index) => (
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
        )}
      </div>
    </div>
  );
};

export default Recommendations;
