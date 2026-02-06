import React from 'react';

interface SettingsProps {
  settings: {
    sport: string;
    bookmaker: string;
    model: string;
  };
  onSettingsChange: (settings: any) => void;
  availableSports: string[];
  availableBookmakers: string[];
  userModels: any[];
  token: string;
}

const Settings: React.FC<SettingsProps> = ({
  settings,
  onSettingsChange,
  availableSports,
  availableBookmakers,
  userModels
}) => {
  const handleChange = (key: string, value: string) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  const modelDescriptions: Record<string, string> = {
    consensus: 'Average across all bookmakers - balanced approach',
    value: 'Finds odds discrepancies and value opportunities',
    momentum: 'Tracks line movement and sharp action',
    contrarian: 'Fades the public, follows sharp money',
    hot_cold: 'Recent form and performance trends',
    rest_schedule: 'Rest days, back-to-backs, and home/away splits',
    matchup: 'Head-to-head history and style matchups',
    injury_aware: 'Adjusts predictions based on player injuries'
  };

  const sportDisplayNames: Record<string, string> = {
    'basketball_nba': 'NBA',
    'americanfootball_nfl': 'NFL',
    'baseball_mlb': 'MLB',
    'icehockey_nhl': 'NHL',
    'soccer_epl': 'EPL'
  };

  return (
    <div className="predictions-section">
      <div className="settings-grid">
        <div className="setting-item">
          <label>Preferred Sport:</label>
          <select 
            value={settings.sport} 
            onChange={(e) => handleChange('sport', e.target.value)}
          >
            {availableSports.map(sport => (
              <option key={sport} value={sport}>
                {sportDisplayNames[sport] || sport.replace('_', ' ').toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div className="setting-item">
          <label>Preferred Bookmaker:</label>
          <select 
            value={settings.bookmaker} 
            onChange={(e) => handleChange('bookmaker', e.target.value)}
          >
            {availableBookmakers.map(bookmaker => (
              <option key={bookmaker} value={bookmaker}>{bookmaker}</option>
            ))}
          </select>
        </div>

        <div className="setting-item">
          <label>Model:</label>
          <select 
            value={settings.model} 
            onChange={(e) => handleChange('model', e.target.value)}
          >
            <optgroup label="System Models">
              <option value="consensus">Consensus</option>
              <option value="value">Value</option>
              <option value="momentum">Momentum</option>
              <option value="contrarian">Contrarian</option>
              <option value="hot_cold">Hot/Cold</option>
              <option value="rest_schedule">Rest/Schedule</option>
              <option value="matchup">Matchup</option>
              <option value="injury_aware">Injury-Aware</option>
            </optgroup>
            {userModels.length > 0 && (
              <optgroup label="My Models">
                {userModels.map(model => (
                  <option key={model.model_id} value={`user:${model.model_id}`}>
                    {model.name}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
          <div className="model-description">
            {settings.model.startsWith('user:') 
              ? userModels.find(m => `user:${m.model_id}` === settings.model)?.description || 'Custom model'
              : modelDescriptions[settings.model]
            }
          </div>
        </div>
      </div>

      <style>{`
        .model-description {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 4px;
          font-style: italic;
        }
      `}</style>
    </div>
  );
};

export default Settings;
