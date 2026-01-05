import React, { useState } from 'react';
import './DisclaimerBanner.css';

const DisclaimerBanner: React.FC = () => {
  const [isVisible, setIsVisible] = useState(true);

  if (!isVisible) return null;

  return (
    <div className="disclaimer-banner">
      <div className="disclaimer-content">
        <span className="disclaimer-text">
          ⚠️ <strong>Risk Warning:</strong> All betting recommendations are for entertainment purposes only. 
          Gambling involves risk of loss. Never bet more than you can afford to lose. 
          Must be 21+ to participate.
        </span>
        <button 
          className="disclaimer-close"
          onClick={() => setIsVisible(false)}
          aria-label="Close disclaimer"
        >
          ×
        </button>
      </div>
    </div>
  );
};

export default DisclaimerBanner;
