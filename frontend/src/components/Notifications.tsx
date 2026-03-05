import React, { useState, useEffect } from 'react';
import './Notifications.css';

interface NotificationsProps {
  token: string;
  userId: string;
  subscription?: any;
}

const Notifications: React.FC<NotificationsProps> = ({ token, userId, subscription }) => {
  const [notifications, setNotifications] = useState({
    bennyWeeklyReport: false,
    bennyBetAlerts: false,
  });
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchPreferences();
  }, [userId, token]);

  const fetchPreferences = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/profile?user_id=${userId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (response.ok) {
        const data = await response.json();
        if (data.preferences?.notifications) {
          setNotifications(data.preferences.notifications);
        }
      }
    } catch (error) {
      console.error('Error fetching preferences:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await fetch(`${process.env.REACT_APP_API_URL}/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: userId,
          preferences: { notifications },
        }),
      });
      
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      console.error('Error saving notification preferences:', error);
    }
  };

  const hasBennyAccess = subscription?.limits?.benny_ai !== false;

  if (loading) return <div className="page-container"><p>Loading...</p></div>;

  return (
    <div className="page-container">
      <h2>Notifications</h2>
      <p>Manage your email notification preferences</p>

      <div className="notifications-card">
        <div className="notification-item">
          <div className="notification-info">
            <label>Benny Weekly Report</label>
            <p>Receive a weekly summary of Benny's betting performance every Monday</p>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={notifications.bennyWeeklyReport}
              onChange={(e) => setNotifications({ ...notifications, bennyWeeklyReport: e.target.checked })}
              disabled={!hasBennyAccess}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        <div className="notification-item">
          <div className="notification-info">
            <label>Benny Bet Alerts</label>
            <p>Get notified when Benny places a new bet</p>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={notifications.bennyBetAlerts}
              onChange={(e) => setNotifications({ ...notifications, bennyBetAlerts: e.target.checked })}
              disabled={!hasBennyAccess}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        {!hasBennyAccess && (
          <p className="upgrade-notice">
            Email notifications require a Pro subscription. <a href="#" onClick={() => window.location.href = '/subscription'}>Upgrade now</a>
          </p>
        )}

        <div className="notification-actions">
          <button className="save-btn" onClick={handleSave}>
            {saved ? 'Saved!' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Notifications;
