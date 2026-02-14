import React from 'react';
import './SideNav.css';

interface SideNavItem {
  label: string;
  page: string;
  icon?: string;
}

interface SideNavProps {
  section: string;
  currentPage: string;
  onNavigate: (page: string) => void;
  isCollapsed: boolean;
}

export const SideNav: React.FC<SideNavProps> = ({ section, currentPage, onNavigate, isCollapsed }) => {
  const navItems: Record<string, SideNavItem[]> = {
    'user-home': [
      { label: 'Profile', page: 'profile' },
      { label: 'Settings', page: 'settings' },
      { label: 'Subscription', page: 'subscription' },
    ],
    'analysis-home': [
      { label: 'Game Bets', page: 'games' },
      { label: 'Prop Bets', page: 'player-props' },
      { label: 'Game Analysis', page: 'game-analysis' },
      { label: 'Prop Analysis', page: 'prop-analysis' },
      { label: 'Benny AI', page: 'benny-dashboard' },
    ],
    'models-home': [
      { label: 'System Models', page: 'system-models' },
      { label: 'My Models', page: 'my-models' },
      { label: 'Model Comparison', page: 'model-comparison' },
    ],
  };

  const items = navItems[section] || [];

  const getSectionTitle = () => {
    if (section === 'user-home') return 'User';
    if (section === 'analysis-home') return 'Analysis';
    if (section === 'models-home') return 'Models';
    return '';
  };

  if (items.length === 0) return null;

  return (
    <aside className={`side-nav ${isCollapsed ? 'hidden' : ''}`}>
      <div className="side-nav-header">
        <h3 className="section-title">{getSectionTitle()}</h3>
      </div>
      <nav className="side-nav-items">
        {items.map((item) => (
          <button
            key={item.page}
            className={`side-nav-item ${currentPage === item.page ? 'active' : ''}`}
            onClick={() => onNavigate(item.page)}
          >
            <span className="side-nav-label">{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
};
