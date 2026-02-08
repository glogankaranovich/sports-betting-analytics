import React, { useState } from 'react';
import './ModelBuilder.css';

interface DataSource {
  enabled: boolean;
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
    custom_data: DataSource;
  };
  minConfidence: number;
  allowBennyAccess: boolean;
}

const DATA_SOURCES = [
  { key: 'team_stats', label: 'Team Stats', description: 'Recent team performance metrics' },
  { key: 'odds_movement', label: 'Odds Movement', description: 'Line movement and sharp action' },
  { key: 'recent_form', label: 'Recent Form', description: 'Win/loss streak and momentum' },
  { key: 'rest_schedule', label: 'Rest & Schedule', description: 'Fatigue and travel factors' },
  { key: 'head_to_head', label: 'Head-to-Head', description: 'Historical matchup performance' },
  { key: 'player_stats', label: 'Player Stats', description: 'Recent player performance (props only)' },
  { key: 'player_injury', label: 'Player Injury', description: 'Player injury status (props only)' },
  { key: 'custom_data', label: 'Custom Data', description: 'Your uploaded custom datasets' },
];

const SPORTS = [
  { value: 'basketball_nba', label: 'Basketball (NBA)' },
  { value: 'americanfootball_nfl', label: 'Football (NFL)' },
  { value: 'baseball_mlb', label: 'Baseball (MLB)' },
  { value: 'icehockey_nhl', label: 'Hockey (NHL)' },
  { value: 'soccer_epl', label: 'Soccer (EPL)' },
];

const BET_TYPES = [
  { value: 'h2h', label: 'Moneyline' },
  { value: 'spreads', label: 'Spread' },
  { value: 'totals', label: 'Totals' },
  { value: 'props', label: 'Player Props' },
];

export const ModelBuilder: React.FC<{ onSave: (config: ModelConfig) => void; onCancel: () => void }> = ({ onSave, onCancel }) => {
  const [config, setConfig] = useState<ModelConfig>({
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
      custom_data: { enabled: false, weight: 0 },
    },
    minConfidence: 60,
    allowBennyAccess: true,
  });

  const totalWeight = Object.values(config.dataSources)
    .filter(ds => ds.enabled)
    .reduce((sum, ds) => sum + ds.weight, 0);

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

  const isValid = config.name.trim() && config.betTypes.length > 0 && totalWeight === 100;

  return (
    <div className="model-builder">
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
            checked={config.allowBennyAccess}
            onChange={(e) => setConfig({ ...config, allowBennyAccess: e.target.checked })}
          />
          <div>
            <strong>Allow Benny to use this model</strong>
            <p className="help-text">
              If enabled, Benny (our AI trader) can learn from and use this model's predictions when making bets. 
              Disable if you want to keep this model private.
            </p>
          </div>
        </label>
      </div>

      <div className="button-group">
        <button onClick={onCancel} className="btn-secondary">Cancel</button>
        <button onClick={() => onSave(config)} disabled={!isValid} className="btn-primary">
          Save Model
        </button>
      </div>
    </div>
  );
};
