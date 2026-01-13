import React, { useState, useEffect } from 'react';
import { bettingApi } from '../services/api';

interface AnalysisHistoryItem {
  pk: string;
  sk: string;
  game_id: string;
  model: string;
  analysis_type: string;
  sport: string;
  home_team?: string;
  away_team?: string;
  player_name?: string;
  prediction: string;
  confidence: number;
  reasoning: string;
  created_at: string;
  analysis_correct?: boolean;
  actual_home_won?: boolean;
  outcome_verified_at?: string;
}

interface AnalysisHistoryProps {
  token: string;
  settings: {
    sport: string;
    model: string;
    bookmaker: string;
  };
}

const AnalysisHistory: React.FC<AnalysisHistoryProps> = ({ token, settings }) => {
  const [analyses, setAnalyses] = useState<AnalysisHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'correct' | 'incorrect' | 'pending'>('all');
  const [typeFilter, setTypeFilter] = useState<'all' | 'game' | 'prop'>('all');

  useEffect(() => {
    fetchAnalysisHistory();
  }, [token, settings]);

  const fetchAnalysisHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // TODO: Create API endpoint for analysis history
      // For now, we'll use a placeholder
      const response = await bettingApi.getAnalysisHistory(token, {
        sport: settings.sport !== 'all' ? settings.sport : undefined,
        model: settings.model !== 'all' ? settings.model : undefined,
        bookmaker: settings.bookmaker !== 'all' ? settings.bookmaker : undefined,
      });
      
      setAnalyses(response.analyses || []);
    } catch (err) {
      console.error('Error fetching analysis history:', err);
      setError('Failed to load analysis history');
      setAnalyses([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredAnalyses = analyses.filter(analysis => {
    // Filter by accuracy
    if (filter === 'correct' && !analysis.analysis_correct) return false;
    if (filter === 'incorrect' && (analysis.analysis_correct !== false || analysis.analysis_correct === undefined)) return false;
    if (filter === 'pending' && analysis.outcome_verified_at) return false;
    
    // Filter by type
    if (typeFilter !== 'all' && analysis.analysis_type !== typeFilter) return false;
    
    return true;
  });

  const getAccuracyStats = () => {
    const verified = analyses.filter(a => a.outcome_verified_at);
    const correct = verified.filter(a => a.analysis_correct);
    const total = verified.length;
    
    return {
      total: analyses.length,
      verified: total,
      correct: correct.length,
      accuracy: total > 0 ? (correct.length / total * 100).toFixed(1) : '0.0'
    };
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (analysis: AnalysisHistoryItem) => {
    if (!analysis.outcome_verified_at) {
      return <span className="status-badge pending">Pending</span>;
    }
    if (analysis.analysis_correct) {
      return <span className="status-badge correct">✓ Correct</span>;
    }
    return <span className="status-badge incorrect">✗ Incorrect</span>;
  };

  const stats = getAccuracyStats();

  if (loading) return <div className="loading">Loading analysis history...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="analysis-history">
      <div className="analysis-history-header">
        <h2>Analysis History</h2>
        <div className="stats-summary">
          <div className="stat">
            <span className="stat-value">{stats.total}</span>
            <span className="stat-label">Total Analyses</span>
          </div>
          <div className="stat">
            <span className="stat-value">{stats.verified}</span>
            <span className="stat-label">Verified</span>
          </div>
          <div className="stat">
            <span className="stat-value">{stats.accuracy}%</span>
            <span className="stat-label">Accuracy</span>
          </div>
        </div>
      </div>

      <div className="filters">
        <select 
          className="filter-select"
          value={filter} 
          onChange={(e) => setFilter(e.target.value as any)}
        >
          <option value="all">All Results</option>
          <option value="correct">Correct Only</option>
          <option value="incorrect">Incorrect Only</option>
          <option value="pending">Pending Verification</option>
        </select>
        
        <select 
          className="filter-select"
          value={typeFilter} 
          onChange={(e) => setTypeFilter(e.target.value as any)}
        >
          <option value="all">All Types</option>
          <option value="game">Game Analysis</option>
          <option value="prop">Prop Analysis</option>
        </select>
      </div>

      <div className="analysis-list">
        {filteredAnalyses.length === 0 ? (
          <div className="no-data">No analysis history found</div>
        ) : (
          filteredAnalyses.map((analysis) => (
            <div key={`${analysis.pk}-${analysis.sk}`} className="analysis-card">
              <div className="analysis-header">
                <div className="analysis-title">
                  {analysis.analysis_type === 'game' ? (
                    <span>{analysis.home_team} vs {analysis.away_team}</span>
                  ) : (
                    <span>{analysis.player_name} - {analysis.sport.toUpperCase()}</span>
                  )}
                </div>
                <div className="analysis-meta">
                  <span className="model-badge">{analysis.model}</span>
                  {getStatusBadge(analysis)}
                </div>
              </div>
              
              <div className="analysis-content">
                <div className="analysis-prediction">
                  <strong>Analysis:</strong> {analysis.prediction}
                </div>
                <div className="analysis-confidence">
                  <strong>Confidence:</strong> {(analysis.confidence * 100).toFixed(1)}%
                </div>
                <div className="analysis-reasoning">
                  <strong>Reasoning:</strong> {analysis.reasoning}
                </div>
              </div>
              
              <div className="analysis-footer">
                <span className="analysis-date">
                  Created: {formatDate(analysis.created_at)}
                </span>
                {analysis.outcome_verified_at && (
                  <span className="verification-date">
                    Verified: {formatDate(analysis.outcome_verified_at)}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AnalysisHistory;
