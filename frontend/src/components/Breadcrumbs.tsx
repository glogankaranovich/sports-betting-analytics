import React from 'react';
import './Breadcrumbs.css';

interface BreadcrumbsProps {
  section: string;
  currentPage: string;
  onNavigate: (page: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ section, currentPage, onNavigate, isCollapsed, onToggleCollapse }) => {
  const getSectionName = () => {
    if (section === 'user-home') return 'User';
    if (section === 'analysis-home') return 'Analysis';
    if (section === 'models-home') return 'Models';
    if (section === 'about') return 'About';
    if (section === 'marketplace') return 'Marketplace';
    return '';
  };

  const getPageName = () => {
    const pageNames: Record<string, string> = {
      'profile': 'Profile',
      'settings': 'Settings',
      'subscription': 'Subscription',
      'games': 'Top Insights',
      'game-analysis': 'Game Predictions',
      'prop-analysis': 'Prop Predictions',
      'system-models': 'System Models',
      'my-models': 'My Models',
      'model-analytics': 'Model Analytics',
      'model-comparison': 'Model Comparison',
      'benny-dashboard': 'Benny Dashboard',
      'how-it-works': 'How It Works',
      'terms': 'Terms of Service',
      'privacy': 'Privacy Policy',
      'marketplace': 'Marketplace',
    };
    return pageNames[currentPage] || '';
  };

  const sectionName = getSectionName();
  const pageName = getPageName();

  // Don't show breadcrumbs on home pages
  const showBreadcrumbs = !currentPage.includes('-home') && currentPage !== 'about';

  return (
    <nav className="breadcrumbs">
      <button 
        className="collapse-button" 
        onClick={onToggleCollapse}
        aria-label={isCollapsed ? 'Show sidebar' : 'Hide sidebar'}
      >
        <div className="hamburger-icon">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </button>
      {showBreadcrumbs && (
        <>
          <button className="breadcrumb-item" onClick={() => onNavigate(section)}>
            {sectionName}
          </button>
          <span className="breadcrumb-separator">/</span>
          <span className="breadcrumb-current">{pageName}</span>
        </>
      )}
    </nav>
  );
};
