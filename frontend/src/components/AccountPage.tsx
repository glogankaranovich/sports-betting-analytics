import React, { useState, useEffect } from 'react';
import './AccountPage.css';

interface AccountPageProps {
  token: string;
  userId: string;
  user: any;
  subscription?: any;
  settings: any;
  onUpdateSettings: (settings: any) => void;
  onNavigate?: (page: string) => void;
  initialTab?: 'profile' | 'subscription' | 'preferences';
}

export const AccountPage: React.FC<AccountPageProps> = ({ 
  token, 
  userId, 
  user, 
  subscription,
  settings,
  onUpdateSettings,
  onNavigate,
  initialTab = 'profile'
}) => {
  const [localSettings, setLocalSettings] = useState(settings);
  const [saved, setSaved] = useState(false);

  const email = user?.signInDetails?.loginId || user?.username || 'N/A';
  const tier = subscription?.tier || 'free';

  const handleSave = () => {
    onUpdateSettings(localSettings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    setLocalSettings({
      sport: 'americanfootball_nfl',
      bookmaker: 'fanduel',
      model: 'ensemble'
    });
  };

  const formatTier = (tier: string) => {
    return tier.charAt(0).toUpperCase() + tier.slice(1);
  };

  return (
    <div className="account-page">
      <div className="account-header">
        <h1>Account Settings</h1>
        <p className="account-subtitle">Manage your profile, subscription, and preferences</p>
      </div>

      <div className="account-content">
        <div className="account-section">
          <h2>Profile</h2>
          <div className="account-field">
            <label>Email</label>
            <div className="field-value">{email}</div>
          </div>
          <div className="account-field">
            <label>User ID</label>
            <div className="field-value">{userId}</div>
          </div>
        </div>

        <div className="account-section">
          <h2>Subscription</h2>
          <div className="subscription-info">
            <div className="subscription-tier">
              <span className="tier-badge">{formatTier(tier)}</span>
            </div>
            <div className="subscription-features">
              <h3>Your Features</h3>
              <ul>
                {tier === 'free' && (
                  <>
                    <li>Ensemble Model Only</li>
                    <li>Basic Predictions</li>
                  </>
                )}
                {tier === 'basic' && (
                  <>
                    <li>All 10 System Models</li>
                    <li>Detailed Reasoning & Analysis</li>
                    <li>Custom Models (3)</li>
                    <li>Custom Data (5)</li>
                  </>
                )}
                {tier === 'pro' && (
                  <>
                    <li>All 10 System Models</li>
                    <li>Benny AI Assistant</li>
                    <li>Custom Models (20)</li>
                    <li>Custom Data (50)</li>
                    <li>Model Marketplace</li>
                  </>
                )}
              </ul>
            </div>
            {tier !== 'pro' && (
              <button 
                className="upgrade-button"
                onClick={() => onNavigate?.('subscription')}
              >
                Upgrade Plan
              </button>
            )}
          </div>
        </div>

        <div className="account-section">
          <h2>Preferences</h2>
          
          <div className="account-field">
            <label>Sport</label>
            <select 
              value={localSettings.sport}
              onChange={(e) => setLocalSettings({ ...localSettings, sport: e.target.value })}
            >
              <option value="americanfootball_nfl">NFL</option>
              <option value="basketball_nba">NBA</option>
              <option value="icehockey_nhl">NHL</option>
              <option value="baseball_mlb">MLB</option>
            </select>
          </div>

          <div className="account-field">
            <label>Bookmaker</label>
            <select 
              value={localSettings.bookmaker}
              onChange={(e) => setLocalSettings({ ...localSettings, bookmaker: e.target.value })}
            >
              <option value="fanduel">FanDuel</option>
              <option value="draftkings">DraftKings</option>
              <option value="betmgm">BetMGM</option>
              <option value="caesars">Caesars</option>
            </select>
          </div>

          <div className="account-field">
            <label>Default Model</label>
            <select 
              value={localSettings.model}
              onChange={(e) => setLocalSettings({ ...localSettings, model: e.target.value })}
            >
              <option value="ensemble">Ensemble</option>
              {subscription?.limits?.show_reasoning !== false && (
                <>
                  <option value="consensus">Consensus</option>
                  <option value="value">Value</option>
                  <option value="momentum">Momentum</option>
                  <option value="contrarian">Contrarian</option>
                  <option value="hot_cold">Hot/Cold</option>
                  <option value="rest_schedule">Rest/Schedule</option>
                  <option value="matchup">Matchup</option>
                  <option value="injury_aware">Injury-Aware</option>
                  <option value="news">News Sentiment</option>
                </>
              )}
              {subscription?.limits?.benny_ai && <option value="benny">Benny AI</option>}
            </select>
          </div>

          <div className="account-actions">
            <button className="save-button" onClick={handleSave}>
              {saved ? '✓ Saved' : 'Save Changes'}
            </button>
            <button className="reset-button" onClick={handleReset}>
              Reset to Defaults
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
