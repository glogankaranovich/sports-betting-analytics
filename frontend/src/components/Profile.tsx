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

  useEffect(() => {
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
        } else {
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

    fetchProfile();
  }, [userId, token, user]);

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
