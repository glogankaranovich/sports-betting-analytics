import React, { useState } from 'react';
import './ModelBuilder.css';

interface DataSource {
  enabled: boolean;
  weight: number;
}

interface CustomDatasetSelection {
  dataset_id: string;
  weight: number;
}

interface ModelConfig {
  name: string;
  description: string;
  sport: string;
  betTypes: string[];
  dataSources: {
    team_stats: DataSource;
    odds_movement: DataSource;
    recent_form: DataSource;
    rest_schedule: DataSource;
    head_to_head: DataSource;
    player_stats: DataSource;
    player_injury: DataSource;
  };
  customDatasets: CustomDatasetSelection[];
  minConfidence: number;
  autoAdjustWeights: boolean;
}

const DATA_SOURCES = [
  { key: 'team_stats', label: 'Team Stats', description: 'Recent team performance metrics' },
  { key: 'odds_movement', label: 'Odds Movement', description: 'Line movement and sharp action' },
  { key: 'recent_form', label: 'Recent Form', description: 'Win/loss streak and momentum' },
  { key: 'rest_schedule', label: 'Rest & Schedule', description: 'Fatigue and travel factors' },
  { key: 'head_to_head', label: 'Head-to-Head', description: 'Historical matchup performance' },
  { key: 'player_stats', label: 'Player Stats', description: 'Recent player performance (props only)' },
  { key: 'player_injury', label: 'Player Injury', description: 'Player injury status (props only)' },
];

const SPORTS = [
  { value: 'basketball_nba', label: 'Basketball (NBA)' },
  { value: 'americanfootball_nfl', label: 'Football (NFL)' },
  { value: 'baseball_mlb', label: 'Baseball (MLB)' },
  { value: 'icehockey_nhl', label: 'Hockey (NHL)' },
  { value: 'soccer_epl', label: 'Soccer (EPL)' },
  { value: 'basketball_mens-college-basketball', label: 'NCAA Men\'s Basketball' },
  { value: 'basketball_womens-college-basketball', label: 'NCAA Women\'s Basketball' },
  { value: 'football_college-football', label: 'NCAA Football' },
];

const BET_TYPES = [
  { value: 'h2h', label: 'Moneyline' },
  { value: 'spreads', label: 'Spread' },
  { value: 'totals', label: 'Totals' },
  { value: 'props', label: 'Player Props' },
];

export const ModelBuilder: React.FC<{ 
  onSave: (config: any) => void; 
  onCancel: () => void;
  initialConfig?: any;
}> = ({ onSave, onCancel, initialConfig }) => {
  const [config, setConfig] = useState<ModelConfig>(initialConfig ? {
    name: initialConfig.name || '',
    description: initialConfig.description || '',
    sport: initialConfig.sport || 'basketball_nba',
    betTypes: initialConfig.bet_types || ['h2h'],
    dataSources: initialConfig.data_sources || {
      team_stats: { enabled: true, weight: 25 },
      odds_movement: { enabled: true, weight: 20 },
      recent_form: { enabled: true, weight: 20 },
      rest_schedule: { enabled: true, weight: 15 },
      head_to_head: { enabled: false, weight: 5 },
      player_stats: { enabled: false, weight: 10 },
      player_injury: { enabled: false, weight: 5 },
    },
    customDatasets: initialConfig.custom_datasets || [],
    minConfidence: Math.round((initialConfig.min_confidence || 0.6) * 100),
    autoAdjustWeights: initialConfig.auto_adjust_weights || false,
  } : {
    name: '',
    description: '',
    sport: 'basketball_nba',
    betTypes: ['h2h'],
    dataSources: {
      team_stats: { enabled: true, weight: 25 },
      odds_movement: { enabled: true, weight: 20 },
      recent_form: { enabled: true, weight: 20 },
      rest_schedule: { enabled: true, weight: 15 },
      head_to_head: { enabled: false, weight: 5 },
      player_stats: { enabled: false, weight: 10 },
      player_injury: { enabled: false, weight: 5 },
    },
    customDatasets: [],
    minConfidence: 60,
    autoAdjustWeights: false,
  });

  const [customDatasets, setCustomDatasets] = useState<any[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState(false);

  React.useEffect(() => {
    fetchCustomDatasets();
  }, []);

  const fetchCustomDatasets = async () => {
    setLoadingDatasets(true);
    try {
      const token = localStorage.getItem('token');
      const payload = JSON.parse(atob(token!.split('.')[1]));
      const userId = payload.sub || payload['cognito:username'];
      
      const response = await fetch(`${process.env.REACT_APP_API_URL}/custom-data?user_id=${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await response.json();
      setCustomDatasets(data.datasets || []);
    } catch (error) {
      console.error('Error fetching datasets:', error);
    } finally {
      setLoadingDatasets(false);
    }
  };

  const totalWeight = Object.values(config.dataSources)
    .filter(ds => ds.enabled)
    .reduce((sum, ds) => sum + ds.weight, 0) +
    config.customDatasets.reduce((sum, cd) => sum + cd.weight, 0);

  const handleWeightChange = (key: string, value: number) => {
    setConfig({
      ...config,
      dataSources: {
        ...config.dataSources,
        [key]: { ...config.dataSources[key as keyof typeof config.dataSources], weight: value },
      },
    });
  };

  const handleToggle = (key: string) => {
    setConfig({
      ...config,
      dataSources: {
        ...config.dataSources,
        [key]: { ...config.dataSources[key as keyof typeof config.dataSources], enabled: !config.dataSources[key as keyof typeof config.dataSources].enabled },
      },
    });
  };

  const handleBetTypeToggle = (betType: string) => {
    const newBetTypes = config.betTypes.includes(betType)
      ? config.betTypes.filter(bt => bt !== betType)
      : [...config.betTypes, betType];
    setConfig({ ...config, betTypes: newBetTypes });
  };

  const handleCustomDatasetToggle = (datasetId: string) => {
    const exists = config.customDatasets.find(cd => cd.dataset_id === datasetId);
    if (exists) {
      setConfig({
        ...config,
        customDatasets: config.customDatasets.filter(cd => cd.dataset_id !== datasetId)
      });
    } else {
      setConfig({
        ...config,
        customDatasets: [...config.customDatasets, { dataset_id: datasetId, weight: 10 }]
      });
    }
  };

  const handleCustomDatasetWeightChange = (datasetId: string, weight: number) => {
    setConfig({
      ...config,
      customDatasets: config.customDatasets.map(cd =>
        cd.dataset_id === datasetId ? { ...cd, weight } : cd
      )
    });
  };

  const isValid = config.name.trim() && config.betTypes.length > 0 && totalWeight === 100;

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button onClick={onCancel} className="close-button">×</button>
        <h2>Create Your Model</h2>
        
        <div className="form-group">
          <label>Model Name *</label>
          <input
            type="text"
            value={config.name}
            onChange={(e) => setConfig({ ...config, name: e.target.value })}
            placeholder="e.g., My Momentum Model"
            maxLength={50}
          />
        </div>

      <div className="form-group">
        <label>Description</label>
        <input
          type="text"
          value={config.description}
          onChange={(e) => setConfig({ ...config, description: e.target.value })}
          placeholder="Brief description of your model"
          maxLength={200}
        />
      </div>

      <div className="form-group">
        <label>Sport *</label>
        <select value={config.sport} onChange={(e) => setConfig({ ...config, sport: e.target.value })}>
          {SPORTS.map(sport => (
            <option key={sport.value} value={sport.value}>{sport.label}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Bet Types *</label>
        <div className="checkbox-group">
          {BET_TYPES.map(betType => (
            <label key={betType.value} className="checkbox-label">
              <input
                type="checkbox"
                checked={config.betTypes.includes(betType.value)}
                onChange={() => handleBetTypeToggle(betType.value)}
              />
              {betType.label}
            </label>
          ))}
        </div>
      </div>

      <div className="divider">Data Sources</div>

      {DATA_SOURCES.map(source => {
        const ds = config.dataSources[source.key as keyof typeof config.dataSources];
        return (
          <div key={source.key} className="data-source">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={ds.enabled}
                onChange={() => handleToggle(source.key)}
              />
              <div>
                <strong>{source.label}</strong>
                <p className="source-description">{source.description}</p>
              </div>
            </label>
            {ds.enabled && (
              <div className="weight-control">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={ds.weight}
                  onChange={(e) => handleWeightChange(source.key, parseInt(e.target.value))}
                  className="weight-slider"
                />
                <span className="weight-value">{ds.weight}%</span>
              </div>
            )}
          </div>
        );
      })}

      {customDatasets.length > 0 && (
        <>
          <div className="divider">Custom Datasets</div>
          {customDatasets.map((dataset) => {
            const selected = config.customDatasets.find(cd => cd.dataset_id === dataset.dataset_id);
            return (
              <div key={dataset.dataset_id} className="data-source-item">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={!!selected}
                    onChange={() => handleCustomDatasetToggle(dataset.dataset_id)}
                  />
                  <div>
                    <strong>{dataset.name}</strong>
                    <p className="description">{dataset.description}</p>
                  </div>
                </label>
                {selected && (
                  <div className="weight-control">
                    <input
                      type="range"
                      min="0"
                      max="50"
                      value={selected.weight}
                      onChange={(e) => handleCustomDatasetWeightChange(dataset.dataset_id, parseInt(e.target.value))}
                      className="weight-slider"
                    />
                    <span className="weight-value">{selected.weight}%</span>
                  </div>
                )}
              </div>
            );
          })}
        </>
      )}

      <div className={`total-weight ${totalWeight === 100 ? 'valid' : 'invalid'}`}>
        Total Weight: {totalWeight}% {totalWeight === 100 ? '✓' : '(must equal 100%)'}
      </div>

      <div className="form-group">
        <label>Minimum Confidence Threshold</label>
        <div className="weight-control">
          <input
            type="range"
            min="50"
            max="90"
            value={config.minConfidence}
            onChange={(e) => setConfig({ ...config, minConfidence: parseInt(e.target.value) })}
            className="weight-slider"
          />
          <span className="weight-value">{config.minConfidence}%</span>
        </div>
        <p className="help-text">Only show predictions above this confidence level</p>
      </div>

      <div className="form-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={config.autoAdjustWeights}
            onChange={(e) => setConfig({ ...config, autoAdjustWeights: e.target.checked })}
          />
          <span>Auto-Adjust Weights Based on Performance</span>
        </label>
        <p className="help-text">
          Automatically optimize data source weights based on which sources are most accurate for your model.
          Adjustments run weekly and you can disable this at any time.
        </p>
      </div>

      <div className="button-group">
        <button onClick={onCancel} className="btn-secondary">Cancel</button>
        <button onClick={() => {
          // Convert camelCase to snake_case for API
          const apiConfig = {
            name: config.name,
            description: config.description,
            sport: config.sport,
            bet_types: config.betTypes,
            data_sources: Object.entries(config.dataSources)
              .filter(([_, ds]) => ds.enabled)
              .reduce((acc, [key, ds]) => ({
                ...acc,
                [key]: { weight: ds.weight / 100, enabled: true }
              }), {}),
            custom_datasets: config.customDatasets.map(cd => ({
              dataset_id: cd.dataset_id,
              weight: cd.weight / 100
            })),
            min_confidence: config.minConfidence / 100,
            auto_adjust_weights: config.autoAdjustWeights,
          };
          onSave(apiConfig);
        }} disabled={!isValid} className="btn-primary">
          Save Model
        </button>
      </div>
      </div>
    </div>
  );
};
