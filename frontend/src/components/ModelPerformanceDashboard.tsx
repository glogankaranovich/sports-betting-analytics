import React, { useState, useEffect } from 'react';
import { bettingApi } from '../services/api';

interface ModelStats {
  model: string;
  totalAnalyses: number;
  correctAnalyses: number;
  accuracy: number;
  description: string;
}

interface ModelPerformanceDashboardProps {
  token: string;
  settings: {
    bookmaker: string;
    sport: string;
    model: string;
  };
}

const ModelPerformanceDashboard: React.FC<ModelPerformanceDashboardProps> = ({ token, settings }) => {
  const [modelStats, setModelStats] = useState<ModelStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const modelDescriptions = {
    consensus: "Analyzes bookmaker consensus by averaging implied probabilities across multiple sportsbooks to identify market agreement.",
    value: "Identifies value betting opportunities by finding low-vig lines and favorable odds compared to true probability estimates.",
    momentum: "Tracks line movement patterns and betting market momentum to predict direction of odds changes and sharp money."
  };

  useEffect(() => {
    const fetchModelPerformance = async () => {
      try {
        setLoading(true);
        const response = await bettingApi.getAnalysisHistory(token, {
          bookmaker: settings.bookmaker
        });
        
        if (response.success && response.data) {
          const analyses = response.data;
          
          // Calculate stats for each model
          const stats: { [key: string]: ModelStats } = {};
          
          analyses.forEach((analysis: any) => {
            const model = analysis.model;
            if (!stats[model]) {
              stats[model] = {
                model,
                totalAnalyses: 0,
                correctAnalyses: 0,
                accuracy: 0,
                description: modelDescriptions[model as keyof typeof modelDescriptions] || 'Model description not available'
              };
            }
            
            stats[model].totalAnalyses++;
            if (analysis.outcome_verified && analysis.outcome_correct) {
              stats[model].correctAnalyses++;
            }
          });
          
          // Calculate accuracy percentages
          Object.values(stats).forEach(stat => {
            stat.accuracy = stat.totalAnalyses > 0 ? (stat.correctAnalyses / stat.totalAnalyses) * 100 : 0;
          });
          
          setModelStats(Object.values(stats));
        }
      } catch (err) {
        setError('Failed to load model performance data');
        console.error('Error fetching model performance:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchModelPerformance();
  }, [token, settings.bookmaker]);

  if (loading) {
    return <div className="loading">Loading model performance data...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="model-performance-dashboard">
      <h2>Model Performance Dashboard</h2>
      <p className="dashboard-subtitle">Performance metrics and accuracy statistics for each analysis model</p>
      
      <div className="model-cards">
        {modelStats.map((stats) => (
          <div key={stats.model} className="model-card">
            <div className="model-header">
              <h3 className="model-name">{stats.model.charAt(0).toUpperCase() + stats.model.slice(1)} Model</h3>
              <div className="accuracy-badge">
                <span className="accuracy-value">{stats.accuracy.toFixed(1)}%</span>
                <span className="accuracy-label">Accuracy</span>
              </div>
            </div>
            
            <p className="model-description">{stats.description}</p>
            
            <div className="model-metrics">
              <div className="metric">
                <span className="metric-value">{stats.totalAnalyses}</span>
                <span className="metric-label">Total Analyses</span>
              </div>
              <div className="metric">
                <span className="metric-value">{stats.correctAnalyses}</span>
                <span className="metric-label">Correct Predictions</span>
              </div>
              <div className="metric">
                <span className="metric-value">{stats.totalAnalyses - stats.correctAnalyses}</span>
                <span className="metric-label">Incorrect Predictions</span>
              </div>
            </div>
            
            <div className="accuracy-bar">
              <div 
                className="accuracy-fill" 
                style={{ width: `${stats.accuracy}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
      
      {modelStats.length === 0 && (
        <div className="no-data">
          <p>No model performance data available yet.</p>
          <p>Performance metrics will appear after analyses have been generated and outcomes verified.</p>
        </div>
      )}
    </div>
  );
};

export default ModelPerformanceDashboard;
