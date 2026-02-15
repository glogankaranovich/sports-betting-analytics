import React, { useState, useEffect } from 'react';
import './Subscription.css';

interface SubscriptionProps {
  token: string;
  userId: string;
}

interface TierLimits {
  system_models: boolean;
  benny_ai: boolean;
  user_models: boolean;
  custom_data: boolean;
  model_marketplace: boolean;
  api_calls_per_day: number;
  max_user_models: number;
  max_custom_datasets: number;
}

interface SubscriptionData {
  tier: string;
  limits: TierLimits;
  usage: {
    api_calls_today: number;
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

  if (loading) return <div className="page-container"><p>Loading subscription...</p></div>;
  if (error) return <div className="page-container"><p>Error: {error}</p></div>;
  if (!subscription) return null;

  const tierInfo = TIER_INFO[subscription.tier as keyof typeof TIER_INFO];
  const { limits, usage } = subscription;

  return (
    <div className="page-container subscription-container">
      <h2>Subscription</h2>
      <p>Manage your plan and usage</p>

      <div className="current-plan">
        <div className="tier-badge" style={{ backgroundColor: tierInfo.color }}>
          {tierInfo.name}
        </div>
        <h2>Current Plan</h2>
        <p className="tier-price">{tierInfo.price}</p>
        
        <div className="usage-stats">
          <div className="usage-item">
            <label>API Calls Today</label>
            <div className="usage-bar">
              <div 
                className="usage-fill" 
                style={{ width: `${(usage.api_calls_today / limits.api_calls_per_day) * 100}%` }}
              />
            </div>
            <span>{usage.api_calls_today} / {limits.api_calls_per_day}</span>
          </div>
          <div className="usage-item">
            <label>User Models</label>
            <span>{usage.user_models_count} / {limits.max_user_models}</span>
          </div>
          <div className="usage-item">
            <label>Custom Datasets</label>
            <span>{usage.datasets_count} / {limits.max_custom_datasets}</span>
          </div>
        </div>

        <div className="features-list">
          <h3>Plan Features</h3>
          <div className="feature-item">
            <span className={limits.system_models ? 'enabled' : 'disabled'}>
              {limits.system_models ? '✓' : '✗'}
            </span>
            System Models
          </div>
          <div className="feature-item">
            <span className={limits.benny_ai ? 'enabled' : 'disabled'}>
              {limits.benny_ai ? '✓' : '✗'}
            </span>
            Benny AI
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
        </div>

        {subscription.tier === 'free' && (
          <button className="upgrade-btn">Upgrade Plan</button>
        )}
      </div>
    </div>
  );
};
