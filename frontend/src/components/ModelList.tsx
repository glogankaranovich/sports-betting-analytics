import React from 'react';
import './ModelList.css';

interface UserModel {
  model_id: string;
  name: string;
  description: string;
  sport: string;
  status: string;
  bet_types: string[];
  min_confidence: number;
  data_sources: Record<string, { enabled: boolean; weight: number }>;
  created_at: string;
}

interface ModelListProps {
  models: UserModel[];
  onEdit: (modelId: string) => void;
  onDelete: (modelId: string) => void;
  onToggleStatus: (modelId: string, currentStatus: string) => void;
  onView: (model: UserModel) => void;
}

const SPORT_LABELS: Record<string, string> = {
  basketball_nba: 'NBA',
  americanfootball_nfl: 'NFL',
  baseball_mlb: 'MLB',
  icehockey_nhl: 'NHL',
  soccer_epl: 'EPL',
  'basketball_mens-college-basketball': 'NCAA Men\'s Basketball',
  'basketball_womens-college-basketball': 'NCAA Women\'s Basketball',
  'football_college-football': 'NCAA Football',
};

const BET_TYPE_LABELS: Record<string, string> = {
  h2h: 'Moneyline',
  spreads: 'Spread',
  totals: 'Totals',
  props: 'Props',
};

const DATA_SOURCE_LABELS: Record<string, string> = {
  team_stats: 'Team Stats',
  odds_movement: 'Odds Movement',
  recent_form: 'Recent Form',
  rest_schedule: 'Rest & Schedule',
  head_to_head: 'Head-to-Head',
  player_stats: 'Player Stats',
  player_injury: 'Injuries',
};

export const ModelList: React.FC<ModelListProps> = ({ models, onEdit, onDelete, onToggleStatus, onView }) => {
  return (
    <div className="model-list">
      {models.length === 0 ? (
        <div className="empty-state">
          <p>You haven't created any models yet.</p>
          <p>Create your first model to start generating custom predictions!</p>
        </div>
      ) : (
        <div className="models-grid">
          {models.map(model => (
            <div key={model.model_id} className="model-card">
              <div className="model-header">
                <div>
                  <h3>{model.name}</h3>
                  <span className="sport-tag">{SPORT_LABELS[model.sport] || model.sport}</span>
                </div>
                <span className={`status-badge ${model.status}`}>
                  {model.status === 'active' ? '● Active' : '○ Inactive'}
                </span>
              </div>
              
              <p className="model-description">{model.description || 'No description'}</p>
              
              <div className="model-info">
                <div className="info-item">
                  <span className="info-label">Bet Types:</span>
                  <span className="info-value">
                    {model.bet_types?.map(bt => BET_TYPE_LABELS[bt] || bt).join(', ') || 'N/A'}
                  </span>
                </div>
                <div className="info-item">
                  <span className="info-label">Min Confidence:</span>
                  <span className="info-value">{Math.round((model.min_confidence || 0) * 100)}%</span>
                </div>
              </div>

              <div className="model-composition">
                <span className="composition-label">Data Sources:</span>
                <div className="composition-bars">
                  {model.data_sources && Object.entries(model.data_sources)
                    .filter(([_, config]) => config.enabled)
                    .sort((a, b) => b[1].weight - a[1].weight)
                    .map(([source, config]) => (
                      <div key={source} className="composition-item">
                        <div className="composition-header">
                          <span className="composition-name">{DATA_SOURCE_LABELS[source] || source}</span>
                          <span className="composition-weight">{Math.round(config.weight * 100)}%</span>
                        </div>
                        <div className="composition-bar">
                          <div 
                            className="composition-fill" 
                            style={{ width: `${config.weight * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                </div>
              </div>
              
              <div className="model-meta">
                <span className="created-date">
                  Created {new Date(model.created_at).toLocaleDateString()}
                </span>
              </div>

              <div className="model-actions">
                <button onClick={() => onView(model)} className="btn-view">
                  View
                </button>
                <button onClick={() => onEdit(model.model_id)} className="btn-edit">
                  Edit
                </button>
                <button
                  onClick={() => onToggleStatus(model.model_id, model.status)}
                  className="btn-toggle"
                >
                  {model.status === 'active' ? 'Pause' : 'Activate'}
                </button>
                <button onClick={() => onDelete(model.model_id)} className="btn-delete">
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
