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
      <div className="marketplace-container">
        <h2>Model Marketplace</h2>
        <p>Coming soon - Browse and subscribe to community models</p>
      </div>
    );
  }

  const hasAccess = subscription?.tier === 'premium' || subscription?.tier === 'pro';

  if (!hasAccess) {
    return (
      <div className="marketplace-container">
        <h2>Model Marketplace</h2>
        <p>Upgrade to Premium or Pro to access the Model Marketplace</p>
        <button onClick={() => onNavigate('subscription')} className="cta-button">
          View Subscription Plans
        </button>
      </div>
    );
  }

  return (
    <div className="marketplace-container">
      <h2>Model Marketplace</h2>
      <p>Coming soon - Browse and subscribe to community models</p>
    </div>
  );
};
