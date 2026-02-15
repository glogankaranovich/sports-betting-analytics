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

  if (loading) return <div className="page-container"><p>Loading profile...</p></div>;
  if (!profile) return null;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="page-container profile-container">
      <h2>Profile</h2>
      <p>Your account information</p>

      <div className="profile-section">
        <h3>Account Information</h3>
        <div className="info-grid">
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
    </div>
  );
};
