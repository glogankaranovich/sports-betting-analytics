import React from 'react';

interface SettingsProps {
  settings: {
    sport: string;
    bookmaker: string;
    model: string;
    riskTolerance: string;
  };
  onSettingsChange: (settings: any) => void;
  availableSports: string[];
  availableBookmakers: string[];
}

const Settings: React.FC<SettingsProps> = ({
  settings,
  onSettingsChange,
  availableSports,
  availableBookmakers
}) => {
  const handleChange = (key: string, value: string) => {
    onSettingsChange({ ...settings, [key]: value });
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
            <option value="all">All Sports</option>
            {availableSports.map(sport => (
              <option key={sport} value={sport}>{sport.replace('_', ' ').toUpperCase()}</option>
            ))}
          </select>
        </div>

        <div className="setting-item">
          <label>Preferred Bookmaker:</label>
          <select 
            value={settings.bookmaker} 
            onChange={(e) => handleChange('bookmaker', e.target.value)}
          >
            <option value="all">All Bookmakers</option>
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
            <option value="consensus">Consensus</option>
            <option value="value">Value-Based</option>
            <option value="momentum">Momentum</option>
          </select>
        </div>

        <div className="setting-item">
          <label>Risk Tolerance:</label>
          <select 
            value={settings.riskTolerance} 
            onChange={(e) => handleChange('riskTolerance', e.target.value)}
          >
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
        </div>
      </div>
    </div>
  );
};

export default Settings;
