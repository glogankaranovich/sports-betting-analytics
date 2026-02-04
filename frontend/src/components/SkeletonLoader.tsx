import React from 'react';

export const GameCardSkeleton: React.FC = () => (
  <div className="skeleton-card">
    <div className="skeleton skeleton-line title"></div>
    <div className="skeleton skeleton-line medium"></div>
    <div className="skeleton skeleton-line short"></div>
    <div style={{ marginTop: '1rem' }}>
      <div className="skeleton skeleton-line"></div>
      <div className="skeleton skeleton-line"></div>
    </div>
  </div>
);

export const AnalysisCardSkeleton: React.FC = () => (
  <div className="skeleton-card">
    <div className="skeleton skeleton-line title"></div>
    <div className="skeleton skeleton-line"></div>
    <div className="skeleton skeleton-line medium"></div>
    <div className="skeleton skeleton-line short"></div>
  </div>
);

export const GamesGridSkeleton: React.FC<{ count?: number }> = ({ count = 6 }) => (
  <div className="skeleton-grid">
    {Array.from({ length: count }).map((_, i) => (
      <GameCardSkeleton key={i} />
    ))}
  </div>
);

export const AnalysisGridSkeleton: React.FC<{ count?: number }> = ({ count = 4 }) => (
  <div className="skeleton-grid">
    {Array.from({ length: count }).map((_, i) => (
      <AnalysisCardSkeleton key={i} />
    ))}
  </div>
);
