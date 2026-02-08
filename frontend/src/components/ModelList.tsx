import React from 'react';
import './ModelList.css';

interface UserModel {
  model_id: string;
  name: string;
  description: string;
  sport: string;
  status: string;
  created_at: string;
}

interface ModelListProps {
  models: UserModel[];
  onCreateNew: () => void;
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
};

export const ModelList: React.FC<ModelListProps> = ({ models, onCreateNew, onEdit, onDelete, onToggleStatus, onView }) => {
  return (
    <div className="model-list">
      <div className="list-header">
        <h2>My Models</h2>
        <button onClick={onCreateNew} className="btn-primary">
          + Create Model
        </button>
      </div>

      {models.length === 0 ? (
        <div className="empty-state">
          <p>You haven't created any models yet.</p>
          <p>Create your first model to start generating custom predictions!</p>
          <button onClick={onCreateNew} className="btn-primary">
            Create Your First Model
          </button>
        </div>
      ) : (
        <div className="models-grid">
          {models.map(model => (
            <div key={model.model_id} className="model-card">
              <div className="model-header">
                <h3>{model.name}</h3>
                <span className={`status-badge ${model.status}`}>
                  {model.status === 'active' ? '● Active' : '○ Inactive'}
                </span>
              </div>
              
              <p className="model-description">{model.description || 'No description'}</p>
              
              <div className="model-meta">
                <span className="sport-tag">{SPORT_LABELS[model.sport] || model.sport}</span>
                <span className="created-date">
                  Created {new Date(model.created_at).toLocaleDateString()}
                </span>
              </div>

              <div className="model-actions">
                <button onClick={() => onView(model)} className="btn-view">
                  View
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

      {models.length > 0 && models.length < 5 && (
        <div className="add-more">
          <p>You can create up to 5 personal models</p>
        </div>
      )}
    </div>
  );
};
