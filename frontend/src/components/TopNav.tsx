import React, { useState, useRef, useEffect } from 'react';
import './TopNav.css';

interface NavItem {
  label: string;
  items: { label: string; page: string }[];
}

interface TopNavProps {
  currentPage: string;
  onNavigate: (page: string) => void;
  onSignOut?: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({ currentPage, onNavigate, onSignOut }) => {
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const navSections: NavItem[] = [
    {
      label: 'User',
      items: [
        { label: 'Profile', page: 'profile' },
        { label: 'Settings', page: 'settings' },
        { label: 'Subscription', page: 'subscription' },
        { label: 'My Models', page: 'my-models' },
      ],
    },
    {
      label: 'Analysis',
      items: [
        { label: 'Game Predictions', page: 'game-analysis' },
        { label: 'Prop Predictions', page: 'prop-analysis' },
        { label: 'Top Insights', page: 'games' },
      ],
    },
    {
      label: 'Models',
      items: [
        { label: 'System Models', page: 'system-models' },
        { label: 'Model Analytics', page: 'model-analytics' },
        { label: 'Model Comparison', page: 'model-comparison' },
        { label: 'Benny Dashboard', page: 'benny-dashboard' },
      ],
    },
    {
      label: 'Marketplace',
      items: [
        { label: 'Coming Soon', page: 'marketplace' },
      ],
    },
    {
      label: 'About',
      items: [
        { label: 'How It Works', page: 'how-it-works' },
        { label: 'Terms of Service', page: 'terms' },
        { label: 'Privacy Policy', page: 'privacy' },
      ],
    },
  ];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdown(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleDropdownToggle = (section: string) => {
    setOpenDropdown(openDropdown === section ? null : section);
  };

  const handleNavigate = (page: string) => {
    onNavigate(page);
    setOpenDropdown(null);
  };

  return (
    <nav className="top-nav" ref={dropdownRef}>
      <div className="nav-sections">
        {navSections.map((section) => (
          <div key={section.label} className="nav-section">
            <button
              className={`nav-button ${openDropdown === section.label ? 'active' : ''}`}
              onClick={() => handleDropdownToggle(section.label)}
            >
              {section.label}
              <span className="dropdown-arrow">▼</span>
            </button>
            {openDropdown === section.label && (
              <div className="dropdown-menu">
                {section.items.map((item) => (
                  <button
                    key={item.page}
                    className={`dropdown-item ${currentPage === item.page ? 'active' : ''}`}
                    onClick={() => handleNavigate(item.page)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
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
