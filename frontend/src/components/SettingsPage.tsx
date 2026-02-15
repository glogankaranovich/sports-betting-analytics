import React, { useState } from 'react';
import './SettingsPage.css';

interface SettingsPageProps {
  settings: {
    sport: string;
    bookmaker: string;
    model: string;
  };
  onSettingsChange: (settings: any) => void;
  subscription?: any;
}

const SettingsPage: React.FC<SettingsPageProps> = ({ settings, onSettingsChange, subscription }) => {
  const hasBennyAccess = subscription?.limits?.benny_ai !== false;
  const [localSettings, setLocalSettings] = useState(settings);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    onSettingsChange(localSettings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    const defaults = {
      sport: 'basketball_nba',
      bookmaker: 'fanduel',
      model: 'consensus',
    };
    setLocalSettings(defaults);
    onSettingsChange(defaults);
  };

  return (
    <div className="page-container settings-page-container">
      <h2>Preferences</h2>

      <div className="settings-page-section">
        <div className="settings-page-grid">
          <div className="setting-page-item">
            <label>Default Sport</label>
            <select
              value={localSettings.sport}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, sport: e.target.value })
              }
            >
              <option value="basketball_nba">NBA Basketball</option>
              <option value="americanfootball_nfl">NFL Football</option>
              <option value="icehockey_nhl">NHL Hockey</option>
              <option value="baseball_mlb">MLB Baseball</option>
              <option value="soccer_epl">EPL Soccer</option>
            </select>
            <span className="setting-page-hint">
              The sport shown when you open the app
            </span>
          </div>

          <div className="setting-page-item">
            <label>Default Bookmaker</label>
            <select
              value={localSettings.bookmaker}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, bookmaker: e.target.value })
              }
            >
              <option value="fanduel">FanDuel</option>
              <option value="draftkings">DraftKings</option>
              <option value="betmgm">BetMGM</option>
              <option value="caesars">Caesars</option>
              <option value="pointsbet">PointsBet</option>
              <option value="betrivers">BetRivers</option>
            </select>
            <span className="setting-page-hint">
              Your preferred sportsbook for odds
            </span>
          </div>

          <div className="setting-page-item">
            <label>Default Model</label>
            <select
              value={localSettings.model}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, model: e.target.value })
              }
            >
              <option value="consensus">Consensus</option>
              <option value="ensemble">Ensemble</option>
              <option value="value">Value</option>
              <option value="momentum">Momentum</option>
              <option value="contrarian">Contrarian</option>
              <option value="hot_cold">Hot/Cold</option>
              <option value="rest_schedule">Rest/Schedule</option>
              <option value="matchup">Matchup</option>
              <option value="injury_aware">Injury-Aware</option>
              <option value="news">News Sentiment</option>
              {hasBennyAccess && <option value="benny">Benny AI</option>}
            </select>
            <span className="setting-page-hint">
              The prediction model to use by default
            </span>
          </div>
        </div>
      </div>

      <div className="settings-page-actions">
        <button className="reset-page-btn" onClick={handleReset}>
          Reset to Defaults
        </button>
        <button className="save-page-btn" onClick={handleSave}>
          {saved ? '✓ Saved!' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
};

export default SettingsPage;
