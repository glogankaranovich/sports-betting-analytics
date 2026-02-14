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

  if (loading) return <div className="subscription-loading">Loading subscription...</div>;
  if (error) return <div className="subscription-error">Error: {error}</div>;
  if (!subscription) return null;

  const tierInfo = TIER_INFO[subscription.tier as keyof typeof TIER_INFO];
  const { limits, usage } = subscription;

  return (
    <div className="subscription-container">
      <div className="subscription-header">
        <h1>Subscription</h1>
        <p>Manage your plan and usage</p>
      </div>

      <div className="current-plan">
        <div className="plan-badge" style={{ backgroundColor: tierInfo.color }}>
          {tierInfo.name}
        </div>
        <h2>Current Plan: {tierInfo.name}</h2>
        <p className="plan-price">{tierInfo.price}</p>
      </div>

      <div className="usage-stats">
        <h3>Usage This Period</h3>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">API Calls</div>
            <div className="stat-value">
              {usage.api_calls_today} / {limits.api_calls_per_day === -1 ? '∞' : limits.api_calls_per_day}
            </div>
            <div className="stat-bar">
              <div 
                className="stat-bar-fill" 
                style={{ 
                  width: limits.api_calls_per_day === -1 ? '0%' : 
                    `${Math.min((usage.api_calls_today / limits.api_calls_per_day) * 100, 100)}%` 
                }}
              />
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">User Models</div>
            <div className="stat-value">
              {usage.user_models_count} / {limits.max_user_models === -1 ? '∞' : limits.max_user_models}
            </div>
            <div className="stat-bar">
              <div 
                className="stat-bar-fill" 
                style={{ 
                  width: limits.max_user_models === -1 || limits.max_user_models === 0 ? '0%' : 
                    `${Math.min((usage.user_models_count / limits.max_user_models) * 100, 100)}%` 
                }}
              />
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Custom Datasets</div>
            <div className="stat-value">
              {usage.datasets_count} / {limits.max_custom_datasets === -1 ? '∞' : limits.max_custom_datasets}
            </div>
            <div className="stat-bar">
              <div 
                className="stat-bar-fill" 
                style={{ 
                  width: limits.max_custom_datasets === -1 || limits.max_custom_datasets === 0 ? '0%' : 
                    `${Math.min((usage.datasets_count / limits.max_custom_datasets) * 100, 100)}%` 
                }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="features-section">
        <h3>Your Features</h3>
        <div className="features-list">
          <div className={`feature-item ${limits.system_models ? 'enabled' : 'disabled'}`}>
            <span className="feature-icon">{limits.system_models ? '✓' : '✗'}</span>
            System Models
          </div>
          <div className={`feature-item ${limits.benny_ai ? 'enabled' : 'disabled'}`}>
            <span className="feature-icon">{limits.benny_ai ? '✓' : '✗'}</span>
            Benny AI Betting Assistant
          </div>
          <div className={`feature-item ${limits.user_models ? 'enabled' : 'disabled'}`}>
            <span className="feature-icon">{limits.user_models ? '✓' : '✗'}</span>
            Custom User Models
          </div>
          <div className={`feature-item ${limits.custom_data ? 'enabled' : 'disabled'}`}>
            <span className="feature-icon">{limits.custom_data ? '✓' : '✗'}</span>
            Custom Data Upload
          </div>
          <div className={`feature-item ${limits.model_marketplace ? 'enabled' : 'disabled'}`}>
            <span className="feature-icon">{limits.model_marketplace ? '✓' : '✗'}</span>
            Model Marketplace
          </div>
        </div>
      </div>

      {subscription.tier !== 'enterprise' && (
        <div className="upgrade-section">
          <h3>Upgrade Your Plan</h3>
          <div className="plans-grid">
            {subscription.tier === 'free' && (
              <>
                <div className="plan-card">
                  <h4>Basic</h4>
                  <p className="plan-card-price">$9.99/mo</p>
                  <ul>
                    <li>Benny AI Assistant</li>
                    <li>3 User Models</li>
                    <li>5 Custom Datasets</li>
                    <li>1,000 API calls/day</li>
                  </ul>
                  <button className="upgrade-btn">Upgrade to Basic</button>
                </div>
                <div className="plan-card featured">
                  <h4>Pro</h4>
                  <p className="plan-card-price">$29.99/mo</p>
                  <ul>
                    <li>Everything in Basic</li>
                    <li>20 User Models</li>
                    <li>50 Custom Datasets</li>
                    <li>10,000 API calls/day</li>
                    <li>Model Marketplace Access</li>
                  </ul>
                  <button className="upgrade-btn">Upgrade to Pro</button>
                </div>
              </>
            )}
            {subscription.tier === 'basic' && (
              <div className="plan-card featured">
                <h4>Pro</h4>
                <p className="plan-card-price">$29.99/mo</p>
                <ul>
                  <li>20 User Models (vs 3)</li>
                  <li>50 Custom Datasets (vs 5)</li>
                  <li>10,000 API calls/day (vs 1,000)</li>
                  <li>Model Marketplace Access</li>
                </ul>
                <button className="upgrade-btn">Upgrade to Pro</button>
              </div>
            )}
            <div className="plan-card">
              <h4>Enterprise</h4>
              <p className="plan-card-price">Custom Pricing</p>
              <ul>
                <li>Unlimited Everything</li>
                <li>Priority Support</li>
                <li>Custom Integrations</li>
                <li>Dedicated Account Manager</li>
              </ul>
              <button className="upgrade-btn">Contact Sales</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
