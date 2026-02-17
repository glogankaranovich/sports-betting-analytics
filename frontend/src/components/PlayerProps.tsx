import React, { useState, useEffect, useCallback } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { PlayerProp } from '../types/betting';
import { bettingApi } from '../services/api';
import Settings from './Settings';

interface PlayerPropsProps {
  token: string;
  games?: any[];
  currentPage: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  settings: {
    sport: string;
    bookmaker: string;
    model: string;
  };
  onSettingsChange: (settings: any) => void;
  availableSports: string[];
  availableBookmakers: string[];
  userModels: any[];
  subscription: any;
}

const PlayerProps: React.FC<PlayerPropsProps> = ({ 
  token, 
  games = [], 
  currentPage, 
  itemsPerPage, 
  onPageChange,
  settings,
  onSettingsChange,
  availableSports,
  availableBookmakers,
  userModels,
  subscription
}) => {
  const [props, setProps] = useState<PlayerProp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPropPage, setCurrentPropPage] = useState(1);
  const propsPerPage = 20;
  const [filters, setFilters] = useState({
    sport: '',
    bookmaker: '',
    prop_type: '',
    player_name: ''
  });
  const [propsSort, setPropsSort] = useState<'player' | 'time'>('player');
  const [propsSortDir, setPropsSortDir] = useState<'asc' | 'desc'>('asc');
  const [showFilters, setShowFilters] = useState(false);
  const [showSort, setShowSort] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const propTypeLabels: { [key: string]: string } = {
    // NFL
    'player_pass_tds': 'Passing TDs',
    'player_pass_yds': 'Passing Yards',
    'player_rush_yds': 'Rushing Yards',
    'player_receptions': 'Receptions',
    'player_reception_yds': 'Receiving Yards',
    // NBA
    'player_points': 'Points',
    'player_rebounds': 'Rebounds',
    'player_assists': 'Assists',
    'player_threes': '3-Pointers Made',
    'player_blocks': 'Blocks',
    'player_steals': 'Steals'
  };

  const getSportPropTypes = (sport: string) => {
    if (sport === 'basketball_nba') {
      return ['player_points', 'player_rebounds', 'player_assists'];
    } else if (sport === 'americanfootball_nfl') {
      return ['player_pass_tds', 'player_pass_yds', 'player_rush_yds', 'player_receptions', 'player_reception_yds'];
    }
    return Object.keys(propTypeLabels);
  };

  const fetchPlayerProps = useCallback(async () => {
    try {
      setLoading(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (!token) {
        setProps([]);
        setLoading(false);
        return;
      }
      
      const filterParams = {
        sport: settings.sport,
        bookmaker: settings.bookmaker,
        prop_type: filters.prop_type || undefined,
        fetchAll: true
      };
      
      const response = await bettingApi.getPlayerProps(token, filterParams);
      setProps(response.props || []);
      setError(null);
    } catch (err) {
      setError('Failed to fetch player props');
      console.error('Error fetching player props:', err);
      setProps([]);
    } finally {
      setLoading(false);
    }
  }, [settings.sport, settings.bookmaker, filters]);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPropPage(1);
    onPageChange(1);
  }, [filters, onPageChange]);

  useEffect(() => {
    fetchPlayerProps();
  }, [fetchPlayerProps]);

  const formatPrice = (price: number) => {
    return price > 0 ? `+${price}` : price.toString();
  };

  const groupedProps = props.reduce((acc, prop) => {
    const key = `${prop.event_id}-${prop.player_name}-${prop.market_key}`;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(prop);
    return acc;
  }, {} as { [key: string]: PlayerProp[] });

  const groupedPropsArray = Object.entries(groupedProps)
    .filter(([key, propGroup]) => {
      if (!filters.player_name) return true;
      const playerName = propGroup[0]?.player_name || '';
      return playerName.toLowerCase().includes(filters.player_name.toLowerCase());
    })
    .sort((a, b) => {
      let comparison = 0;
      if (propsSort === 'player') {
        const playerA = a[1][0]?.player_name || '';
        const playerB = b[1][0]?.player_name || '';
        comparison = playerA.localeCompare(playerB);
      } else {
        const timeA = new Date(a[1][0]?.commence_time || 0).getTime();
        const timeB = new Date(b[1][0]?.commence_time || 0).getTime();
        comparison = timeA - timeB;
      }
      return propsSortDir === 'desc' ? -comparison : comparison;
    });
  
  // Client-side pagination
  const totalPages = Math.ceil(groupedPropsArray.length / propsPerPage);
  const startIndex = (currentPropPage - 1) * propsPerPage;
  const paginatedProps = groupedPropsArray.slice(startIndex, startIndex + propsPerPage);

  if (loading) return <div className="loading">Loading player props...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="player-props">
      <div className="games-header">
        <h2>Prop Bets</h2>
        <div className="filters">
          <button 
            className="filter-icon-btn"
            onClick={() => setShowSettings(!showSettings)}
            aria-label="Toggle settings"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ marginRight: '0.5rem' }}>
              <path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/>
              <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319z"/>
            </svg>
            Settings
          </button>
          <button 
            className="filter-icon-btn"
            onClick={() => setShowFilters(!showFilters)}
            aria-label="Toggle filters"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ marginRight: '0.5rem' }}>
              <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5v-2z"/>
            </svg>
            Filter {(filters.player_name || filters.prop_type) && <span className="filter-badge">•</span>}
          </button>
          <button 
            className="filter-icon-btn"
            onClick={() => setShowSort(!showSort)}
            aria-label="Toggle sort options"
          >
            ⇅ Sort
          </button>
        </div>
      </div>
      
      {showSettings && (
        <div className="filter-panel">
          <Settings 
            settings={settings}
            onSettingsChange={onSettingsChange}
            availableSports={availableSports}
            availableBookmakers={availableBookmakers}
            userModels={userModels}
            token={token}
            subscription={subscription}
          />
        </div>
      )}
      
      {showFilters && (
        <div className="filter-panel">
          <input
            type="text"
            placeholder="Filter by player..."
            value={filters.player_name}
            onChange={(e) => setFilters({...filters, player_name: e.target.value})}
            className="filter-select"
          />
          <select 
            className="filter-select"
            value={filters.prop_type} 
            onChange={(e) => setFilters({...filters, prop_type: e.target.value})}
          >
            <option key="all-props" value="">All Prop Types</option>
            {getSportPropTypes(settings.sport).map((key) => (
              <option key={key} value={key}>{propTypeLabels[key]}</option>
            ))}
          </select>
        </div>
      )}
      
      {showSort && (
        <div className="filter-panel">
          <select 
            className="filter-select"
            value={propsSort} 
            onChange={(e) => setPropsSort(e.target.value as 'player' | 'time')}
          >
            <option value="player">Sort by Player</option>
            <option value="time">Sort by Time</option>
          </select>
          <select 
            className="filter-select"
            value={propsSortDir} 
            onChange={(e) => setPropsSortDir(e.target.value as 'asc' | 'desc')}
          >
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>
      )}

      <div className="games-grid">
        {paginatedProps.map(([key, propGroup]) => {
          const [eventId, playerName, marketKey] = key.split('-');
          const firstProp = propGroup[0];
          
          // Find the matching game for this event
          const matchingGame = games.find(game => game.game_id === eventId);
          const gameMatchup = matchingGame 
            ? `${matchingGame.away_team} @ ${matchingGame.home_team}`
            : 'Game TBD';
          
          return (
            <div key={key} className="game-card">
              <div className="game-header">
                <div className="teams">
                  <h3>{playerName} - {propTypeLabels[marketKey] || marketKey}</h3>
                  <p className="game-matchup">{gameMatchup}</p>
                  <p className="game-time">{new Date(firstProp.commence_time).toLocaleString()}</p>
                </div>
              </div>
              
              <div className="odds-section">
                <div className="odds-header">
                  <span className="odds-label">O/U {firstProp.point} {propTypeLabels[marketKey] || marketKey}</span>
                </div>
                <div className="bookmaker-odds">
                  {Object.entries(
                    propGroup.reduce((acc, prop) => {
                      if (!acc[prop.bookmaker]) acc[prop.bookmaker] = {};
                      acc[prop.bookmaker][prop.outcome] = prop;
                      return acc;
                    }, {} as Record<string, Record<string, any>>)
                  ).map(([bookmaker, outcomes]) => (
                    <div key={bookmaker} className="bookmaker-row">
                      <div className="odds-values">
                        {outcomes.Over && (
                          <span className="odds-value home">
                            Over: {formatPrice(outcomes.Over.price)}
                          </span>
                        )}
                        {outcomes.Under && (
                          <span className="odds-value away">
                            Under: {formatPrice(outcomes.Under.price)}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {totalPages > 1 && (
        <div style={{ textAlign: 'center', marginTop: '20px', display: 'flex', gap: '10px', justifyContent: 'center', alignItems: 'center' }}>
          <button 
            onClick={() => setCurrentPropPage(p => Math.max(1, p - 1))} 
            disabled={currentPropPage === 1}
            style={{ padding: '8px 16px', cursor: currentPropPage === 1 ? 'not-allowed' : 'pointer' }}
          >
            Previous
          </button>
          <span>Page {currentPropPage} of {totalPages} ({groupedPropsArray.length} props)</span>
          <button 
            onClick={() => setCurrentPropPage(p => Math.min(totalPages, p + 1))} 
            disabled={currentPropPage === totalPages}
            style={{ padding: '8px 16px', cursor: currentPropPage === totalPages ? 'not-allowed' : 'pointer' }}
          >
            Next
          </button>
        </div>
      )}
      
      {props.length === 0 && (
        <div className="no-data">No player props found for current filters</div>
      )}
    </div>
  );
};

export default PlayerProps;
