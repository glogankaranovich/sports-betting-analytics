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
import { Marketplace } from './components/Marketplace';
import { Benny } from './components/Benny';
import { BennyDashboard } from './components/BennyDashboard';
import { Subscription } from './components/Subscription';
import { Profile } from './components/Profile';
import SettingsPage from './components/SettingsPage';
import LandingPage from './components/LandingPage';
import { GamesGridSkeleton, AnalysisGridSkeleton } from './components/SkeletonLoader';
import TermsOfService from './components/TermsOfService';
import PrivacyPolicy from './components/PrivacyPolicy';
import { TopNav } from './components/TopNav';
import { SideNav } from './components/SideNav';
import { Breadcrumbs } from './components/Breadcrumbs';
import { AboutPage } from './components/AboutPage';
import Footer from './components/Footer';
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
  const [activePage, setActivePage] = useState<string>('games');
  const [currentPage, setCurrentPage] = useState(1);
  const [propAnalysisPage, setPropAnalysisPage] = useState(1);
  const [gameAnalysisPage, setGameAnalysisPage] = useState(1);
  const itemsPerPage = 20;
  const [marketFilter, setMarketFilter] = useState<string>('all');
  const [gameAnalysisSort, setGameAnalysisSort] = useState<'confidence' | 'time' | 'roi'>('confidence');
  const [gameAnalysisSortDir, setGameAnalysisSortDir] = useState<'asc' | 'desc'>('desc');
  const [propAnalysisSort, setPropAnalysisSort] = useState<'confidence' | 'time' | 'roi'>('confidence');
  const [propAnalysisSortDir, setPropAnalysisSortDir] = useState<'asc' | 'desc'>('desc');
  const [riskFilter, setRiskFilter] = useState<'all' | 'conservative' | 'moderate' | 'aggressive'>('all');
  const [showGameAnalysisFilters, setShowGameAnalysisFilters] = useState(false);
  const [showGameAnalysisSort, setShowGameAnalysisSort] = useState(false);
  const [showPropAnalysisFilters, setShowPropAnalysisFilters] = useState(false);
  const [showPropAnalysisSort, setShowPropAnalysisSort] = useState(false);
  const [teamFilter, setTeamFilter] = useState<string>('');
  const [playerFilter, setPlayerFilter] = useState<string>('');
  const [gamesSort, setGamesSort] = useState<'time' | 'team'>('time');
  const [gamesSortDir, setGamesSortDir] = useState<'asc' | 'desc'>('asc');
  const [showFilters, setShowFilters] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [predictionTypeFilter, setPredictionTypeFilter] = useState<'all' | 'original' | 'inverse'>('all');
  const [showSort, setShowSort] = useState(false);
  const [token, setToken] = useState<string>('');
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('userSettings');
    return saved ? JSON.parse(saved) : {
      sport: 'basketball_nba',
      bookmaker: 'fanduel',
      model: 'consensus'
    };
  });

  // Save settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('userSettings', JSON.stringify(settings));
  }, [settings]);
  const [gameAnalysisKey, setGameAnalysisKey] = useState<string | null>(null);
  const [propAnalysisKey, setPropAnalysisKey] = useState<string | null>(null);
  const [loadingMoreGame, setLoadingMoreGame] = useState(false);
  const [loadingMoreProp, setLoadingMoreProp] = useState(false);
  const [gamesKey, setGamesKey] = useState<string | null>(null);
  const [loadingMoreGames, setLoadingMoreGames] = useState(false);
  const [modelLeaderboard, setModelLeaderboard] = useState<any[]>([]);
  const [userModels, setUserModels] = useState<any[]>([]);
  const [sideNavCollapsed, setSideNavCollapsed] = useState(() => {
    const saved = localStorage.getItem('sideNavCollapsed');
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    localStorage.setItem('sideNavCollapsed', JSON.stringify(sideNavCollapsed));
  }, [sideNavCollapsed]);
  
  const [userId, setUserId] = useState<string>('');
  const [subscription, setSubscription] = useState<any>(null);

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

  // Fetch user models (only if subscription allows)
  useEffect(() => {
    const fetchUserModels = async () => {
      if (token && subscription?.limits?.user_models) {
        try {
          const response = await bettingApi.getUserModels(token, userId);
          setUserModels(response.models || []);
        } catch (error) {
          console.error('Error fetching user models:', error);
        }
      }
    };
    fetchUserModels();
  }, [token, userId, subscription]);

  // Fetch subscription
  useEffect(() => {
    const fetchSubscription = async () => {
      if (token && userId) {
        try {
          const response = await fetch(
            `${process.env.REACT_APP_API_URL}/subscription?user_id=${userId}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (response.ok) {
            const data = await response.json();
            setSubscription(data);
          }
        } catch (error) {
          console.error('Error fetching subscription:', error);
        }
      }
    };
    fetchSubscription();
  }, [token, userId]);

  // Reset model to ensemble if current model is not allowed for free tier
  useEffect(() => {
    if (subscription?.limits?.system_models && Array.isArray(subscription.limits.system_models)) {
      const allowedModels = subscription.limits.system_models.map((m: string) => m.toLowerCase());
      if (!allowedModels.includes(settings.model.toLowerCase())) {
        setSettings({ ...settings, model: 'ensemble' });
      }
    }
    // Clear leaderboard for free tier
    if (subscription?.limits?.show_reasoning === false) {
      setModelLeaderboard([]);
    }
  }, [subscription]);

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
          let analyses = data.analyses || [];
          
          // Filter models based on subscription tier
          if (subscription?.limits?.system_models && Array.isArray(subscription.limits.system_models)) {
            // Free tier: only show allowed models (e.g., ["Ensemble"])
            const allowedModels = subscription.limits.system_models.map((m: string) => m.toLowerCase());
            analyses = analyses.filter((a: any) => allowedModels.includes(a.model?.toLowerCase()));
          }
          
          setGameAnalysis(analyses);
        }
        setGameAnalysisKey(null);
      }
    } catch (err) {
      console.error('Error fetching game analysis:', err);
    } finally {
      setLoadingGameAnalysis(false);
    }
  }, [settings.sport, settings.model, settings.bookmaker, userId, subscription]);

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
          let analyses = data.analyses || [];
          
          // Filter models based on subscription tier
          if (subscription?.limits?.system_models && Array.isArray(subscription.limits.system_models)) {
            // Free tier: only show allowed models (e.g., ["Ensemble"])
            const allowedModels = subscription.limits.system_models.map((m: string) => m.toLowerCase());
            analyses = analyses.filter((a: any) => allowedModels.includes(a.model?.toLowerCase()));
          }
          
          setPropAnalysis(analyses);
        }
        setPropAnalysisKey(null);
      }
    } catch (err) {
      console.error('Error fetching prop analysis:', err);
    } finally {
      setLoadingPropAnalysis(false);
    }
  }, [settings.sport, settings.model, settings.bookmaker, userId, subscription]);

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
        // Fetch model comparison data for all sports (uses cache)
        const response = await fetch(
          `${process.env.REACT_APP_API_URL}/model-comparison?sport=all&days=90`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        
        if (!response.ok) {
          console.error('Model comparison API error:', response.status, await response.text());
          return;
        }
        
        const data = await response.json();
        console.log('Model comparison data:', data);
        
        // Separate game and prop performance
        const gamePerformance: any[] = [];
        const propPerformance: any[] = [];
        
        data.models?.forEach((model: any) => {
          const originalAcc = model.original_accuracy * 100;
          const inverseAcc = model.inverse_accuracy * 100;
          const bestAcc = Math.max(originalAcc, inverseAcc);
          
          let strategy = '';
          if (inverseAcc > originalAcc) {
            strategy = `${inverseAcc.toFixed(1)}% when betting AGAINST`;
          } else {
            strategy = `${originalAcc.toFixed(1)}% when FOLLOWING`;
          }
          
          const perf = {
            model_name: model.model,
            sport: model.sport,
            accuracy: bestAcc,
            total: model.sample_size,
            strategy: strategy,
          };
          
          if (model.bet_type === 'game') {
            gamePerformance.push(perf);
          } else if (model.bet_type === 'prop') {
            propPerformance.push(perf);
          }
        });
        
        // Top 10 for each, min 10 predictions, and >50% accuracy
        const topGames = gamePerformance
          .filter(m => m.total >= 10 && m.accuracy > 50)
          .sort((a, b) => b.accuracy - a.accuracy)
          .slice(0, 10);
        
        const topProps = propPerformance
          .filter(m => m.total >= 10 && m.accuracy > 50)
          .sort((a, b) => b.accuracy - a.accuracy)
          .slice(0, 10);
        
        console.log('Top games:', topGames);
        console.log('Top props:', topProps);
        
        setModelLeaderboard([
          { type: 'games', models: topGames },
          { type: 'props', models: topProps },
        ]);
      }
    } catch (err) {
      console.error('Error fetching model leaderboard:', err);
    }
  }, []);

  useEffect(() => {
    if (token && subscription) {
      fetchTopAnalysis();
      fetchModelLeaderboard();
    }
  }, [token, subscription, settings.sport, fetchTopAnalysis, fetchModelLeaderboard]);

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

  // Reset to page 1 when switching pages
  const handlePageChange = (page: string) => {
    setActivePage(page);
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
      <TopNav 
        currentPage={activePage}
        onNavigate={setActivePage}
        onSignOut={signOut}
        logo={logo}
      />
      
      {((topInsight && subscription?.limits?.show_reasoning !== false) || (modelLeaderboard.length > 0 && subscription?.limits?.show_reasoning !== false)) && (
        <div className="ticker-bar">
          <div className="ticker-content">
            {topInsight && subscription?.limits?.show_reasoning !== false && (
              <>
                <div className="ticker-item ticker-label">TOP ANALYSIS:</div>
                <div className="ticker-item">
                  {topInsight.analysis_type === 'prop' && topInsight.player_name ? (
                    <>🎯 {topInsight.player_name} - {propTypeLabels[topInsight.market_key] || topInsight.market_key} - {topInsight.prediction} • {(topInsight.confidence * 100).toFixed(0)}% confidence{topInsight.roi !== null && topInsight.roi !== undefined && <> • {topInsight.roi > 0 ? '+' : ''}{topInsight.roi}% ROI</>} • {topInsight.model}</>
                  ) : (
                    <>🎯 {topInsight.prediction} • {(topInsight.confidence * 100).toFixed(0)}% confidence{topInsight.roi !== null && topInsight.roi !== undefined && <> • {topInsight.roi > 0 ? '+' : ''}{topInsight.roi}% ROI</>} • {topInsight.model}</>
                  )}
                </div>
              </>
            )}
            {modelLeaderboard.length > 0 && subscription?.limits?.show_reasoning !== false && (
              <>
                {modelLeaderboard.map((section: any) => (
                  <React.Fragment key={section.type}>
                    <div className="ticker-item ticker-label">
                      🎯 TOP ACCURATE - {section.type.toUpperCase()} - 90 DAYS:
                    </div>
                    {section.models.length > 0 ? (
                      section.models.map((model: any, index: number) => (
                        <div key={`${section.type}-${model.model_name}-${index}`} className="ticker-item">
                          🏆 #{index + 1} {model.model_name} ({model.sport?.split('_').pop()?.toUpperCase()}): {model.strategy} • {model.total} predictions
                        </div>
                      ))
                    ) : (
                      <div className="ticker-item">
                        ⚠️ No models with &gt;50% accuracy in last 90 days
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </>
            )}
            {topInsight && subscription?.limits?.show_reasoning !== false && (
              <>
                <div className="ticker-item ticker-label">TOP ANALYSIS:</div>
                <div className="ticker-item">
                  {topInsight.analysis_type === 'prop' && topInsight.player_name ? (
                    <>🎯 {topInsight.player_name} - {propTypeLabels[topInsight.market_key] || topInsight.market_key} - {topInsight.prediction} • {(topInsight.confidence * 100).toFixed(0)}% confidence{topInsight.roi !== null && topInsight.roi !== undefined && <> • {topInsight.roi > 0 ? '+' : ''}{topInsight.roi}% ROI</>} • {topInsight.model}</>
                  ) : (
                    <>🎯 {topInsight.prediction} • {(topInsight.confidence * 100).toFixed(0)}% confidence{topInsight.roi !== null && topInsight.roi !== undefined && <> • {topInsight.roi > 0 ? '+' : ''}{topInsight.roi}% ROI</>} • {topInsight.model}</>
                  )}
                </div>
              </>
            )}
            {modelLeaderboard.length > 0 && subscription?.limits?.show_reasoning !== false && (
              <>
                {modelLeaderboard.map((section: any, sectionIndex: number) => (
                  <React.Fragment key={`section-${section.type}-${sectionIndex}`}>
                    <div className="ticker-item ticker-label">
                      🎯 TOP ACCURATE - {section.type.toUpperCase()} - 90 DAYS:
                    </div>
                    {section.models.length > 0 ? (
                      section.models.map((model: any, index: number) => (
                        <div key={`model-${section.type}-${index}`} className="ticker-item">
                          🏆 #{index + 1} {model.model_name} ({model.sport?.split('_').pop()?.toUpperCase()}): {model.strategy} • {model.total} predictions
                        </div>
                      ))
                    ) : (
                      <div className="ticker-item">
                        ⚠️ No models with &gt;50% accuracy in last 90 days
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </>
            )}
          </div>
        </div>
      )}
      
      <div className="app-layout">
        <div className="main-content-wrapper">
          <Breadcrumbs 
            section={activePage.includes('user') || ['profile', 'settings', 'subscription'].includes(activePage) ? 'user-home' : 
                    activePage.includes('analysis') || ['games', 'player-props', 'game-analysis', 'prop-analysis'].includes(activePage) ? 'analysis-home' :
                    activePage.includes('benny') || ['benny-chat', 'benny-dashboard'].includes(activePage) ? 'benny-home' :
                    activePage.includes('models') || ['system-models', 'my-models', 'model-analytics', 'model-comparison'].includes(activePage) ? 'models-home' :
                    activePage === 'about' || ['how-it-works', 'terms', 'privacy'].includes(activePage) ? 'about' : 
                    activePage === 'marketplace' ? 'marketplace' : ''}
            currentPage={activePage}
            onNavigate={setActivePage}
            isCollapsed={sideNavCollapsed}
            onToggleCollapse={() => setSideNavCollapsed(!sideNavCollapsed)}
          />
          <div className="content-with-sidenav">
            {['user-home', 'analysis-home', 'benny-home', 'models-home', 'marketplace', 'about', 'profile', 'settings', 'subscription', 'games', 'player-props', 'game-analysis', 'prop-analysis', 'benny-chat', 'benny-dashboard', 'system-models', 'my-models', 'model-analytics', 'model-comparison', 'how-it-works', 'terms', 'privacy'].includes(activePage) && (
              <SideNav 
                section={activePage.includes('user') || ['profile', 'settings', 'subscription'].includes(activePage) ? 'user-home' : 
                        activePage.includes('analysis') || ['games', 'player-props', 'game-analysis', 'prop-analysis'].includes(activePage) ? 'analysis-home' :
                        activePage.includes('benny') || ['benny-chat', 'benny-dashboard'].includes(activePage) ? 'benny-home' :
                        activePage.includes('models') || ['system-models', 'my-models', 'model-analytics', 'model-comparison'].includes(activePage) ? 'models-home' :
                        activePage === 'marketplace' ? 'marketplace' :
                        activePage === 'about' || ['how-it-works', 'terms', 'privacy'].includes(activePage) ? 'about' : ''}
                currentPage={activePage}
                onNavigate={setActivePage}
                isCollapsed={sideNavCollapsed}
              />
            )}
            <main className="main-content">
          {activePage === 'user-home' && (
            <div className="page-container">
              <h2>User Dashboard</h2>
              <p>Manage your profile, settings, subscription, and custom models.</p>
            </div>
          )}

          {activePage === 'analysis-home' && (
            <div className="page-container">
              <h2>Analysis Dashboard</h2>
              <p>View game bets, prop bets, and detailed analysis.</p>
            </div>
          )}

          {activePage === 'models-home' && (
            <div className="page-container">
              <h2>Models Dashboard</h2>
              <p>Explore system models, analytics, comparisons, and Benny's insights.</p>
            </div>
          )}

          {activePage === 'games' && (
          <div role="tabpanel" id="games-panel" aria-labelledby="games-tab">
            <div className="games-header">
              <h2>Available Games</h2>
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
                  Filter {(teamFilter || marketFilter !== 'all') && <span className="filter-badge">•</span>}
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
                  onSettingsChange={setSettings}
                  availableSports={['basketball_nba', 'americanfootball_nfl', 'baseball_mlb', 'icehockey_nhl', 'soccer_epl']}
                  availableBookmakers={['draftkings', 'fanduel', 'betmgm', 'caesars']}
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
              </div>
            )}
            
            {showSort && (
              <div className="filter-panel">
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
            )}
            
            {loadingGames && games.length === 0 ? (
              <GamesGridSkeleton count={6} />
            ) : (
            <div className={`games-grid ${loadingGames ? 'loading' : ''}`}>
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

        {activePage === 'game-analysis' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>Game Analysis</h2>
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
                  onClick={() => setShowGameAnalysisFilters(!showGameAnalysisFilters)}
                  aria-label="Toggle filters"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ marginRight: '0.5rem' }}>
                    <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5v-2z"/>
                  </svg>
                  Filter {teamFilter && <span className="filter-badge">•</span>}
                </button>
                <button 
                  className="filter-icon-btn"
                  onClick={() => setShowGameAnalysisSort(!showGameAnalysisSort)}
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
                  onSettingsChange={setSettings}
                  availableSports={['basketball_nba', 'americanfootball_nfl', 'baseball_mlb', 'icehockey_nhl', 'soccer_epl']}
                  availableBookmakers={['draftkings', 'fanduel', 'betmgm', 'caesars']}
                  userModels={userModels}
                  token={token}
                  subscription={subscription}
                />
              </div>
            )}
            
            {showGameAnalysisFilters && (
              <div className="filter-panel">
                <input
                  type="text"
                  placeholder="Filter by team..."
                  value={teamFilter}
                  onChange={(e) => setTeamFilter(e.target.value)}
                  className="filter-select"
                />
                <select
                  value={predictionTypeFilter}
                  onChange={(e) => setPredictionTypeFilter(e.target.value as 'all' | 'original' | 'inverse')}
                  className="filter-select"
                >
                  <option value="all">All Predictions</option>
                  <option value="original">Original Only (Betting With Model)</option>
                  <option value="inverse">Inverse Only (Betting Against Model)</option>
                </select>
                <select
                  value={riskFilter}
                  onChange={(e) => setRiskFilter(e.target.value as 'all' | 'conservative' | 'moderate' | 'aggressive')}
                  className="filter-select"
                >
                  <option value="all">All Risk Levels</option>
                  <option value="conservative">Conservative</option>
                  <option value="moderate">Moderate</option>
                  <option value="aggressive">Aggressive</option>
                </select>
              </div>
            )}
            
            {showGameAnalysisSort && (
              <div className="filter-panel">
                <select 
                  className="filter-select"
                  value={gameAnalysisSort} 
                  onChange={(e) => setGameAnalysisSort(e.target.value as 'confidence' | 'time' | 'roi')}
                >
                  <option value="confidence">Sort by Confidence</option>
                  <option value="roi">Sort by ROI</option>
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
            )}
            {loadingGameAnalysis && gameAnalysis.length === 0 ? (
              <AnalysisGridSkeleton count={4} />
            ) : (
              <>
                <div className={`games-grid ${loadingGameAnalysis ? 'loading' : ''}`}>
                  {gameAnalysis.length > 0 ? (
                    gameAnalysis
                      .filter((analysis: any) => {
                        if (teamFilter) {
                          const filter = teamFilter.toLowerCase();
                          const teamMatch = analysis.home_team?.toLowerCase().includes(filter) || 
                                 analysis.away_team?.toLowerCase().includes(filter);
                          if (!teamMatch) return false;
                        }
                        const isInverse = analysis.reasoning?.toLowerCase().includes('inverse');
                        if (predictionTypeFilter === 'inverse' && !isInverse) return false;
                        if (predictionTypeFilter === 'original' && isInverse) return false;
                        if (riskFilter !== 'all' && analysis.risk_level !== riskFilter) return false;
                        return true;
                      })
                      .sort((a: any, b: any) => {
                        let comparison = 0;
                        if (gameAnalysisSort === 'confidence') {
                          comparison = b.confidence - a.confidence;
                        } else if (gameAnalysisSort === 'roi') {
                          comparison = (b.roi || 0) - (a.roi || 0);
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
                            </div>
                          </div>
                          <div className="analysis-info">
                            <div className="analysis-row">
                              <span className="analysis-label">Prediction: </span>
                              <span className="analysis-value">{analysis.prediction}</span>
                            </div>
                            <div className="confidence-row">
                              <span className="confidence-label">Confidence: </span>
                              <span className="confidence-value">{(analysis.confidence * 100).toFixed(0)}%</span>
                              {analysis.roi !== null && analysis.roi !== undefined && (
                                <>
                                  <span className="confidence-label" style={{ marginLeft: '20px' }}>ROI: </span>
                                  <span className={`confidence-value ${analysis.roi > 0 ? 'positive' : 'negative'}`}>
                                    {analysis.roi > 0 ? '+' : ''}{analysis.roi}%
                                  </span>
                                </>
                              )}
                              {analysis.risk_level && (
                                <span className={`risk-badge ${analysis.risk_level}`} style={{ marginLeft: '12px' }}>
                                  {analysis.risk_level}
                                </span>
                              )}
                            </div>
                            {subscription?.limits?.show_reasoning !== false && (
                              <div className="reasoning-section">
                                <div className="reasoning-header">
                                  <span className="reasoning-label">Analysis:</span>
                                </div>
                                <div className="reasoning-content">
                                  {analysis.reasoning}
                                </div>
                              </div>
                            )}
                            {subscription?.limits?.show_reasoning === false && (
                              <div className="reasoning-section" style={{ background: '#1a1a1a', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
                                <div style={{ textAlign: 'center', color: '#888' }}>
                                  <p style={{ margin: '0 0 12px 0' }}>🔒 Upgrade to see detailed analysis</p>
                                  <button 
                                    className="upgrade-btn"
                                    onClick={() => setActivePage('subscription')}
                                    style={{ padding: '8px 16px', fontSize: '14px' }}
                                  >
                                    View Plans
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                          <div className="game-meta">
                            <span className={`prediction-badge ${analysis.reasoning?.toLowerCase().includes('inverse') ? 'against-model' : 'with-model'}`}>
                              {analysis.reasoning?.toLowerCase().includes('inverse') ? 'BETTING AGAINST MODEL' : 'BETTING WITH MODEL'}
                            </span>
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

        {activePage === 'prop-analysis' && (
          <div className="predictions-section">
            <div className="games-header">
              <h2>Player Prop Analysis</h2>
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
                  onClick={() => setShowPropAnalysisFilters(!showPropAnalysisFilters)}
                  aria-label="Toggle filters"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ marginRight: '0.5rem' }}>
                    <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5v-2z"/>
                  </svg>
                  Filter {(playerFilter || marketFilter !== 'all') && <span className="filter-badge">•</span>}
                </button>
                <button 
                  className="filter-icon-btn"
                  onClick={() => setShowPropAnalysisSort(!showPropAnalysisSort)}
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
                  onSettingsChange={setSettings}
                  availableSports={['basketball_nba', 'americanfootball_nfl', 'baseball_mlb', 'icehockey_nhl', 'soccer_epl']}
                  availableBookmakers={['draftkings', 'fanduel', 'betmgm', 'caesars']}
                  userModels={userModels}
                  token={token}
                  subscription={subscription}
                />
              </div>
            )}
            
            {showPropAnalysisFilters && (
              <div className="filter-panel">
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
                  value={riskFilter}
                  onChange={(e) => setRiskFilter(e.target.value as 'all' | 'conservative' | 'moderate' | 'aggressive')}
                  className="filter-select"
                >
                  <option value="all">All Risk Levels</option>
                  <option value="conservative">Conservative</option>
                  <option value="moderate">Moderate</option>
                  <option value="aggressive">Aggressive</option>
                </select>
              </div>
            )}
            
            {showPropAnalysisSort && (
              <div className="filter-panel">
                <select 
                  className="filter-select"
                  value={propAnalysisSort} 
                  onChange={(e) => setPropAnalysisSort(e.target.value as 'confidence' | 'time' | 'roi')}
                >
                  <option value="confidence">Sort by Confidence</option>
                  <option value="roi">Sort by ROI</option>
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
            )}
            {loadingPropAnalysis && propAnalysis.length === 0 ? (
              <AnalysisGridSkeleton count={4} />
            ) : (
              <>
                <div className={`games-grid ${loadingPropAnalysis ? 'loading' : ''}`}>
                  {propAnalysis.length > 0 ? (
                    propAnalysis
                      .filter((analysis: any) => {
                        if (marketFilter !== 'all' && analysis.market_key !== marketFilter) return false;
                        if (playerFilter && !analysis.player_name?.toLowerCase().includes(playerFilter.toLowerCase())) return false;
                        if (riskFilter !== 'all' && analysis.risk_level !== riskFilter) return false;
                        return true;
                      })
                      .sort((a: any, b: any) => {
                        let comparison = 0;
                        if (propAnalysisSort === 'confidence') {
                          comparison = b.confidence - a.confidence;
                        } else if (propAnalysisSort === 'roi') {
                          comparison = (b.roi || 0) - (a.roi || 0);
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
                              <p className="game-time">{new Date(analysis.commence_time).toLocaleString()}</p>
                            </div>
                          </div>
                          <div className="prediction-info">
                            <div className="prediction-box">
                              <span className="prediction-label">Prediction: </span>
                              <span className="prediction-value">{analysis.prediction}</span>
                            </div>
                            <div className="confidence">
                              <span className="confidence-label">Confidence: </span>
                              <span className="confidence-value">{(analysis.confidence * 100).toFixed(0)}%</span>
                              {analysis.roi !== null && analysis.roi !== undefined && (
                                <>
                                  <span className="confidence-label" style={{ marginLeft: '20px' }}>ROI: </span>
                                  <span className={`confidence-value ${analysis.roi > 0 ? 'positive' : 'negative'}`}>
                                    {analysis.roi > 0 ? '+' : ''}{analysis.roi}%
                                  </span>
                                </>
                              )}
                              {analysis.risk_level && (
                                <span className={`risk-badge ${analysis.risk_level}`} style={{ marginLeft: '12px' }}>
                                  {analysis.risk_level}
                                </span>
                              )}
                            </div>
                          </div>
                          {subscription?.limits?.show_reasoning !== false && (
                            <div className="reasoning-section">
                              <div className="reasoning-header">
                                <span className="reasoning-label">Analysis:</span>
                              </div>
                              <div className="reasoning-content">
                                {analysis.reasoning}
                              </div>
                            </div>
                          )}
                          {subscription?.limits?.show_reasoning === false && (
                            <div className="reasoning-section" style={{ background: '#1a1a1a', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
                              <div style={{ textAlign: 'center', color: '#888' }}>
                                <p style={{ margin: '0 0 12px 0' }}>🔒 Upgrade to see detailed analysis</p>
                                <button 
                                  className="upgrade-btn"
                                  onClick={() => setActivePage('subscription')}
                                  style={{ padding: '8px 16px', fontSize: '14px' }}
                                >
                                  View Plans
                                </button>
                              </div>
                            </div>
                          )}
                          <div className="game-meta">
                            <span className={`prediction-badge ${analysis.reasoning?.toLowerCase().includes('inverse') ? 'against-model' : 'with-model'}`}>
                              {analysis.reasoning?.toLowerCase().includes('inverse') ? 'BETTING AGAINST MODEL' : 'BETTING WITH MODEL'}
                            </span>
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

        {activePage === 'player-props' && (
          <>
            <PlayerProps 
              token={token} 
              games={games}
              currentPage={currentPage}
              itemsPerPage={itemsPerPage}
              onPageChange={setCurrentPage}
              settings={settings}
              onSettingsChange={setSettings}
              availableSports={['basketball_nba', 'americanfootball_nfl', 'baseball_mlb', 'icehockey_nhl', 'soccer_epl']}
              availableBookmakers={['draftkings', 'fanduel', 'betmgm', 'caesars']}
              userModels={userModels}
              subscription={subscription}
            />
          </>
        )}

        {activePage === 'profile' && (
          <Profile token={token} userId={userId} user={user} />
        )}

        {activePage === 'subscription' && (
          <Subscription token={token} userId={userId} />
        )}

        {activePage === 'settings' && (
          <SettingsPage settings={settings} onSettingsChange={setSettings} subscription={subscription} />
        )}

        {activePage === 'system-models' && subscription && (
          <Models token={token} settings={settings} subscription={subscription} />
        )}

        {activePage === 'model-analytics' && subscription && (
          <ModelAnalytics token={token} selectedModel={settings.model} />
        )}

        {activePage === 'my-models' && subscription && (
          <UserModels token={token} subscription={subscription} onNavigate={setActivePage} />
        )}

        {activePage === 'marketplace' && subscription && (
          <Marketplace subscription={subscription} onNavigate={setActivePage} />
        )}

        {activePage === 'benny-chat' && (
          <div className="benny-chat-page">
            <div className="benny-chat-container">
              <Benny userId={userId} token={token} isFullPage={true} subscription={subscription} onNavigate={setActivePage} />
            </div>
          </div>
        )}

        {activePage === 'benny-dashboard' && (
          <BennyDashboard subscription={subscription} onNavigate={setActivePage} />
        )}

        {activePage === 'model-comparison' && (
          <ModelComparison settings={settings} subscription={subscription} />
        )}

        {activePage === 'about' && (
          <AboutPage />
        )}

        {activePage === 'how-it-works' && (
          <div className="page-container">
            <h2>How It Works</h2>
            <p>Learn about our betting models and how to use the platform.</p>
          </div>
        )}

        {activePage === 'terms' && (
          <TermsOfService />
        )}

        {activePage === 'privacy' && (
          <PrivacyPolicy />
        )}
            </main>
          </div>
        </div>
      </div>
      
      <Footer />
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
                margin: '1rem auto 0'
              }} 
            />
          );
        },
        Footer() {
          return (
            <div style={{ textAlign: 'center', marginTop: '1rem', padding: '1rem' }}>
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
