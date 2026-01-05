import React, { useState, useEffect } from 'react';
import AgeVerification from './AgeVerification';
import TermsAcceptance from './TermsAcceptance';
import DisclaimerBanner from './DisclaimerBanner';
import ResponsibleGambling from './ResponsibleGambling';
import Footer from './Footer';
import { complianceTracker } from '../utils/complianceTracker';
import './ComplianceWrapper.css';

const ComplianceWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [showAgeVerification, setShowAgeVerification] = useState(false);
  const [showTermsAcceptance, setShowTermsAcceptance] = useState(false);
  const [showResponsibleGambling, setShowResponsibleGambling] = useState(false);
  const [isCompliant, setIsCompliant] = useState(false);

  useEffect(() => {
    // Check compliance status on load
    const status = complianceTracker.getComplianceStatus();
    
    if (!status.ageVerified) {
      setShowAgeVerification(true);
      complianceTracker.logAction('age_verification_required');
    } else if (!status.termsAccepted) {
      setShowTermsAcceptance(true);
      complianceTracker.logAction('terms_acceptance_required');
    } else {
      setIsCompliant(true);
      complianceTracker.logAction('compliance_check_passed');
    }
  }, []);

  const handleAgeVerified = (verified: boolean) => {
    if (verified) {
      setShowAgeVerification(false);
      setShowTermsAcceptance(true);
      complianceTracker.logAction('age_verified', { verified: true });
    } else {
      complianceTracker.logAction('age_verification_failed');
      // Redirect to age restriction page or show error
    }
  };

  const handleTermsAccepted = (accepted: boolean) => {
    if (accepted) {
      setShowTermsAcceptance(false);
      setIsCompliant(true);
      complianceTracker.logAction('terms_accepted');
    }
  };

  const handleResponsibleGamblingOpen = () => {
    setShowResponsibleGambling(true);
    complianceTracker.logAction('responsible_gambling_modal_opened');
  };

  const handleResponsibleGamblingClose = () => {
    setShowResponsibleGambling(false);
    complianceTracker.logAction('responsible_gambling_modal_closed');
  };

  if (showAgeVerification) {
    return <AgeVerification onVerified={handleAgeVerified} />;
  }

  if (showTermsAcceptance) {
    return <TermsAcceptance onAccepted={handleTermsAccepted} />;
  }

  if (!isCompliant) {
    return <div>Loading compliance checks...</div>;
  }

  return (
    <div className="app-with-compliance">
      <DisclaimerBanner />
      
      <div className="main-content">
        {children}
      </div>
      
      <div className="responsible-gambling-trigger">
        <button 
          onClick={handleResponsibleGamblingOpen}
          className="responsible-gambling-button"
        >
          Responsible Gambling Resources
        </button>
      </div>
      
      <Footer />
      
      <ResponsibleGambling 
        isOpen={showResponsibleGambling}
        onClose={handleResponsibleGamblingClose}
      />
    </div>
  );
};

export default ComplianceWrapper;
