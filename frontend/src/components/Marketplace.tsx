import React, { useState, useEffect } from 'react';
import { bettingApi } from '../services/api';

interface MarketplaceProps {
  subscription: any;
  onNavigate: (page: string) => void;
}

export const Marketplace: React.FC<MarketplaceProps> = ({ subscription, onNavigate }) => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Wait for subscription to load
    if (subscription) {
      setLoading(false);
    }
  }, [subscription]);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  // Step 1: Check if feature is enabled (from subscription limits which includes feature flags)
  const featureEnabled = subscription?.limits?.model_marketplace === true;
  
  if (!featureEnabled) {
    return (
      <div className="page-container">
        <h2>Model Marketplace</h2>
        <p>Coming soon - Browse and subscribe to community models</p>
      </div>
    );
  }

  // Step 2: Check if user has access via subscription tier
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
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <h3 style={{ marginBottom: '16px' }}>🏪 Model Marketplace</h3>
          <p style={{ color: '#ccc', marginBottom: '24px' }}>
            Access community-built models and share your own strategies.
          </p>
          <ul style={{ textAlign: 'left', color: '#ccc', marginBottom: '24px', listStyle: 'none', padding: 0, maxWidth: '400px', margin: '0 auto 24px' }}>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Browse proven models</li>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Subscribe to top performers</li>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Share your models</li>
            <li style={{ padding: '8px 0' }}>✓ Earn from your strategies</li>
          </ul>
          <button 
            className="upgrade-btn" 
            onClick={() => onNavigate('subscription')}
            style={{ width: '100%', maxWidth: '400px', margin: '0 auto' }}
          >
            Upgrade to Access Marketplace
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
