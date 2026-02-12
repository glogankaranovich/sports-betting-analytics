import React from 'react';
import './TopNav.css';

interface TopNavProps {
  currentPage: string;
  onNavigate: (page: string) => void;
  onSignOut?: () => void;
  logo?: string;
}

export const TopNav: React.FC<TopNavProps> = ({ currentPage, onNavigate, onSignOut, logo }) => {
  const sections = [
    { label: 'User', page: 'user-home' },
    { label: 'Analysis', page: 'analysis-home' },
    { label: 'Models', page: 'models-home' },
    { label: 'Marketplace', page: 'marketplace' },
    { label: 'About', page: 'about' },
  ];

  const getCurrentSection = () => {
    if (currentPage.startsWith('user-') || ['profile', 'settings', 'subscription'].includes(currentPage)) return 'user-home';
    if (currentPage.startsWith('analysis-') || ['games', 'game-analysis', 'prop-analysis'].includes(currentPage)) return 'analysis-home';
    if (currentPage.startsWith('models-') || ['system-models', 'my-models', 'model-analytics', 'model-comparison', 'benny-dashboard'].includes(currentPage)) return 'models-home';
    if (currentPage === 'marketplace') return 'marketplace';
    if (['about', 'how-it-works', 'terms', 'privacy'].includes(currentPage)) return 'about';
    return currentPage;
  };

  const currentSection = getCurrentSection();

  return (
    <nav className="top-nav">
      {logo && (
        <img src={logo} alt="Carpool Bets" className="nav-logo" onClick={() => onNavigate('analysis-home')} />
      )}
      <div className="nav-sections">
        {sections.map((section) => (
          <button
            key={section.page}
            className={`nav-button ${currentSection === section.page ? 'active' : ''}`}
            onClick={() => onNavigate(section.page)}
          >
            {section.label}
          </button>
        ))}
      </div>
      {onSignOut && (
        <button className="sign-out-button" onClick={onSignOut}>
          Sign Out
        </button>
      )}
    </nav>
  );
};
