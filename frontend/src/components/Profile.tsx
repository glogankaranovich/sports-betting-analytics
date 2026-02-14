import React, { useState, useEffect } from 'react';
import './Profile.css';

interface ProfileProps {
  token: string;
  userId: string;
  user: any;
}

interface ProfileData {
  user_id: string;
  email: string;
  created_at: string;
  last_login?: string;
  preferences?: {
    default_sport?: string;
    default_bookmaker?: string;
    email_notifications?: boolean;
  };
}

export const Profile: React.FC<ProfileProps> = ({ token, userId, user }) => {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [preferences, setPreferences] = useState({
    default_sport: 'basketball_nba',
    default_bookmaker: 'fanduel',
    email_notifications: true,
  });

  useEffect(() => {
    fetchProfile();
  }, [userId, token]);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/profile?user_id=${userId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.ok) {
        const data = await response.json();
        setProfile(data);
        if (data.preferences) {
          setPreferences(data.preferences);
        }
      } else {
        // Profile doesn't exist yet, create default
        setProfile({
          user_id: userId,
          email: user?.signInDetails?.loginId || user?.username || 'N/A',
          created_at: new Date().toISOString(),
        });
      }
    } catch (err) {
      console.error('Error fetching profile:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/profile`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            user_id: userId,
            preferences,
          }),
        }
      );

      if (response.ok) {
        setEditing(false);
        fetchProfile();
      }
    } catch (err) {
      console.error('Error saving profile:', err);
    }
  };

  if (loading) return <div className="profile-loading">Loading profile...</div>;
  if (!profile) return null;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="profile-container">
      <div className="profile-header">
        <h1>Profile</h1>
        <p>Manage your account information and preferences</p>
      </div>

      <div className="profile-section">
        <h3>Account Information</h3>
        <div className="info-grid">
          <div className="info-item">
            <label>User ID</label>
            <div className="info-value">{profile.user_id}</div>
          </div>
          <div className="info-item">
            <label>Email</label>
            <div className="info-value">{profile.email}</div>
          </div>
          <div className="info-item">
            <label>Member Since</label>
            <div className="info-value">{formatDate(profile.created_at)}</div>
          </div>
          {profile.last_login && (
            <div className="info-item">
              <label>Last Login</label>
              <div className="info-value">{formatDate(profile.last_login)}</div>
            </div>
          )}
        </div>
      </div>

      <div className="profile-section">
        <div className="section-header">
          <h3>Preferences</h3>
          {!editing ? (
            <button className="edit-btn" onClick={() => setEditing(true)}>
              Edit
            </button>
          ) : (
            <div className="edit-actions">
              <button className="cancel-btn" onClick={() => setEditing(false)}>
                Cancel
              </button>
              <button className="save-btn" onClick={handleSave}>
                Save
              </button>
            </div>
          )}
        </div>

        <div className="preferences-grid">
          <div className="pref-item">
            <label>Default Sport</label>
            {editing ? (
              <select
                value={preferences.default_sport}
                onChange={(e) =>
                  setPreferences({ ...preferences, default_sport: e.target.value })
                }
              >
                <option value="basketball_nba">NBA Basketball</option>
                <option value="americanfootball_nfl">NFL Football</option>
                <option value="icehockey_nhl">NHL Hockey</option>
                <option value="baseball_mlb">MLB Baseball</option>
                <option value="soccer_epl">EPL Soccer</option>
              </select>
            ) : (
              <div className="pref-value">
                {preferences.default_sport === 'basketball_nba' && 'NBA Basketball'}
                {preferences.default_sport === 'americanfootball_nfl' && 'NFL Football'}
                {preferences.default_sport === 'icehockey_nhl' && 'NHL Hockey'}
                {preferences.default_sport === 'baseball_mlb' && 'MLB Baseball'}
                {preferences.default_sport === 'soccer_epl' && 'EPL Soccer'}
              </div>
            )}
          </div>

          <div className="pref-item">
            <label>Default Bookmaker</label>
            {editing ? (
              <select
                value={preferences.default_bookmaker}
                onChange={(e) =>
                  setPreferences({ ...preferences, default_bookmaker: e.target.value })
                }
              >
                <option value="fanduel">FanDuel</option>
                <option value="draftkings">DraftKings</option>
                <option value="betmgm">BetMGM</option>
                <option value="caesars">Caesars</option>
              </select>
            ) : (
              <div className="pref-value">
                {preferences.default_bookmaker === 'fanduel' && 'FanDuel'}
                {preferences.default_bookmaker === 'draftkings' && 'DraftKings'}
                {preferences.default_bookmaker === 'betmgm' && 'BetMGM'}
                {preferences.default_bookmaker === 'caesars' && 'Caesars'}
              </div>
            )}
          </div>

          <div className="pref-item">
            <label>Email Notifications</label>
            {editing ? (
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={preferences.email_notifications}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      email_notifications: e.target.checked,
                    })
                  }
                />
                <span className="toggle-slider"></span>
              </label>
            ) : (
              <div className="pref-value">
                {preferences.email_notifications ? 'Enabled' : 'Disabled'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
