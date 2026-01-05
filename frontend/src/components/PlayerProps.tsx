import React, { useState, useEffect, useCallback } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { PlayerProp } from '../types/betting';
import { bettingApi } from '../services/api';

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
    riskTolerance: string;
  };
}

const PlayerProps: React.FC<PlayerPropsProps> = ({ 
  token, 
  games = [], 
  currentPage, 
  itemsPerPage, 
  onPageChange,
  settings
}) => {
  const [props, setProps] = useState<PlayerProp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    sport: '',
    bookmaker: '',
    prop_type: ''
  });

  const propTypeLabels: { [key: string]: string } = {
    'player_pass_tds': 'Passing TDs',
    'player_pass_yds': 'Passing Yards',
    'player_rush_yds': 'Rushing Yards',
    'player_receptions': 'Receptions',
    'player_reception_yds': 'Receiving Yards',
    'player_points': 'Points',
    'player_rebounds': 'Rebounds',
    'player_assists': 'Assists'
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
        limit: 500
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

  // Paginate the grouped props
  const groupedPropsArray = Object.entries(groupedProps);
  const getTotalPages = () => Math.ceil(groupedPropsArray.length / itemsPerPage);
  const paginateItems = () => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return groupedPropsArray.slice(startIndex, startIndex + itemsPerPage);
  };

  if (loading) return <div className="loading">Loading player props...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="player-props">
      <div className="games-header">
        <h2>Prop Bets</h2>
        <div className="filters">
          <select 
            className="filter-select"
            value={filters.prop_type} 
            onChange={(e) => setFilters({...filters, prop_type: e.target.value})}
          >
            <option key="all-props" value="">All Prop Types</option>
            {Object.entries(propTypeLabels).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="games-grid">
        {paginateItems().map(([key, propGroup]) => {
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
                  <div className="sport-tag">{gameMatchup}</div>
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

      {groupedPropsArray.length > itemsPerPage && (
        <div className="pagination">
          <button 
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </button>
          <span>Page {currentPage} of {getTotalPages()}</span>
          <button 
            onClick={() => onPageChange(Math.min(getTotalPages(), currentPage + 1))}
            disabled={currentPage === getTotalPages()}
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
