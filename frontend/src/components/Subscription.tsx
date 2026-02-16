import React, { useState, useEffect } from 'react';
import './Subscription.css';
import { SubscriptionModal } from './SubscriptionModal';

interface SubscriptionProps {
  token: string;
  userId: string;
}

interface TierLimits {
  system_models: boolean | string[];
  show_reasoning: boolean;
  benny_ai: boolean;
  user_models: boolean;
  custom_data: boolean;
  model_marketplace: boolean;
  max_user_models: number;
  max_custom_datasets: number;
}

interface SubscriptionData {
  tier: string;
  status: string;
  limits: TierLimits;
  usage: {
    user_models_count: number;
    datasets_count: number;
  };
}

const TIER_INFO = {
  free: { name: 'Free', price: '$0', color: '#6c757d' },
  basic: { name: 'Basic', price: '$9.99/mo', color: '#0d6efd' },
  pro: { name: 'Pro', price: '$29.99/mo', color: '#198754' },
  enterprise: { name: 'Enterprise', price: 'Custom', color: '#6f42c1' }
};

export const Subscription: React.FC<SubscriptionProps> = ({ token, userId }) => {
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetchSubscription();
  }, [userId, token]);

  const fetchSubscription = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/subscription?user_id=${userId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (!response.ok) throw new Error('Failed to fetch subscription');
      
      const data = await response.json();
      setSubscription(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tier: string) => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/subscription/upgrade`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ user_id: userId, tier })
        }
      );

      if (!response.ok) throw new Error('Failed to upgrade subscription');

      const data = await response.json();
      
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        await fetchSubscription();
        setShowModal(false);
        alert('Subscription updated successfully!');
      }
    } catch (err) {
      alert(`Update failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (loading) return <div className="page-container"><p className="subscription-loading">Loading subscription...</p></div>;
  if (error) return <div className="page-container"><p className="subscription-error">Error: {error}</p></div>;
  if (!subscription) return null;

  const tierInfo = TIER_INFO[subscription.tier as keyof typeof TIER_INFO];
  const { limits, usage } = subscription;

  return (
    <div className="page-container subscription-container">
      <h2>Subscription</h2>

      <div className="current-plan">
        <div className="tier-badge" style={{ backgroundColor: tierInfo.color }}>
          {tierInfo.name}
        </div>
        <h2>Current Plan</h2>
        <p className="tier-price">{tierInfo.price}</p>
        
        <div className="usage-stats">
          <div className="usage-item">
            <label>User Models</label>
            <div className="usage-bar">
              <div 
                className="usage-fill" 
                style={{ 
                  width: limits.max_user_models === -1 
                    ? '0%' 
                    : `${(usage.user_models_count / limits.max_user_models) * 100}%` 
                }}
              />
            </div>
            <span>
              {usage.user_models_count} / {limits.max_user_models === -1 ? '∞' : limits.max_user_models}
            </span>
          </div>
          <div className="usage-item">
            <label>Custom Datasets</label>
            <div className="usage-bar">
              <div 
                className="usage-fill" 
                style={{ 
                  width: limits.max_custom_datasets === -1 
                    ? '0%' 
                    : `${(usage.datasets_count / limits.max_custom_datasets) * 100}%` 
                }}
              />
            </div>
            <span>
              {usage.datasets_count} / {limits.max_custom_datasets === -1 ? '∞' : limits.max_custom_datasets}
            </span>
          </div>
        </div>

        <div className="features-list">
          <h3>Plan Features</h3>
          <div className="feature-item">
            <span className={Array.isArray(limits.system_models) || limits.system_models ? 'enabled' : 'disabled'}>
              {Array.isArray(limits.system_models) || limits.system_models ? '✓' : '✗'}
            </span>
            System Models {Array.isArray(limits.system_models) 
              ? `(Carpool only)` 
              : limits.system_models === true 
                ? '(All 10 models)' 
                : '(None)'}
          </div>
          <div className="feature-item">
            <span className={limits.show_reasoning ? 'enabled' : 'disabled'}>
              {limits.show_reasoning ? '✓' : '✗'}
            </span>
            Detailed Reasoning & Analysis
          </div>
          <div className="feature-item">
            <span className={limits.benny_ai ? 'enabled' : 'disabled'}>
              {limits.benny_ai ? '✓' : '✗'}
            </span>
            Benny AI Assistant
          </div>
          <div className="feature-item">
            <span className={limits.user_models ? 'enabled' : 'disabled'}>
              {limits.user_models ? '✓' : '✗'}
            </span>
            Custom Models
          </div>
          <div className="feature-item">
            <span className={limits.custom_data ? 'enabled' : 'disabled'}>
              {limits.custom_data ? '✓' : '✗'}
            </span>
            Custom Data
          </div>
          <div className="feature-item">
            <span className={limits.model_marketplace ? 'enabled' : 'disabled'}>
              {limits.model_marketplace ? '✓' : '✗'}
            </span>
            Model Marketplace
          </div>
        </div>

        <button className="upgrade-btn" onClick={() => setShowModal(true)}>
          Change Plan
        </button>
      </div>

      {showModal && (
        <SubscriptionModal
          currentTier={subscription.tier}
          onClose={() => setShowModal(false)}
          onSelectTier={handleUpgrade}
        />
      )}
    </div>
  );
};
