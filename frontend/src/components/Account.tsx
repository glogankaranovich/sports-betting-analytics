import React, { useState, useEffect } from 'react';
import './Account.css';

interface AccountProps {
  token: string;
  userId: string;
  user: any;
  settings: { sport: string; bookmaker: string; model: string };
  onSettingsChange: (settings: any) => void;
}

const Account: React.FC<AccountProps> = ({ token, userId, user, settings, onSettingsChange }) => {
  const [activeTab, setActiveTab] = useState<'profile' | 'subscription' | 'preferences'>('profile');
  const [profile, setProfile] = useState<any>(null);
  const [subscription, setSubscription] = useState<any>(null);
  const [localSettings, setLocalSettings] = useState(settings);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchData();
  }, [userId, token]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [profileRes, subRes] = await Promise.all([
        fetch(`${process.env.REACT_APP_API_URL}/profile?user_id=${userId}`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch(`${process.env.REACT_APP_API_URL}/subscription?user_id=${userId}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      if (profileRes.ok) {
        setProfile(await profileRes.json());
      } else {
        setProfile({
          user_id: userId,
          email: user?.signInDetails?.loginId || user?.username || 'N/A',
          created_at: new Date().toISOString(),
        });
      }

      if (subRes.ok) {
        setSubscription(await subRes.json());
      }
    } catch (err) {
      console.error('Error fetching account data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = () => {
    onSettingsChange(localSettings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleResetSettings = () => {
    const defaults = { sport: 'basketball_nba', bookmaker: 'fanduel', model: 'consensus' };
    setLocalSettings(defaults);
    onSettingsChange(defaults);
  };

  const TIER_INFO: Record<string, any> = {
    free: { name: 'Free', price: '$0', color: '#6c757d' },
    basic: { name: 'Basic', price: '$9.99/mo', color: '#0d6efd' },
    pro: { name: 'Pro', price: '$29.99/mo', color: '#198754' },
    enterprise: { name: 'Enterprise', price: 'Custom', color: '#6f42c1' }
  };

  if (loading) return <div className="page-container"><p>Loading account...</p></div>;

  return (
    <div className="page-container">
      <div className="account-header">
        <h2>Account</h2>
        <p>Manage your profile, subscription, and preferences</p>
      </div>

      <div className="account-tabs">
        <button
          className={activeTab === 'profile' ? 'active' : ''}
          onClick={() => setActiveTab('profile')}
        >
          Profile
        </button>
        <button
          className={activeTab === 'subscription' ? 'active' : ''}
          onClick={() => setActiveTab('subscription')}
        >
          Subscription
        </button>
        <button
          className={activeTab === 'preferences' ? 'active' : ''}
          onClick={() => setActiveTab('preferences')}
        >
          Preferences
        </button>
      </div>

      {activeTab === 'profile' && profile && (
        <div className="account-section">
          <div className="account-card">
            <h3>Profile Information</h3>
            <div className="account-field">
              <label>User ID</label>
              <span>{profile.user_id}</span>
            </div>
            <div className="account-field">
              <label>Email</label>
              <span>{profile.email}</span>
            </div>
            <div className="account-field">
              <label>Member Since</label>
              <span>{new Date(profile.created_at).toLocaleDateString()}</span>
            </div>
            {profile.last_login && (
              <div className="account-field">
                <label>Last Login</label>
                <span>{new Date(profile.last_login).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'subscription' && subscription && (
        <div className="account-section">
          <div className="account-card">
            <div className="tier-badge" style={{ backgroundColor: TIER_INFO[subscription.tier]?.color }}>
              {TIER_INFO[subscription.tier]?.name || subscription.tier}
            </div>
            <h3>Current Plan</h3>
            <p className="tier-price">{TIER_INFO[subscription.tier]?.price}</p>
            
            <div className="usage-stats">
              <div className="usage-item">
                <label>API Calls Today</label>
                <div className="usage-bar">
                  <div 
                    className="usage-fill" 
                    style={{ width: `${(subscription.usage.api_calls_today / subscription.limits.api_calls_per_day) * 100}%` }}
                  />
                </div>
                <span>{subscription.usage.api_calls_today} / {subscription.limits.api_calls_per_day}</span>
              </div>
              <div className="usage-item">
                <label>User Models</label>
                <span>{subscription.usage.user_models_count} / {subscription.limits.max_user_models}</span>
              </div>
              <div className="usage-item">
                <label>Custom Datasets</label>
                <span>{subscription.usage.datasets_count} / {subscription.limits.max_custom_datasets}</span>
              </div>
            </div>

            <div className="features-list">
              <h4>Plan Features</h4>
              <div className="feature-item">
                <span className={subscription.limits.system_models ? 'enabled' : 'disabled'}>
                  {subscription.limits.system_models ? '✓' : '✗'}
                </span>
                System Models
              </div>
              <div className="feature-item">
                <span className={subscription.limits.benny_ai ? 'enabled' : 'disabled'}>
                  {subscription.limits.benny_ai ? '✓' : '✗'}
                </span>
                Benny AI
              </div>
              <div className="feature-item">
                <span className={subscription.limits.user_models ? 'enabled' : 'disabled'}>
                  {subscription.limits.user_models ? '✓' : '✗'}
                </span>
                Custom Models
              </div>
              <div className="feature-item">
                <span className={subscription.limits.custom_data ? 'enabled' : 'disabled'}>
                  {subscription.limits.custom_data ? '✓' : '✗'}
                </span>
                Custom Data
              </div>
            </div>

            {subscription.tier === 'free' && (
              <button className="upgrade-btn">Upgrade Plan</button>
            )}
          </div>
        </div>
      )}

      {activeTab === 'preferences' && (
        <div className="account-section">
          <div className="account-card">
            <h3>Default Preferences</h3>
            <p className="section-desc">These settings apply when you first load the app</p>
            
            <div className="account-field">
              <label>Default Sport</label>
              <select
                value={localSettings.sport}
                onChange={(e) => setLocalSettings({ ...localSettings, sport: e.target.value })}
              >
                <option value="basketball_nba">NBA Basketball</option>
                <option value="americanfootball_nfl">NFL Football</option>
                <option value="icehockey_nhl">NHL Hockey</option>
                <option value="baseball_mlb">MLB Baseball</option>
                <option value="soccer_epl">EPL Soccer</option>
              </select>
            </div>

            <div className="account-field">
              <label>Default Bookmaker</label>
              <select
                value={localSettings.bookmaker}
                onChange={(e) => setLocalSettings({ ...localSettings, bookmaker: e.target.value })}
              >
                <option value="fanduel">FanDuel</option>
                <option value="draftkings">DraftKings</option>
                <option value="betmgm">BetMGM</option>
                <option value="caesars">Caesars</option>
                <option value="pointsbet">PointsBet</option>
                <option value="betrivers">BetRivers</option>
              </select>
            </div>

            <div className="account-field">
              <label>Default Model</label>
              <select
                value={localSettings.model}
                onChange={(e) => setLocalSettings({ ...localSettings, model: e.target.value })}
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
              </select>
            </div>

            <div className="account-actions">
              <button className="save-btn" onClick={handleSaveSettings}>
                {saved ? 'Saved!' : 'Save Changes'}
              </button>
              <button className="reset-btn" onClick={handleResetSettings}>
                Reset to Defaults
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Account;
