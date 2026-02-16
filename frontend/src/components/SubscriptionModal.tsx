import React from 'react';
import './SubscriptionModal.css';

interface SubscriptionModalProps {
  currentTier: string;
  onClose: () => void;
  onSelectTier: (tier: string) => void;
}

const TIERS = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    models: 0,
    datasets: 0,
    features: ['Ensemble Model Only', 'Basic Predictions', 'No Detailed Analysis']
  },
  {
    id: 'basic',
    name: 'Basic',
    price: '$9.99/mo',
    models: 3,
    datasets: 5,
    features: ['All 10 System Models', 'Detailed Reasoning & Analysis', 'Model Comparison', 'Custom Models (3)', 'Custom Data (5)']
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$29.99/mo',
    models: 20,
    datasets: 50,
    features: ['Everything in Basic', 'Benny AI Assistant', 'Benny Dashboard', 'Model Marketplace', 'Custom Models (20)', 'Custom Data (50)']
  }
];

export const SubscriptionModal: React.FC<SubscriptionModalProps> = ({ currentTier, onClose, onSelectTier }) => {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Choose Your Plan</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="tiers-grid">
          {TIERS.map(tier => (
            <div 
              key={tier.id}
              className={`tier-card ${tier.id === currentTier ? 'current' : ''}`}
            >
              <h3>{tier.name}</h3>
              <div className="tier-price">{tier.price}</div>
              
              <div className="tier-limits">
                <div>Models: {tier.models === -1 ? '∞' : tier.models}</div>
                <div>Datasets: {tier.datasets === -1 ? '∞' : tier.datasets}</div>
              </div>
              
              <ul className="tier-features">
                {tier.features.map(feature => (
                  <li key={feature}>✓ {feature}</li>
                ))}
              </ul>
              
              {tier.id === currentTier ? (
                <button className="tier-btn current-btn" disabled>Current Plan</button>
              ) : (
                <button 
                  className="tier-btn select-btn"
                  onClick={() => onSelectTier(tier.id)}
                >
                  Select {tier.name}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
