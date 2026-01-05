import React, { useState } from 'react';
import './TermsAcceptance.css';

interface TermsAcceptanceProps {
  onAccepted: (accepted: boolean) => void;
}

const TermsAcceptance: React.FC<TermsAcceptanceProps> = ({ onAccepted }) => {
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  const [acceptedRisks, setAcceptedRisks] = useState(false);

  const handleAccept = () => {
    if (acceptedTerms && acceptedPrivacy && acceptedRisks) {
      const acceptance = {
        termsAccepted: true,
        privacyAccepted: true,
        risksAccepted: true,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        ipAddress: 'logged-server-side'
      };
      
      localStorage.setItem('termsAcceptance', JSON.stringify(acceptance));
      onAccepted(true);
    }
  };

  const allAccepted = acceptedTerms && acceptedPrivacy && acceptedRisks;

  return (
    <div className="terms-overlay">
      <div className="terms-modal">
        <div className="terms-header">
          <h2>Terms and Conditions</h2>
          <p>Please review and accept our terms to continue</p>
        </div>
        
        <div className="terms-content">
          <div className="terms-section">
            <h3>⚠️ Risk Acknowledgment</h3>
            <div className="terms-text">
              <p><strong>IMPORTANT:</strong> This platform provides betting analysis for entertainment purposes only.</p>
              <ul>
                <li>All recommendations are informational and do not guarantee profits</li>
                <li>Gambling involves significant financial risk</li>
                <li>You may lose all money wagered</li>
                <li>Never bet more than you can afford to lose</li>
                <li>Gambling can be addictive</li>
              </ul>
            </div>
          </div>

          <div className="checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={acceptedRisks}
                onChange={(e) => setAcceptedRisks(e.target.checked)}
              />
              <span className="checkmark"></span>
              I understand and accept all gambling risks and disclaimers
            </label>
          </div>

          <div className="checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={acceptedTerms}
                onChange={(e) => setAcceptedTerms(e.target.checked)}
              />
              <span className="checkmark"></span>
              I agree to the &nbsp;<a href="/terms" target="_blank">Terms of Service</a>
            </label>
          </div>

          <div className="checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={acceptedPrivacy}
                onChange={(e) => setAcceptedPrivacy(e.target.checked)}
              />
              <span className="checkmark"></span>
              I agree to the &nbsp;<a href="/privacy" target="_blank">Privacy Policy</a>
            </label>
          </div>
        </div>
        
        <div className="terms-footer">
          <button 
            className={`accept-button ${allAccepted ? 'enabled' : 'disabled'}`}
            onClick={handleAccept}
            disabled={!allAccepted}
          >
            Accept and Continue
          </button>
          <p className="legal-note">
            By clicking "Accept and Continue", you acknowledge that you have read, 
            understood, and agree to be bound by these terms.
          </p>
        </div>
      </div>
    </div>
  );
};

export default TermsAcceptance;
