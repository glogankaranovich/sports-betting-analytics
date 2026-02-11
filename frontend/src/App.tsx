import React, { useState, useEffect, useCallback } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { bettingApi } from './services/api';
import { Game } from './types/betting';
import PlayerProps from './components/PlayerProps';
import Settings from './components/Settings';
import ComplianceWrapper from './components/ComplianceWrapper';
import { ModelAnalytics } from './components/ModelAnalytics';
import { ModelComparison } from './components/ModelComparison';
import Models from './components/Models';
import { UserModels } from './components/UserModels';
import { Benny } from './components/Benny';
import { BennyDashboard } from './components/BennyDashboard';
import LandingPage from './components/LandingPage';
import { GamesGridSkeleton, AnalysisGridSkeleton } from './components/SkeletonLoader';
import TermsOfService from './components/TermsOfService';
import PrivacyPolicy from './components/PrivacyPolicy';
import logo from './assets/logo_2.png';
import './amplifyConfig'; // Initialize Amplify
import '@aws-amplify/ui-react/styles.css';
import './amplify-theme.css';
import './App.css';

function Dashboard({ user, signOut }: { user: any; signOut?: () => void }) {
  const propTypeLabels: { [key: string]: string } = {
    'player_pass_tds': 'Passing TDs',
    'player_pass_yds': 'Passing Yards',
    'player_rush_yds': 'Rushing Yards',
    'player_receptions': 'Receptions',
    'player_reception_yds': 'Receiving Yards',
    'player_points': 'Points',
    'player_rebounds': 'Rebounds',
    'player_assists': 'Assists',
    'player_threes': '3-Pointers Made',
    'player_blocks': 'Blocks',
    'player_steals': 'Steals'
  };

  const [games, setGames] = useState<Game[]>([]);
  const [gameAnalysis, setGameAnalysis] = useState<any[]>([]);
  const [propAnalysis, setPropAnalysis] = useState<any[]>([]);
  const [topInsight, setTopInsight] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingGames, setLoadingGames] = useState(true);
  const [loadingGameAnalysis, setLoadingGameAnalysis] = useState(true);
  const [loadingPropAnalysis, setLoadingPropAnalysis] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'games' | 'game-analysis' | 'prop-analysis' | 'player-props' | 'system-models' | 'my-models' | 'benny-dashboard' | 'model-comparison'>('games');
  const [currentPage, setCurrentPage] = useState(1);
  const [propAnalysisPage, setPropAnalysisPage] = useState(1);
  const [gameAnalysisPage, setGameAnalysisPage] = useState(1);
  const itemsPerPage = 20;
  const [marketFilter, setMarketFilter] = useState<string>('all');
  const [gameAnalysisSort, setGameAnalysisSort] = useState<'confidence' | 'time'>('confidence');
  const [gameAnalysisSortDir, setGameAnalysisSortDir] = useState<'asc' | 'desc'>('desc');
  const [propAnalysisSort, setPropAnalysisSort] = useState<'confidence' | 'time'>('confidence');
  const [propAnalysisSortDir, setPropAnalysisSortDir] = useState<'asc' | 'desc'>('desc');
  const [teamFilter, setTeamFilter] = useState<string>('');
  const [playerFilter, setPlayerFilter] = useState<string>('');
  const [gamesSort, setGamesSort] = useState<'time' | 'team'>('time');
  const [gamesSortDir, setGamesSortDir] = useState<'asc' | 'desc'>('asc');
  const [token, setToken] = useState<string>('');
  const [settings, setSettings] = useState({
    sport: 'basketball_nba',
    bookmaker: 'fanduel',
    model: 'consensus'
  });
  const [gameAnalysisKey, setGameAnalysisKey] = useState<string | null>(null);
  const [propAnalysisKey, setPropAnalysisKey] = useState<string | null>(null);
  const [loadingMoreGame, setLoadingMoreGame] = useState(false);
  const [loadingMoreProp, setLoadingMoreProp] = useState(false);
  const [gamesKey, setGamesKey] = useState<string | null>(null);
  const [loadingMoreGames, setLoadingMoreGames] = useState(false);
  const [modelLeaderboard, setModelLeaderboard] = useState<any[]>([]);
  const [userModels, setUserModels] = useState<any[]>([]);
  const [userId, setUserId] = useState<string>('');

  useEffect(() => {
    const initializeData = async () => {
      try {
        const session = await fetchAuthSession();
        const idToken = session.tokens?.idToken?.toString();
        if (idToken) {
          setToken(idToken);
          // Extract user ID from JWT token payload
          const payload = JSON.parse(atob(idToken.split('.')[1]));
          setUserId(payload.sub || 'unknown');
          // Only fetch data after token is set
          fetchGames();
          fetchGameAnalysis();
          fetchPropAnalysis();
        }
      } catch (error) {
        console.error('Error getting auth session:', error);
      }
    };
    
    initializeData();
  }, []);

  // Fetch user models
  useEffect(() => {
    const fetchUserModels = async () => {
      if (token) {
        try {
          const response = await bettingApi.getUserModels(token, userId);
          setUserModels(response.models || []);
        } catch (error) {
          console.error('Error fetching user models:', error);
        }
      }
    };
    fetchUserModels();
  }, [token, userId]);

  // Refetch data when settings change
  useEffect(() => {
    if (token) {
      fetchGames();
      fetchGameAnalysis();
      fetchPropAnalysis();
    }
  }, [settings, token]);

  const fetchGames = useCallback(async () => {
    try {
      setLoadingGames(true);
      setLoading(true);
      setError(null);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const bookmaker = settings.bookmaker;
        const data = await bettingApi.getGames(token, sport, bookmaker);
        setGames(data.games || []);
        setGamesKey(data.lastEvaluatedKey || null);
      }
    } catch (err: any) {
      const message = err?.message || 'Unable to load games. Please check your connection and try again.';
      setError(message);
      console.error('Error fetching games:', err);
    } finally {
      setLoadingGames(false);
      setLoading(false);
    }
  }, [settings.sport, settings.bookmaker]);


  const fetchGameAnalysis = useCallback(async () => {
    try {
      setLoadingGameAnalysis(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const model = settings.model;
        const bookmaker = settings.bookmaker;
        
        // Check if it's a user model
        if (model.startsWith('user:')) {
          const modelId = model.replace('user:', '');
          const data = await bettingApi.getUserModelPredictions(token, userId);
          // Filter predictions for this specific model and sport, h2h only
          const filtered = (data.predictions || []).filter((p: any) => 
            p.model_id === modelId && 
            p.sport === sport && 
            p.bet_type === 'h2h'
          );
          setGameAnalysis(filtered);
        } else {
          const data = await bettingApi.getAnalyses(token, { sport, model, bookmaker, type: 'game', fetchAll: true });
          setGameAnalysis(data.analyses || []);
        }
        setGameAnalysisKey(null);
      }
    } catch (err) {
      console.error('Error fetching game analysis:', err);
    } finally {
      setLoadingGameAnalysis(false);
    }
  }, [settings.sport, settings.model, settings.bookmaker, userId]);

  const fetchPropAnalysis = useCallback(async () => {
    try {
      setLoadingPropAnalysis(true);
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const sport = settings.sport;
        const model = settings.model;
        const bookmaker = settings.bookmaker;
        
        // Check if it's a user model
        if (model.startsWith('user:')) {
          const modelId = model.replace('user:', '');
          const data = await bettingApi.getUserModelPredictions(token, userId);
          // Filter predictions for this specific model and sport, props only
          const filtered = (data.predictions || []).filter((p: any) => 
            p.model_id === modelId && 
            p.sport === sport && 
            p.bet_type !== 'h2h'
          );
          setPropAnalysis(filtered);
        } else {
          const data = await bettingApi.getAnalyses(token, { sport, model, bookmaker, type: 'prop', fetchAll: true });
          setPropAnalysis(data.analyses || []);
        }
        setPropAnalysisKey(null);
      }
    } catch (err) {
      console.error('Error fetching prop analysis:', err);
    } finally {
      setLoadingPropAnalysis(false);
    }
  }, [settings.sport, settings.model, settings.bookmaker, userId]);

  const fetchTopAnalysis = useCallback(async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        const data = await bettingApi.getTopAnalysis(token, { 
          sport: settings.sport, 
          bookmaker: settings.bookmaker 
        });
        setTopInsight(data.top_analysis);
      }
    } catch (err) {
      console.error('Error fetching top analysis:', err);
    }
  }, [settings.sport, settings.bookmaker]);

  const fetchModelLeaderboard = useCallback(async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (token) {
        // Fetch ROI rankings instead of just accuracy
        const response = await fetch(
          `${process.env.REACT_APP_API_BASE_URL}/model-rankings?sport=${settings.sport}&days=30&mode=both`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        
        if (!response.ok) {
          console.error('Model rankings API error:', response.status, await response.text());
          return;
        }
        
        const data = await response.json();
        console.log('Model rankings data:', data);
        
        // Show top 5 by ROI (include negative ROI too)
        const topByROI = (data.rankings || [])
          .sort((a: any, b: any) => b.roi - a.roi)
          .slice(0, 5);
        
        console.log('Top 5 by ROI:', topByROI);
        setModelLeaderboard(topByROI);
      }
    } catch (err) {
      console.error('Error fetching model leaderboard:', err);
    }
  }, [settings.sport]);

  useEffect(() => {
    if (token) {
      fetchTopAnalysis();
      fetchModelLeaderboard();
    }
  }, [token, settings.sport, fetchTopAnalysis, fetchModelLeaderboard]);

  // Games are already grouped by game_id from the API
  let filteredGames = games.filter(game => {
    // Skip games with invalid team names
    if (!game.home_team || !game.away_team || game.home_team.trim() === '' || game.away_team.trim() === '') {
      return false;
    }
    return true;
  });

  // Apply sport and bookmaker filters
  filteredGames = filteredGames.filter(game => 
    game.sport === settings.sport && 
    Object.keys(game.odds || {}).includes(settings.bookmaker)
  );

  // Get unique sports and bookmakers for filter options (keeping for potential future use)
  // const uniqueSports = Array.from(new Set(games.map(game => game.sport).filter(Boolean)));
  // const uniqueBookmakers = Array.from(new Set(
  //   games.flatMap(game => Object.keys(game.odds || {}))
  // ));


  const formatSport = (sport: string) => {
    if (!sport) return 'UNKNOWN';
    return sport.replace('americanfootball_', '').toUpperCase();
  };

  // Separate game and prop analysis using new schema
  const filteredGameAnalysis = gameAnalysis.filter((a: any) => 
    a.analysis_type === 'game' && a.home_team && a.away_team
  );
  const filteredPropAnalysis = propAnalysis.filter((p: any) => 
    p.player_name && p.prediction
  );

  // Pagination logic
  const paginateItems = (items: any[], page: number) => {
    const startIndex = (page - 1) * itemsPerPage;
    return items.slice(startIndex, startIndex + itemsPerPage);
  };

  const getTotalPages = (items: any[]) => Math.ceil(items.length / itemsPerPage);

  // Reset to page 1 when switching tabs
  const handleTabChange = (tab: typeof activeTab) => {
    setActiveTab(tab);
    setCurrentPage(1);
  };

  // Generate all game cards for pagination
  const generateGameCards = () => {
    const result = games.map((game) => {
      const availableBookmakers = Object.keys(game.odds || {});
      
      const displayBookmakers = availableBookmakers.filter(bookmaker => bookmaker === settings.bookmaker);
      
      if (displayBookmakers.length === 0) return null;

      // Collect all bet types data for this game
      const allMarkets = ['h2h', 'spreads', 'totals'] as const;
      const marketsToShow = marketFilter === 'all' ? allMarkets : [marketFilter as any];
      
      const gameMarkets: any = {};
      marketsToShow.forEach(market => {
        const bookmakerOdds = displayBookmakers
          .map(bookmaker => ({ name: bookmaker, odds: game.odds[bookmaker]?.[market] }))
          .filter(item => item.odds);
        
        if (bookmakerOdds.length > 0) {
          gameMarkets[market] = bookmakerOdds;
        }
      });

      // Only return if we have at least one market with data
      if (Object.keys(gameMarkets).length === 0) return null;

      return { game, markets: gameMarkets, key: game.game_id };
    }).filter(Boolean);
    
    return result;
  };

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : `${odds}`;
  };

  if (loading) return <div className="loading">Loading games...</div>;
  if (error) return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '50vh',
      padding: '2rem',
      textAlign: 'center'
    }}>
      <div style={{
        background: 'rgba(255, 107, 107, 0.1)',
        border: '1px solid rgba(255, 107, 107, 0.3)',
        borderRadius: '12px',
        padding: '2rem',
        maxWidth: '500px'
      }}>
        <h2 style={{ color: '#ff6b6b', marginBottom: '1rem' }}>Unable to Load Data</h2>
        <p style={{ color: '#e2e8f0', marginBottom: '1.5rem' }}>{error}</p>
        <button 
          onClick={() => {
            setError(null);
            fetchGames();
            fetchGameAnalysis();
            fetchPropAnalysis();
          }}
          className="btn btn-primary"
        >
          Try Again
        </button>
      </div>
    </div>
  );

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-left">
          <img src={logo} alt="Carpool Bets" className="logo" />
          <div className="header-info">
            <span>Welcome, {user?.signInDetails?.loginId}</span>
          </div>
        </div>
        
        <div className="header-actions">
          <a 
            href="/about" 
            className="btn btn-secondary"
            style={{ textDecoration: 'none', display: 'inline-block' }}
          >
            About
          </a>
          <button className="btn btn-primary" onClick={signOut}>
            Sign Out
          </button>
        </div>
      </header>
      
      {(topInsight || modelLeaderboard.length > 0) && (
        <div className="ticker-bar">
          <div className="ticker-content">
            {topInsight && (
              <>
                <div className="ticker-item ticker-label">TOP ANALYSIS:</div>
                <div className="ticker-item">
                  🎯 {topInsight.prediction} • {(topInsight.confidence * 100).toFixed(0)}% confidence • {topInsight.model}
                </div>
              </>
            )}
            {modelLeaderboard.length > 0 && (
              <>
                <div className="ticker-item ticker-label">
                  💰 TOP PROFITABLE ({settings.sport.split('_').pop()?.toUpperCase()}):
                </div>
                {modelLeaderboard.map((model: any, index: number) => (
                  <div key={model.model_id} className="ticker-item">
                    🏆 #{index + 1} {model.model} ({model.mode}): {(model.roi * 100).toFixed(1)}% ROI • {model.profit > 0 ? '+' : ''}${model.profit.toFixed(0)} profit
                  </div>
                ))}
              </>
            )}
            {topInsight && (
              <>
                <div className="ticker-item ticker-label">TOP ANALYSIS:</div>
                <div className="ticker-item">
                  🎯 {topInsight.prediction} • {(topInsight.confidence * 100).toFixed(0)}% confidence • {topInsight.model}
                </div>
              </>
            )}
            {modelLeaderboard.length > 0 && (
              <>
                <div className="ticker-item ticker-label">
                  💰 TOP PROFITABLE ({settings.sport.split('_').pop()?.toUpperCase()}):
                </div>
                {modelLeaderboard.map((model: any, index: number) => (
                  <div key={`dup-${model.model_id}`} className="ticker-item">
                    🏆 #{index + 1} {model.model} ({model.mode}): {(model.roi * 100).toFixed(1)}% ROI • {model.profit > 0 ? '+' : ''}${model.profit.toFixed(0)} profit
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}
      
      
      <Settings 
        settings={settings}
        onSettingsChange={setSettings}
        availableSports={['basketball_nba', 'americanfootball_nfl', 'baseball_mlb', 'icehockey_nhl', 'soccer_epl']}
        availableBookmakers={['draftkings', 'fanduel', 'betmgm', 'caesars']}
        userModels={userModels}
        token={token}
      />
      
      <main>
        <nav className="tab-navigation" role="tablist" aria-label="Main navigation">
          <button 
            role="tab"
            aria-selected={activeTab === 'games'}
            aria-controls="games-panel"
            className={`tab-button ${activeTab === 'games' ? 'active' : ''}`}
            onClick={() => handleTabChange('games')}
          >
            Game Bets
          </button>
          <button 
            role="tab"
            aria-selected={activeTab === 'player-props'}
            aria-controls="player-props-panel"
            className={`tab-button ${activeTab === 'player-props' ? 'active' : ''}`}
            onClick={() => handleTabChange('player-props')}
          >
            Prop Bets
          </button>
          <button 
            role="tab"
            aria-selected={activeTab === 'game-analysis'}
            aria-controls="game-analysis-panel"
            className={`tab-button ${activeTab === 'game-analysis' ? 'active' : ''}`}
            onClick={() => handleTabChange('game-analysis')}
          >
            Game Analysis
          </button>
          <button 
            role="tab"
            aria-selected={activeTab === 'prop-analysis'}
            aria-controls="prop-analysis-panel"
            className={`tab-button ${activeTab === 'prop-analysis' ? 'active' : ''}`}
            onClick={() => handleTabChange('prop-analysis')}
          >
            Prop Analysis
          </button>
          <button 
            role="tab"
            aria-selected={activeTab === 'system-models'}
            aria-controls="system-models-panel"
            className={`tab-button ${activeTab === 'system-models' ? 'active' : ''}`}
            onClick={() => handleTabChange('system-models')}
          >
            System Models
          </button>
          <button 
            role="tab"
            aria-selected={activeTab === 'my-models'}
            aria-controls="my-models-panel"
            className={`tab-button ${activeTab === 'my-models' ? 'active' : ''}`}
            onClick={() => handleTabChange('my-models')}
          >
            My Models
          </button>
          <button 
            role="tab"
            aria-selected={activeTab === 'benny-dashboard'}
            aria-controls="benny-dashboard-panel"
            className={`tab-button ${activeTab === 'benny-dashboard' ? 'active' : ''}`}
            onClick={() => handleTabChange('benny-dashboard')}
          >
            🤖 Benny
          </button>
          <button 
            role="tab"
            aria-selected={activeTab === 'model-comparison'}
            aria-controls="model-comparison-panel"
            className={`tab-button ${activeTab === 'model-comparison' ? 'active' : ''}`}
            onClick={() => handleTabChange('model-comparison')}
          >
            📊 Model Comparison
          </button>
        </nav>

        {activeTab === 'games' && (
          <div role="tabpanel" id="games-panel" aria-labelledby="games-tab">
            <div className="games-header">
              <h2>Available Games</h2>
              <div className="filters">
                <input
                  type="text"
                  placeholder="Filter by team..."
                  aria-label="Filter games by team name"
                  value={teamFilter}
                  onChange={(e) => setTeamFilter(e.target.value)}
                  className="filter-select"
                />
                <select 
                  className="filter-select"
                  aria-label="Filter by bet type"
                  value={marketFilter} 
                  onChange={(e) => setMarketFilter(e.target.value)}
                >
                  <option key="all-markets" value="all">All Bet Types</option>
                  <option key="h2h" value="h2h">Moneyline</option>
                  <option key="spreads" value="spreads">Spread</option>
                  <option key="totals" value="totals">Total</option>
                </select>
                <select 
                  className="filter-select"
                  aria-label="Sort games by"
                  value={gamesSort} 
                  onChange={(e) => setGamesSort(e.target.value as 'time' | 'team')}
                >
                  <option value="time">Sort by Time</option>
                  <option value="team">Sort by Team</option>
                </select>
                <select 
                  className="filter-select"
                  value={gamesSortDir} 
                  onChange={(e) => setGamesSortDir(e.target.value as 'asc' | 'desc')}
                >
                  <option value="asc">Ascending</option>
                  <option value="desc">Descending</option>
                </select>
              </div>
            </div>
            
            {loadingGames ? (
              <GamesGridSkeleton count={6} />
            ) : (
            <div className="games-grid">
              {(() => {
                const allGameCards = generateGameCards();
                return allGameCards
                  .filter((cardData: any) => {
                    if (!teamFilter) return true;
                    const filter = teamFilter.toLowerCase();
                    return cardData.game.home_team?.toLowerCase().includes(filter) || 
                           cardData.game.away_team?.toLowerCase().includes(filter);
                  })
                  .sort((a: any, b: any) => {
                    let comparison = 0;
                    if (gamesSort === 'time') {
                      comparison = new Date(a.game.commence_time).getTime() - new Date(b.game.commence_time).getTime();
                    } else {
                      comparison = a.game.home_team.localeCompare(b.game.home_team);
                    }
                    return gamesSortDir === 'desc' ? -comparison : comparison;
                  })
                  .map((cardData: any) => {
                  const { game, markets, key } = cardData;
                  const marketLabels: Record<string, string> = { h2h: 'Moneyline', spreads: 'Spread', totals: 'Total' };
                  
                  return (
                    <div key={key} className="game-card">
                      <div className="game-header">
                        <div className="teams">
                          <h3>{game.away_team} @ {game.home_team}</h3>
                          <div className="sport-tag">{formatSport(game.sport)}</div>
                          <p className="game-time">{new Date(game.commence_time).toLocaleString()}</p>
                        </div>
                      </div>
                      
                      {Object.entries(markets).map(([market, bookmakerOdds]: [string, any]) => (
                        <div key={market} className="odds-section">
                          <div className="odds-header">
                            <span className="odds-label">{marketLabels[market]} Odds</span>
                          </div>
                          <div className="bookmaker-odds">
                            {bookmakerOdds.map((bookmaker: any) => (
                              <div key={`${game.game_id}-${bookmaker.name}-${market}`} className="bookmaker-row">
                                <div className="odds-values">
                                  {bookmaker.odds?.map((outcome: any) => (
                                    <span key={outcome.name} className={`odds-value ${outcome.name === game.home_team ? 'home' : 'away'}`}>
                                      {outcome.name}: {formatOdds(outcome.price)}
                                      {outcome.point && ` (${outcome.point > 0 ? '+' : ''}${outcome.point})`}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                });
              })()}
            </div>
            )}
            
            {!loadingGames && games.length === 0 && (
              <div className="no-data">No games found for current filters</div>
            )}
          </div>
        )}

        {activeTab === 'game-analysis' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>Game Analysis</h2>
              <div className="filters">
                <input
                  type="text"
                  placeholder="Filter by team..."
                  value={teamFilter}
                  onChange={(e) => setTeamFilter(e.target.value)}
                  className="filter-select"
                />
                <select 
                  className="filter-select"
                  value={gameAnalysisSort} 
                  onChange={(e) => setGameAnalysisSort(e.target.value as 'confidence' | 'time')}
                >
                  <option value="confidence">Sort by Confidence</option>
                  <option value="time">Sort by Time</option>
                </select>
                <select 
                  className="filter-select"
                  value={gameAnalysisSortDir} 
                  onChange={(e) => setGameAnalysisSortDir(e.target.value as 'asc' | 'desc')}
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
            </div>
            {loadingGameAnalysis ? (
              <AnalysisGridSkeleton count={4} />
            ) : (
              <>
                <div className="games-grid">
                  {gameAnalysis.length > 0 ? (
                    gameAnalysis
                      .filter((analysis: any) => {
                        if (!teamFilter) return true;
                        const filter = teamFilter.toLowerCase();
                        return analysis.home_team?.toLowerCase().includes(filter) || 
                               analysis.away_team?.toLowerCase().includes(filter);
                      })
                      .sort((a: any, b: any) => {
                        let comparison = 0;
                        if (gameAnalysisSort === 'confidence') {
                          comparison = b.confidence - a.confidence;
                        } else {
                          comparison = new Date(b.commence_time).getTime() - new Date(a.commence_time).getTime();
                        }
                        return gameAnalysisSortDir === 'asc' ? -comparison : comparison;
                      })
                      .slice((gameAnalysisPage - 1) * itemsPerPage, gameAnalysisPage * itemsPerPage)
                      .map((analysis: any, index: number) => (
                        <div key={index} className="game-card">
                          <div className="game-info">
                            <div className="teams">
                              <h3>{analysis.away_team} @ {analysis.home_team}</h3>
                              <div className="sport-tag">{formatSport(analysis.sport)}</div>
                            </div>
                          </div>
                          <div className="analysis-info">
                            <div className="analysis-row">
                              <span className="analysis-label">Analysis Outcome: </span>
                              <span className="analysis-value">{analysis.prediction}</span>
                            </div>
                            <div className="confidence-row">
                              <span className="confidence-label">Confidence: </span>
                              <span className="confidence-value">{(analysis.confidence * 100).toFixed(0)}%</span>
                            </div>
                            <div className="reasoning">
                              <span className="reasoning-label">Reasoning: </span>
                              <span className="reasoning-value">{analysis.reasoning}</span>
                            </div>
                          </div>
                          <div className="game-meta">
                            <span className="model">Model: {analysis.model}</span>
                            <span className="game-time">{new Date(analysis.commence_time).toLocaleString()}</span>
                          </div>
                        </div>
                      ))
                  ) : null}
                </div>
                
                {gameAnalysis.length > itemsPerPage && (
                  <div style={{ textAlign: 'center', marginTop: '20px', display: 'flex', gap: '10px', justifyContent: 'center', alignItems: 'center' }}>
                    <button 
                      onClick={() => setGameAnalysisPage(p => Math.max(1, p - 1))} 
                      disabled={gameAnalysisPage === 1}
                      style={{ padding: '8px 16px', cursor: gameAnalysisPage === 1 ? 'not-allowed' : 'pointer' }}
                    >
                      Previous
                    </button>
                    <span>Page {gameAnalysisPage} of {Math.ceil(gameAnalysis.length / itemsPerPage)} ({gameAnalysis.length} analyses)</span>
                    <button 
                      onClick={() => setGameAnalysisPage(p => Math.min(Math.ceil(gameAnalysis.length / itemsPerPage), p + 1))} 
                      disabled={gameAnalysisPage === Math.ceil(gameAnalysis.length / itemsPerPage)}
                      style={{ padding: '8px 16px', cursor: gameAnalysisPage === Math.ceil(gameAnalysis.length / itemsPerPage) ? 'not-allowed' : 'pointer' }}
                    >
                      Next
                    </button>
                  </div>
                )}
                
                {gameAnalysis.length === 0 && (
                  <div className="no-data">No game analysis items found for current filters</div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'prop-analysis' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>Player Prop Analysis</h2>
              <div className="filters">
                <input
                  type="text"
                  placeholder="Filter by player..."
                  value={playerFilter}
                  onChange={(e) => setPlayerFilter(e.target.value)}
                  className="filter-select"
                />
                <select 
                  className="filter-select"
                  value={marketFilter} 
                  onChange={(e) => setMarketFilter(e.target.value)}
                >
                  <option value="all">All Prop Types</option>
                  {settings.sport === 'basketball_nba' && (
                    <>
                      <option value="player_points">Points</option>
                      <option value="player_rebounds">Rebounds</option>
                      <option value="player_assists">Assists</option>
                    </>
                  )}
                  {settings.sport === 'americanfootball_nfl' && (
                    <>
                      <option value="player_pass_tds">Passing TDs</option>
                      <option value="player_pass_yds">Passing Yards</option>
                      <option value="player_rush_yds">Rushing Yards</option>
                      <option value="player_receptions">Receptions</option>
                      <option value="player_reception_yds">Receiving Yards</option>
                    </>
                  )}
                </select>
                <select 
                  className="filter-select"
                  value={propAnalysisSort} 
                  onChange={(e) => setPropAnalysisSort(e.target.value as 'confidence' | 'time')}
                >
                  <option value="confidence">Sort by Confidence</option>
                  <option value="time">Sort by Time</option>
                </select>
                <select 
                  className="filter-select"
                  value={propAnalysisSortDir} 
                  onChange={(e) => setPropAnalysisSortDir(e.target.value as 'asc' | 'desc')}
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
            </div>
            {loadingPropAnalysis ? (
              <AnalysisGridSkeleton count={4} />
            ) : (
              <>
                <div className="games-grid">
                  {propAnalysis.length > 0 ? (
                    propAnalysis
                      .filter((analysis: any) => {
                        if (marketFilter !== 'all' && analysis.market_key !== marketFilter) return false;
                        if (!playerFilter) return true;
                        return analysis.player_name?.toLowerCase().includes(playerFilter.toLowerCase());
                      })
                      .sort((a: any, b: any) => {
                        let comparison = 0;
                        if (propAnalysisSort === 'confidence') {
                          comparison = b.confidence - a.confidence;
                        } else {
                          comparison = new Date(b.commence_time).getTime() - new Date(a.commence_time).getTime();
                        }
                        return propAnalysisSortDir === 'asc' ? -comparison : comparison;
                      })
                      .slice((propAnalysisPage - 1) * itemsPerPage, propAnalysisPage * itemsPerPage)
                      .map((analysis: any, index: number) => (
                        <div key={index} className="game-card">
                          <div className="game-info">
                            <div className="teams">
                              <h3>{analysis.player_name}{analysis.market_key ? ` - ${propTypeLabels[analysis.market_key] || analysis.market_key}` : ''}</h3>
                              <div className="sport-tag">{formatSport(analysis.sport)}</div>
                              <p className="game-time">{new Date(analysis.commence_time).toLocaleString()}</p>
                            </div>
                          </div>
                          <div className="prediction-info">
                            <div className="prediction-box">
                              <span className="prediction-label">Analysis Outcome: </span>
                              <span className="prediction-value">{analysis.prediction}</span>
                            </div>
                            <div className="confidence">
                              <span className="confidence-label">Confidence</span>
                              <span className="confidence-value">{(analysis.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                          <div className="reasoning">
                            <span className="reasoning-label">Reasoning: </span>
                            <span>{analysis.reasoning}</span>
                          </div>
                          <div className="game-meta">
                            <span className="model">Model: {analysis.model}</span>
                            <span className="game-time">{new Date(analysis.commence_time).toLocaleString()}</span>
                          </div>
                        </div>
                      ))
                  ) : null}
                </div>
                
                {propAnalysis.length > itemsPerPage && (
                  <div style={{ textAlign: 'center', marginTop: '20px', display: 'flex', gap: '10px', justifyContent: 'center', alignItems: 'center' }}>
                    <button 
                      onClick={() => setPropAnalysisPage(p => Math.max(1, p - 1))} 
                      disabled={propAnalysisPage === 1}
                      style={{ padding: '8px 16px', cursor: propAnalysisPage === 1 ? 'not-allowed' : 'pointer' }}
                    >
                  Previous
                </button>
                <span>Page {propAnalysisPage} of {Math.ceil(propAnalysis.length / itemsPerPage)} ({propAnalysis.length} analyses)</span>
                <button 
                  onClick={() => setPropAnalysisPage(p => Math.min(Math.ceil(propAnalysis.length / itemsPerPage), p + 1))} 
                  disabled={propAnalysisPage === Math.ceil(propAnalysis.length / itemsPerPage)}
                  style={{ padding: '8px 16px', cursor: propAnalysisPage === Math.ceil(propAnalysis.length / itemsPerPage) ? 'not-allowed' : 'pointer' }}
                >
                  Next
                </button>
              </div>
            )}
            
            {propAnalysis.length === 0 && (
              <div className="no-data">No prop analysis items found for current filters</div>
            )}
              </>
            )}
          </div>
        )}

        {activeTab === 'player-props' && (
          <PlayerProps 
            token={token} 
            games={games}
            currentPage={currentPage}
            itemsPerPage={itemsPerPage}
            onPageChange={setCurrentPage}
            settings={settings}
          />
        )}

        {activeTab === 'system-models' && (
          <Models token={token} settings={settings} />
        )}

        {activeTab === 'my-models' && (
          <UserModels token={token} />
        )}

        {activeTab === 'benny-dashboard' && (
          <BennyDashboard />
        )}

        {activeTab === 'model-comparison' && (
          <ModelComparison />
        )}
      </main>
      
      {/* Benny - AI Assistant */}
      <Benny userId={user?.username || user?.signInDetails?.loginId || 'anonymous'} />
    </div>
  );
}

function App() {
  // Simple routing based on URL path
  const path = window.location.pathname;
  
  // Check if we're in production (based on environment variable)
  const isProduction = process.env.REACT_APP_STAGE === 'prod';
  
  // About page (converted from landing page)
  if (path === '/about') {
    return <LandingPage />;
  }
  
  if (path === '/terms') {
    return <TermsOfService />;
  }
  
  if (path === '/privacy') {
    return <PrivacyPolicy />;
  }
  
  if (path === '/responsible-gambling') {
    return <ResponsibleGamblingPage />;
  }
  
  // Block app access in production
  if (isProduction) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        color: 'white',
        textAlign: 'center',
        padding: '20px'
      }}>
        <div>
          <h1 style={{ fontSize: '3rem', marginBottom: '20px', color: '#667eea' }}>🚧 Coming Soon</h1>
          <p style={{ fontSize: '1.5rem', marginBottom: '30px' }}>The app is currently in private beta.</p>
          <a href="/" style={{
            display: 'inline-block',
            padding: '15px 40px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '50px',
            fontSize: '1.1rem',
            fontWeight: '600'
          }}>
            ← Back to Home
          </a>
        </div>
      </div>
    );
  }
  
  // App requires authentication (beta only)
  return (
    <Authenticator
      hideSignUp={true}
      loginMechanisms={['email']}
      components={{
        Header() {
          return (
            <img 
              src={logo} 
              alt="Carpool Bets" 
              style={{ 
                height: '160px',
                filter: 'drop-shadow(0 4px 16px rgba(0, 212, 255, 0.3))',
                opacity: '0.95',
                display: 'block',
                margin: '3rem auto 2rem'
              }} 
            />
          );
        },
        Footer() {
          return (
            <div style={{ textAlign: 'center', marginTop: '2rem', padding: '1rem' }}>
              <a 
                href="/about" 
                style={{ 
                  color: '#00d4ff', 
                  textDecoration: 'none',
                  fontSize: '0.9rem'
                }}
              >
                About Carpool Bets
              </a>
            </div>
          );
        },
      }}
    >
      {({ signOut, user }) => (
        <ComplianceWrapper>
          <Dashboard user={user} signOut={signOut} />
        </ComplianceWrapper>
      )}
    </Authenticator>
  );
}

// Standalone Responsible Gambling page
function ResponsibleGamblingPage() {
  return (
    <div className="legal-page">
      <div className="legal-container">
        <h1>Responsible Gambling</h1>
        
        <section>
          <h2>⚠️ Important Gambling Warnings</h2>
          <ul>
            <li>Gambling can be addictive and harmful</li>
            <li>Never bet more than you can afford to lose</li>
            <li>Set limits on time and money spent gambling</li>
            <li>Don't chase losses with bigger bets</li>
            <li>Gambling is not a way to make money or solve financial problems</li>
          </ul>
        </section>

        <section>
          <h2>Get Help</h2>
          <div style={{ background: 'rgba(74, 158, 255, 0.1)', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
            <h3>National Problem Gambling Helpline</h3>
            <p style={{ fontSize: '2rem', color: '#4a9eff', fontWeight: 'bold', margin: '10px 0' }}>1-800-522-4700</p>
            <p>24/7 confidential support</p>
          </div>
          
          <h3>Additional Resources:</h3>
          <ul>
            <li><a href="https://www.ncpgambling.org" target="_blank" rel="noopener noreferrer">National Council on Problem Gambling</a></li>
            <li><a href="https://www.gamblersanonymous.org" target="_blank" rel="noopener noreferrer">Gamblers Anonymous</a></li>
            <li><a href="https://www.responsiblegambling.org" target="_blank" rel="noopener noreferrer">Responsible Gambling Council</a></li>
          </ul>
        </section>

        <section>
          <h2>Self-Help Tools</h2>
          <p>Consider using these tools to maintain control:</p>
          <ul>
            <li>Set daily, weekly, or monthly spending limits</li>
            <li>Use time limits for gambling sessions</li>
            <li>Take regular breaks from gambling</li>
            <li>Self-exclude from gambling sites if needed</li>
          </ul>
        </section>

        <section>
          <h2>Warning Signs of Problem Gambling</h2>
          <ul>
            <li>Spending more money or time gambling than you can afford</li>
            <li>Having arguments with family or friends about money and gambling</li>
            <li>Losing interest in usual activities or hobbies</li>
            <li>Feeling guilty or anxious about gambling</li>
            <li>Borrowing money or selling possessions to gamble</li>
            <li>Trying unsuccessfully to cut down or stop gambling</li>
          </ul>
        </section>

        <div style={{ textAlign: 'center', marginTop: '40px' }}>
          <a href="/" style={{ color: '#4a9eff', textDecoration: 'none', fontSize: '1.1rem' }}>← Back to Home</a>
        </div>
      </div>
    </div>
  );
}

export default App;
