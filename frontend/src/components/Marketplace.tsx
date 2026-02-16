import React, { useState, useEffect } from 'react';
import { bettingApi } from '../services/api';

interface MarketplaceProps {
  subscription: any;
  onNavigate: (page: string) => void;
}

export const Marketplace: React.FC<MarketplaceProps> = ({ subscription, onNavigate }) => {
  const [featureEnabled, setFeatureEnabled] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkFeatureAccess();
  }, []);

  const checkFeatureAccess = async () => {
    try {
      // Attempt to access marketplace - backend will check feature access
      setFeatureEnabled(true);
      setLoading(false);
    } catch (error: any) {
      console.error('Error checking marketplace access:', error);
      if (error.response?.status === 403) {
        setFeatureEnabled(false);
      }
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!featureEnabled) {
    return (
      <div className="page-container">
        <h2>Model Marketplace</h2>
        <p>Coming soon - Browse and subscribe to community models</p>
      </div>
    );
  }

  const hasAccess = subscription?.tier === 'premium' || subscription?.tier === 'pro';

  if (!hasAccess) {
    return (
      <div className="page-container">
        <div style={{ 
          padding: '40px', 
          textAlign: 'center',
          background: '#1a1a1a',
          borderRadius: '8px',
          border: '1px solid #333',
          maxWidth: '600px',
          margin: '40px auto'
        }}>
          <h3 style={{ marginBottom: '16px' }}>🏪 Model Marketplace</h3>
          <p style={{ color: '#ccc', marginBottom: '24px' }}>
            Access community-built models and share your own strategies.
          </p>
          <ul style={{ textAlign: 'left', color: '#ccc', marginBottom: '24px', listStyle: 'none', padding: 0 }}>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Browse proven models</li>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Subscribe to top performers</li>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Share your models</li>
            <li style={{ padding: '8px 0' }}>✓ Earn from your strategies</li>
          </ul>
          <button 
            className="upgrade-btn" 
            onClick={() => onNavigate('subscription')}
            style={{ width: '100%' }}
          >
            Upgrade to Premium or Pro
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h2>Model Marketplace</h2>
      <p>Coming soon - Browse and subscribe to community models</p>
    </div>
  );
};
