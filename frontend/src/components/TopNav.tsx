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
    { label: 'User', page: 'profile' },
    { label: 'Analysis', page: 'games' },
    { label: 'Models', page: 'model-comparison' },
    { label: 'Marketplace', page: 'marketplace' },
  ];

  const getCurrentSection = () => {
    if (currentPage.startsWith('user-') || ['profile', 'settings', 'subscription'].includes(currentPage)) return 'user-home';
    if (currentPage.startsWith('analysis-') || ['games', 'player-props', 'game-analysis', 'prop-analysis', 'benny-dashboard'].includes(currentPage)) return 'analysis-home';
    if (currentPage.startsWith('models-') || ['system-models', 'my-models', 'model-analytics', 'model-comparison'].includes(currentPage)) return 'models-home';
    if (currentPage === 'marketplace') return 'marketplace';
    if (['about', 'how-it-works', 'terms', 'privacy'].includes(currentPage)) return 'about';
    return currentPage;
  };

  const currentSection = getCurrentSection();

  return (
    <nav className="top-nav">
      {logo && (
        <img src={logo} alt="Carpool Bets" className="nav-logo" onClick={() => onNavigate('game-bets')} />
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
