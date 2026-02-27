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
  subscription?: any;
}

const Settings: React.FC<SettingsProps> = ({
  settings,
  onSettingsChange,
  availableSports,
  availableBookmakers,
  userModels,
  subscription
}) => {
  const hasBennyAccess = subscription?.limits?.benny_ai !== false;
  const isFree = subscription?.limits?.show_reasoning === false;
  
  const handleChange = (key: string, value: string) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  const modelDescriptions: Record<string, string> = {
    consensus: 'Average across all bookmakers - balanced approach',
    ensemble: 'Intelligent combination of all models using dynamic weighting',
    value: 'Finds odds discrepancies and value opportunities',
    momentum: 'Tracks line movement and sharp action',
    contrarian: 'Fades the public, follows sharp money',
    hot_cold: 'Recent form and performance trends',
    rest_schedule: 'Rest days, back-to-backs, and home/away splits',
    matchup: 'Head-to-head history and style matchups',
    injury_aware: 'Adjusts predictions based on player injuries',
    news: 'Analyzes recent news sentiment and impact',
    player_stats: 'Player performance history and matchups (props only)'
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
              {!isFree && <option value="consensus">Consensus</option>}
              <option value="ensemble">Ensemble</option>
              {!isFree && <option value="value">Value</option>}
              {!isFree && <option value="momentum">Momentum</option>}
              {!isFree && <option value="contrarian">Contrarian</option>}
              {!isFree && <option value="hot_cold">Hot/Cold</option>}
              {!isFree && <option value="rest_schedule">Rest/Schedule</option>}
              {!isFree && <option value="matchup">Matchup</option>}
              {!isFree && <option value="injury_aware">Injury-Aware</option>}
              {!isFree && <option value="news">News Sentiment</option>}
              {!isFree && <option value="fundamentals">Fundamentals</option>}
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
        </div>
      </div>
    </div>
  );
};

export default Settings;
