import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  TrendingUp, TrendingDown, Activity, DollarSign, 
  BarChart2, Shield, Play, RefreshCw, AlertCircle, Briefcase,
  Lock, LogIn, User, Award, BookOpen, Brain, Zap, LogOut
} from 'lucide-react';
import { 
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, 
  Tooltip, Legend, CartesianGrid, AreaChart, Area, ComposedChart 
} from 'recharts';
import './App.css';

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://127.0.0.1:8000' 
  : 'https://nse-trading-suite.onrender.com';

function App() {
  // Auth states
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // App states
  const [activeTab, setActiveTab] = useState('analysis');
  const [liveSignals, setLiveSignals] = useState([]);
  const [positionsData, setPositionsData] = useState({ capital: 100000, positions: {}, order_history: [] });
  const [indicatorsData, setIndicatorsData] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('RELIANCE.NS');
  
  // Advanced Analysis states
  const [analysisData, setAnalysisData] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [optionChain, setOptionChain] = useState(null);
  const [globalSentiment, setGlobalSentiment] = useState(null);

  // Backtest states
  const [btSymbol, setBtSymbol] = useState('RELIANCE.NS');
  const [btInterval, setBtInterval] = useState('5m');
  const [btStartDate, setBtStartDate] = useState('2026-04-01');
  const [btResults, setBtResults] = useState(null);
  const [btLoading, setBtLoading] = useState(false);

  // --- NEW INTERACTIVE STATES ---
  const [orderSymbol, setOrderSymbol] = useState('RELIANCE.NS');
  const [orderQty, setOrderQty] = useState(10);
  const [orderSide, setOrderSide] = useState('BUY');
  const [orderType, setOrderType] = useState('MARKET');
  const [orderPrice, setOrderPrice] = useState('');
  const [orderLoading, setOrderLoading] = useState(false);
  const [watchlistFilter, setWatchlistFilter] = useState('');
  const [orderFilter, setOrderFilter] = useState('');

  const [chartLines, setChartLines] = useState({
    price: true,
    vwap: true,
    ema_20: true,
    ema_50: true,
    rsi_14: true
  });

  const [expiryTarget, setExpiryTarget] = useState('');
  const [autoTradeEnabled, setAutoTradeEnabled] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/login`, { username, password });
      if (res.data.status === 'success') {
        setIsAuthenticated(true);
        localStorage.setItem('quant_token', res.data.token);
      }
    } catch (e) {
      setLoginError(e.response?.data?.detail || "Login failed. Check server.");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('quant_token');
    setUsername('');
    setPassword('');
  };

  const fetchLiveSignals = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/signals?expiry_target=${expiryTarget}`);
      setLiveSignals(res.data);
    } catch (e) {
      console.error("Error fetching signals", e);
    }
  };

  const fetchPositions = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/positions`);
      setPositionsData(res.data);
    } catch (e) {
      console.error("Error fetching positions", e);
    }
  };

  const fetchAutoTradeStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/autotrade/status`);
      setAutoTradeEnabled(res.data.enabled);
    } catch (e) {
      console.error("Error fetching autotrade status", e);
    }
  };

  const toggleAutoTrade = async () => {
    try {
      const res = await axios.post(`${API_BASE_URL}/api/autotrade/toggle`);
      setAutoTradeEnabled(res.data.enabled);
      alert(res.data.message);
    } catch (e) {
      alert(`Error toggling auto-trade: ${e.response?.data?.detail || e.message}`);
    }
  };

  const fetchIndicators = async (sym) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/indicators?symbol=${sym}`);
      setIndicatorsData(res.data);
    } catch (e) {
      console.error("Error fetching indicators", e);
    }
  };

  const fetchAnalysis = async (sym) => {
    setAnalysisLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/api/analysis?symbol=${sym}`);
      setAnalysisData(res.data);
    } catch (e) {
      console.error("Error fetching advanced analysis", e);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const fetchAdvancedData = async (sym) => {
    try {
      const sentimentRes = await axios.get(`${API_BASE_URL}/api/global_sentiment`);
      setGlobalSentiment(sentimentRes.data);
      const ocRes = await axios.get(`${API_BASE_URL}/api/option_chain?symbol=${sym}&spot_price=0`);
      setOptionChain(ocRes.data);
    } catch (e) {
      console.error("Error fetching advanced data", e);
    }
  };

  const handlePlaceOrder = async (e) => {
    if (e) e.preventDefault();
    setOrderLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/api/orders`, {
        symbol: orderSymbol,
        quantity: parseInt(orderQty),
        side: orderSide,
        order_type: orderType,
        price: orderType === 'LIMIT' ? parseFloat(orderPrice) : null
      });
      fetchPositions();
      alert(`Successfully placed manual ${orderSide} order.`);
    } catch (e) {
      alert(`Manual order failed: ${e.response?.data?.detail || e.message}`);
    } finally {
      setOrderLoading(false);
    }
  };

  const handleQuickOrder = async (side) => {
    try {
      await axios.post(`${API_BASE_URL}/api/orders`, {
        symbol: selectedSymbol,
        quantity: 10,
        side: side,
        order_type: 'MARKET'
      });
      fetchPositions();
      alert(`Instant Market ${side} executed for ${selectedSymbol}`);
    } catch (e) {
      alert(`Execution Error: ${e.response?.data?.detail || e.message}`);
    }
  };

  useEffect(() => {
    const savedToken = localStorage.getItem('quant_token');
    if (savedToken) {
      setIsAuthenticated(true);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;

    fetchLiveSignals();
    fetchPositions();
    fetchIndicators(selectedSymbol);
    fetchAnalysis(selectedSymbol);
    fetchAdvancedData(selectedSymbol);
    fetchAutoTradeStatus();

    const interval = setInterval(() => {
      if (activeTab === 'live' || activeTab === 'analysis') {
        fetchLiveSignals();
        fetchPositions();
        fetchAdvancedData(selectedSymbol);
      }
    }, 15000);

    return () => clearInterval(interval);
  }, [isAuthenticated, activeTab, selectedSymbol, expiryTarget]);

  const handleRunBacktest = async (e) => {
    e.preventDefault();
    setBtLoading(true);
    setBtResults(null);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/backtest`, {
        symbol: btSymbol,
        interval: btInterval,
        start_date: btStartDate,
        capital: positionsData.capital || 100000
      });
      setBtResults(res.data);
    } catch (e) {
      alert("Backtest failed. Check parameters.");
      console.error(e);
    } finally {
      setBtLoading(false);
    }
  };

  const getSignalBadge = (signal) => {
    if (signal === 'BUY') return <span className="signal-badge bg-bullish-glow text-bullish">BUY</span>;
    if (signal === 'SELL') return <span className="signal-badge bg-bearish-glow text-bearish">SELL</span>;
    return <span className="signal-badge" style={{background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)'}}>NEUTRAL</span>;
  };

  const toggleChartLine = (line) => {
    setChartLines(prev => ({ ...prev, [line]: !prev[line] }));
  };

  if (!isAuthenticated) {
    return (
      <div className="login-wrapper">
        <div className="card glass login-card">
          <div className="login-header">
            <div className="login-logo">
              <Shield size={32} className="text-primary" />
            </div>
            <h2>Chandra Quant Login</h2>
            <p>Access algorithmic execution gateways</p>
          </div>
          <form onSubmit={handleLogin}>
            {loginError && <div className="error-banner">{loginError}</div>}
            <div className="form-group">
              <label><User size={14} style={{marginRight: 6, display: 'inline'}} /> Username</label>
              <input 
                type="text" 
                className="form-input" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                placeholder="admin" 
                required 
              />
            </div>
            <div className="form-group">
              <label><Lock size={14} style={{marginRight: 6, display: 'inline'}} /> Password</label>
              <input 
                type="password" 
                className="form-input" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                placeholder="admin" 
                required 
              />
            </div>
            <button type="submit" className="btn-primary" style={{width: '100%', marginTop: 12}} disabled={loginLoading}>
              {loginLoading ? 'Authenticating...' : <><LogIn size={16} style={{marginRight: 8, display: 'inline', verticalAlign: 'middle'}} /> Secure Login</>}
            </button>
          </form>
          <div className="login-footer">
            <p>Protected by end-to-end security gateways.</p>
            <p style={{fontSize: '0.75rem', marginTop: 4, opacity: 0.5}}>(Default credentials: admin / admin)</p>
          </div>
        </div>
      </div>
    );
  }

  const filteredWatchlist = liveSignals.filter(sig => 
    sig.symbol.toLowerCase().includes(watchlistFilter.toLowerCase())
  );

  const filteredOrders = positionsData.order_history?.filter(order => 
    order.symbol.toLowerCase().includes(orderFilter.toLowerCase()) ||
    order.side.toLowerCase().includes(orderFilter.toLowerCase())
  );

  return (
    <div className="app-container">
      <header>
        <div className="logo-section">
          <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
            <Brain size={32} className="text-primary" />
            <div>
              <h1 style={{margin: 0}}>CHANDRA QUANT</h1>
              <p style={{margin: 0}}>NSE Algorithmic Trading Suite</p>
            </div>
          </div>
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
          <div className="tabs-nav">
            <button className={`tab-btn ${activeTab === 'analysis' ? 'active' : ''}`} onClick={() => setActiveTab('analysis')}>
              <Award size={16} style={{marginRight: 6}} /> Analysis
            </button>
            <button className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`} onClick={() => setActiveTab('live')}>
              <Activity size={16} style={{marginRight: 6}} /> Live
            </button>
            <button className={`tab-btn ${activeTab === 'backtest' ? 'active' : ''}`} onClick={() => setActiveTab('backtest')}>
              <Play size={16} style={{marginRight: 6}} /> Backtester
            </button>
          </div>
          <button onClick={handleLogout} className="btn-logout" title="Log Out">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <div className="market-indices-bar">
        {liveSignals.length > 0 ? liveSignals.map((sig, idx) => {
          const changePct = sig.vwap ? ((sig.price - sig.vwap) / sig.vwap * 100) : 0;
          const isPositive = changePct >= 0;
          return (
            <div key={idx} className="index-item">
              <span className="index-symbol">{sig.symbol.replace('^NSEI', 'NIFTY').replace('.NS', '').replace('BSE:', '')}</span>
              <span className="index-price">{sig.price?.toFixed(2) || '---'}</span>
              <span style={{ color: isPositive ? 'var(--bullish)' : 'var(--bearish)' }}>
                {isPositive ? '+' : ''}{changePct.toFixed(2)}%
              </span>
            </div>
          );
        }) : (
          <div className="index-item"><span className="index-symbol">Loading Market Data...</span></div>
        )}
      </div>

      {activeTab === 'live' && (
        <div className="grid-container">
          {/* Summary Cards */}
          <div className="card glass summary-widget hover-scale">
            <div className="widget-title">
              <span>Account Margin</span>
              <DollarSign size={20} className="text-bullish" />
            </div>
            <h2 className="widget-value">₹{positionsData.capital?.toLocaleString(undefined, {maximumFractionDigits: 2})}</h2>
            <p className="widget-subtext">Free execution balance</p>
          </div>

          <div className="card glass summary-widget hover-scale">
            <div className="widget-title">
              <span>Active Signals</span>
              <AlertCircle size={20} style={{color: 'var(--secondary)'}} />
            </div>
            <h2 className="widget-value">{liveSignals.filter(s => s.signal !== 'NEUTRAL').length}</h2>
            <p className="widget-subtext">Actionable opportunities</p>
          </div>

          <div className="card glass summary-widget hover-scale">
            <div className="widget-title">
              <span>Open Positions</span>
              <Briefcase size={20} className="text-primary" />
            </div>
            <h2 className="widget-value">
              {Object.keys(positionsData.positions || {}).filter(k => positionsData.positions[k] !== 0).length}
            </h2>
            <p className="widget-subtext">Active market exposure</p>
          </div>

          <div className="card glass summary-widget hover-scale">
            <div className="widget-title">
              <span>Risk Management</span>
              <Shield size={20} className="text-bullish" />
            </div>
            <h2 className="widget-value" style={{color: 'var(--bullish)'}}>ENABLED</h2>
            <p className="widget-subtext">Trailing StopLoss deployed</p>
          </div>

          {/* Interactive Execution Terminal */}
          <div className="card glass" style={{gridColumn: 'span 4'}}>
            <h3 style={{margin: '0 0 16px 0'}}>Execution Terminal</h3>
            <form onSubmit={handlePlaceOrder}>
              <div className="form-group">
                <label>Symbol</label>
                <select className="form-input" value={orderSymbol} onChange={(e) => setOrderSymbol(e.target.value)}>
                  <option value="RELIANCE.NS">RELIANCE</option>
                  <option value="TCS.NS">TCS</option>
                  <option value="HDFCBANK.NS">HDFCBANK</option>
                  <option value="INFY.NS">INFY</option>
                  <option value="^NSEI">NIFTY 50</option>
                  <option value="BSE:SENSEX">SENSEX</option>
                </select>
              </div>
              
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12}}>
                <div className="form-group">
                  <label>Side</label>
                  <select className="form-input" value={orderSide} onChange={(e) => setOrderSide(e.target.value)}>
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Quantity</label>
                  <input type="number" className="form-input" value={orderQty} onChange={(e) => setOrderQty(e.target.value)} min={1} required />
                </div>
              </div>

              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12}}>
                <div className="form-group">
                  <label>Order Type</label>
                  <select className="form-input" value={orderType} onChange={(e) => setOrderType(e.target.value)}>
                    <option value="MARKET">Market</option>
                    <option value="LIMIT">Limit</option>
                  </select>
                </div>
                {orderType === 'LIMIT' && (
                  <div className="form-group">
                    <label>Price</label>
                    <input type="number" className="form-input" value={orderPrice} onChange={(e) => setOrderPrice(e.target.value)} step={0.05} placeholder="0.00" required />
                  </div>
                )}
              </div>

              <button type="submit" className="btn-primary" style={{width: '100%', marginTop: 8}} disabled={orderLoading}>
                {orderLoading ? 'Placing Order...' : `${orderSide} Order`}
              </button>
            </form>
          </div>

          {/* Watchlist Panel with search */}
          <div className="card glass" style={{gridColumn: 'span 8'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16}}>
              <h3 style={{margin: 0}}>Watchlist Tracker</h3>
              <div style={{display: 'flex', gap: 12, alignItems: 'center'}}>
                <input 
                  type="text" 
                  placeholder="Filter ticker..." 
                  className="form-input" 
                  style={{padding: '6px 12px', width: 160}} 
                  value={watchlistFilter} 
                  onChange={(e) => setWatchlistFilter(e.target.value)} 
                />
                <button 
                  className={`btn-primary ${expiryTarget ? 'bg-bearish-glow' : ''}`} 
                  style={{padding: '6px 12px', background: expiryTarget ? 'var(--bearish)' : 'var(--primary)', boxShadow: 'none'}}
                  onClick={() => {
                    if (!expiryTarget) setExpiryTarget('BSE:SENSEX');
                    else if (expiryTarget === 'BSE:SENSEX') setExpiryTarget('^NSEI');
                    else setExpiryTarget('');
                  }}
                  title="Cycle Expiry Mode Target"
                >
                  <Zap size={14} style={{display: 'inline', marginRight: 4}} />
                  {expiryTarget === 'BSE:SENSEX' ? 'Expiry: SENSEX' : expiryTarget === '^NSEI' ? 'Expiry: NIFTY 50' : 'Expiry Mode OFF'}
                </button>
                <button 
                  className="btn-primary" 
                  style={{padding: '6px 12px', background: autoTradeEnabled ? 'var(--bullish)' : 'transparent', border: autoTradeEnabled ? 'none' : '1px solid var(--text-muted)', boxShadow: autoTradeEnabled ? '0 0 10px rgba(16, 185, 129, 0.4)' : 'none', color: autoTradeEnabled ? '#fff' : 'var(--text-muted)'}}
                  onClick={toggleAutoTrade}
                  title="Enable fully autonomous algorithmic execution"
                >
                  <Activity size={14} style={{display: 'inline', marginRight: 4}} />
                  {autoTradeEnabled ? 'AUTO-TRADE: ACTIVE' : 'AUTO-TRADE: OFF'}
                </button>
                <button className="tab-btn" onClick={fetchLiveSignals} style={{padding: 6}}>
                  <RefreshCw size={14} />
                </button>
              </div>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Asset</th>
                    <th>Current Price</th>
                    <th>Action</th>
                    <th>Target Buy Price</th>
                    <th>Target Sell Price</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredWatchlist.map((sig, idx) => {
                    // Simulated signals for display purposes as requested by user
                    const isBuy = sig.signal === 'BUY';
                    const isSell = sig.signal === 'SELL';
                    
                    let buyAt = sig.price;
                    let sellAt = sig.price;

                    if (isBuy) {
                      buyAt = sig.price; 
                      sellAt = sig.price * 1.015; // 1.5% target
                    } else if (isSell) {
                      buyAt = sig.price * 0.985; // short cover target
                      sellAt = sig.price;
                    } else {
                      // Neutral
                      buyAt = sig.price * 0.995; // buy on slight dip
                      sellAt = sig.price * 1.005; // sell on slight peak
                    }

                    return (
                      <tr key={idx} style={{cursor: 'pointer'}} onClick={() => { setSelectedSymbol(sig.symbol); setActiveTab('analysis'); }}>
                        <td style={{fontWeight: 600}}>{sig.symbol.replace('.NS', '')}</td>
                        <td>₹{sig.price?.toFixed(2)}</td>
                        <td>{getSignalBadge(sig.signal)}</td>
                        <td style={{color: 'var(--bullish)', fontWeight: 500}}>₹{buyAt?.toFixed(2)}</td>
                        <td style={{color: 'var(--bearish)', fontWeight: 500}}>₹{sellAt?.toFixed(2)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Order Book with search */}
          <div className="card glass" style={{gridColumn: 'span 12'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12}}>
              <h3 style={{margin: 0}}>Order Execution Logs</h3>
              <input 
                type="text" 
                placeholder="Search logs..." 
                className="form-input" 
                style={{padding: '6px 12px', width: 200}} 
                value={orderFilter} 
                onChange={(e) => setOrderFilter(e.target.value)} 
              />
            </div>
            <div className="table-container">
              {filteredOrders?.length === 0 ? (
                <p style={{color: 'var(--text-muted)', textAlign: 'center', padding: '48px 0'}}>No records match criteria.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Order ID</th>
                      <th>Symbol</th>
                      <th>Side</th>
                      <th>Qty</th>
                      <th>Fill Price</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredOrders?.map((order, idx) => (
                      <tr key={idx}>
                        <td><code>{order.order_id}</code></td>
                        <td>{order.symbol}</td>
                        <td className={order.side === 'BUY' ? 'text-bullish' : 'text-bearish'}>{order.side}</td>
                        <td>{order.quantity}</td>
                        <td>₹{order.fill_price?.toFixed(2)}</td>
                        <td>
                          <span className="status-badge status-filled">{order.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'analysis' && (
        <div className="grid-container">
          {/* Controls & AI Advisor */}
          <div className="card glass" style={{gridColumn: 'span 4'}}>
            <div className="form-group" style={{marginBottom: 20}}>
              <label>Select Company</label>
              <select 
                className="form-input" 
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
              >
                <option value="RELIANCE.NS">RELIANCE</option>
                <option value="TCS.NS">TCS</option>
                <option value="HDFCBANK.NS">HDFCBANK</option>
                <option value="INFY.NS">INFY</option>
                <option value="^NSEI">NIFTY 50</option>
                <option value="BSE:SENSEX">SENSEX</option>
              </select>
            </div>

            {/* Quick manual Buy/Sell buttons for high interactivity */}
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20}}>
              <button onClick={() => handleQuickOrder('BUY')} className="btn-primary bg-bullish-glow" style={{background: 'var(--bullish)', color: '#fff', boxShadow: 'none'}}>
                Quick BUY (10 units)
              </button>
              <button onClick={() => handleQuickOrder('SELL')} className="btn-primary bg-bearish-glow" style={{background: 'var(--bearish)', color: '#fff', boxShadow: 'none'}}>
                Quick SELL (10 units)
              </button>
            </div>

            {analysisLoading || !analysisData ? (
              <div style={{textAlign: 'center', padding: '20px 0', color: 'var(--text-muted)'}}>
                <Zap size={30} className="pulse" style={{marginBottom: 8, opacity: 0.5}} />
                <p>Synthesizing analyzer insights...</p>
              </div>
            ) : (
              <div>
                <div style={{background: 'linear-gradient(145deg, rgba(99,102,241,0.15), rgba(14,165,233,0.05))', padding: 16, borderRadius: 12, border: '1px solid rgba(99,102,241,0.25)', marginBottom: 20}}>
                  <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12}}>
                    <Brain size={20} className="text-primary" />
                    <span style={{fontWeight: 600, color: 'var(--text-primary)'}}>Quant Advisor Insight</span>
                  </div>
                  <p style={{fontSize: '0.9rem', color: 'var(--text-primary)', lineHeight: 1.6, margin: 0}}>
                    "{analysisData.fundamentals.advisor_advice}"
                  </p>
                </div>

                <div style={{background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 12, marginBottom: 16, border: '1px solid rgba(255,255,255,0.05)', textAlign: 'center'}}>
                  <span style={{fontSize: '0.8rem', color: 'var(--text-secondary)'}}>Live Algorithmic Signal</span>
                  {(() => {
                    const tech = analysisData.technicals;
                    let score = 0;
                    if (tech.trend_strength?.toLowerCase().includes('uptrend')) score += 2;
                    if (tech.trend_strength?.toLowerCase().includes('downtrend')) score -= 2;
                    if (tech.rsi_status?.toLowerCase() === 'bullish') score += 1;
                    if (tech.rsi_status?.toLowerCase() === 'bearish') score -= 1;
                    if (tech.rsi_status?.toLowerCase() === 'overbought') score -= 2;
                    if (tech.rsi_status?.toLowerCase() === 'oversold') score += 2;
                    if (tech.is_sideways) score = score / 2;
                    
                    let signal = 'NEUTRAL';
                    let color = 'var(--text-muted)';
                    let glow = 'none';
                    if (score >= 2.5) { signal = 'STRONG BUY'; color = 'var(--bullish)'; glow = '0 0 15px rgba(16, 185, 129, 0.4)'; }
                    else if (score >= 1) { signal = 'BUY'; color = '#34d399'; glow = '0 0 10px rgba(52, 211, 153, 0.3)'; }
                    else if (score <= -2.5) { signal = 'STRONG SELL'; color = 'var(--bearish)'; glow = '0 0 15px rgba(239, 68, 68, 0.4)'; }
                    else if (score <= -1) { signal = 'SELL'; color = '#f87171'; glow = '0 0 10px rgba(248, 113, 113, 0.3)'; }
                    
                    return (
                      <div style={{fontSize: '1.5rem', fontWeight: 700, color, textShadow: glow, marginTop: 4, letterSpacing: '1.5px'}}>
                        {signal}
                      </div>
                    );
                  })()}
                </div>

                <h4 style={{margin: '0 0 12px 0'}}>Technicals Summary</h4>
                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20}}>
                  <div className="sub-stat-card">
                    <span className="sub-stat-label">Sideways Filter</span>
                    <span className={`sub-stat-val ${analysisData.technicals.is_sideways ? 'text-bearish' : 'text-bullish'}`}>
                      {analysisData.technicals.is_sideways ? 'Sideways (No Go)' : 'Trending (Trade)'}
                    </span>
                  </div>
                  <div className="sub-stat-card">
                    <span className="sub-stat-label">RSI Condition</span>
                    <span className="sub-stat-val text-primary">{analysisData.technicals.rsi_status}</span>
                  </div>
                  <div className="sub-stat-card">
                    <span className="sub-stat-label">Trend Strength</span>
                    <span className="sub-stat-val text-bullish">{analysisData.technicals.trend_strength}</span>
                  </div>
                  <div className="sub-stat-card">
                    <span className="sub-stat-label">VWAP Target</span>
                    <span className="sub-stat-val text-secondary">{analysisData.technicals.vwap_proximity}</span>
                  </div>
                </div>

                {globalSentiment && (
                  <>
                    <h4 style={{margin: '0 0 12px 0'}}>Global Sentiment & Macro</h4>
                    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 20}}>
                      <div className="sub-stat-card">
                        <span className="sub-stat-label">Overall Bias</span>
                        <span className={`sub-stat-val ${globalSentiment.overall_impact === 'BULLISH' ? 'text-bullish' : globalSentiment.overall_impact === 'BEARISH' ? 'text-bearish' : 'text-primary'}`}>
                          {globalSentiment.overall_impact}
                        </span>
                      </div>
                      <div className="sub-stat-card">
                        <span className="sub-stat-label">News Score</span>
                        <span className="sub-stat-val text-secondary">{globalSentiment.sentiment.score.toFixed(1)}</span>
                      </div>
                      <div className="sub-stat-card">
                        <span className="sub-stat-label">Global Markets</span>
                        <span className="sub-stat-val text-secondary">{globalSentiment.global_score.toFixed(1)}</span>
                      </div>
                    </div>
                  </>
                )}

                {optionChain && (
                  <>
                    <h4 style={{margin: '0 0 12px 0'}}>Options AI Analytics</h4>
                    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20}}>
                      <div className="sub-stat-card">
                        <span className="sub-stat-label">Put-Call Ratio (PCR)</span>
                        <span className={`sub-stat-val ${optionChain.pcr > 1.0 ? 'text-bullish' : 'text-bearish'}`}>
                          {optionChain.pcr.toFixed(2)} {optionChain.pcr > 1.0 ? '(Bullish)' : '(Bearish)'}
                        </span>
                      </div>
                      <div className="sub-stat-card">
                        <span className="sub-stat-label">Highest Put OI (Support)</span>
                        <span className="sub-stat-val text-bullish">{optionChain.support}</span>
                      </div>
                      <div className="sub-stat-card">
                        <span className="sub-stat-label">Highest Call OI (Resistance)</span>
                        <span className="sub-stat-val text-bearish">{optionChain.resistance}</span>
                      </div>
                      <div className="sub-stat-card">
                        <span className="sub-stat-label">Trend Bias</span>
                        <span className={`sub-stat-val ${optionChain.bias === 'BULLISH' ? 'text-bullish' : 'text-bearish'}`}>
                          {optionChain.bias}
                        </span>
                      </div>
                    </div>
                  </>
                )}

                <h4 style={{margin: '0 0 12px 0'}}>Fundamentals Overview</h4>
                <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.5}}>
                  {analysisData.fundamentals.business_summary}
                </p>
                <div className="table-container" style={{marginTop: 0}}>
                  <table className="analysis-table">
                    <tbody>
                      <tr><td>P/E Ratio</td><td style={{textAlign: 'right', fontWeight: 600}}>{analysisData.fundamentals.pe_ratio}</td></tr>
                      <tr><td>P/B Ratio</td><td style={{textAlign: 'right', fontWeight: 600}}>{analysisData.fundamentals.pb_ratio}</td></tr>
                      <tr><td>Market Cap</td><td style={{textAlign: 'right', fontWeight: 600}}>{analysisData.fundamentals.market_cap}</td></tr>
                      <tr><td>Dividend Yield</td><td style={{textAlign: 'right', fontWeight: 600}}>{analysisData.fundamentals.dividend_yield}</td></tr>
                      <tr><td>EPS</td><td style={{textAlign: 'right', fontWeight: 600}}>₹{analysisData.fundamentals.eps}</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Charts Panel with Line Toggles */}
          <div className="card glass chart-card" style={{gridColumn: 'span 8'}}>
            {indicatorsData.length > 0 && (() => {
              const latestData = indicatorsData[indicatorsData.length - 1];
              const firstData = indicatorsData[0];
              const currentPrice = latestData?.close;
              const prevPrice = firstData?.close;
              const priceDiff = currentPrice - prevPrice;
              const pricePct = prevPrice !== 0 ? (priceDiff / prevPrice) * 100 : 0;
              const isPositive = priceDiff >= 0;
              
              const highs = indicatorsData.map(d => d.high).filter(Boolean);
              const lows = indicatorsData.map(d => d.low).filter(Boolean);
              const dayHigh = highs.length ? Math.max(...highs) : 0;
              const dayLow = lows.length ? Math.min(...lows) : 0;
              const lowHighDiff = dayHigh - dayLow;
              const currentPositionPct = lowHighDiff > 0 ? ((currentPrice - dayLow) / lowHighDiff) * 100 : 50;

              return (
                <div style={{marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16, background: 'rgba(255,255,255,0.02)', padding: '16px 20px', borderRadius: 12, border: '1px solid rgba(255,255,255,0.05)'}}>
                  <div>
                    <span style={{fontSize: '0.85rem', color: 'var(--text-secondary)'}}>Live Market Price</span>
                    <div style={{display: 'flex', alignItems: 'baseline', gap: 8}}>
                      <h2 style={{margin: 0, fontSize: '2.25rem', color: isPositive ? 'var(--bullish)' : 'var(--bearish)'}}>
                        ₹{currentPrice?.toFixed(2)}
                      </h2>
                      <span style={{fontSize: '0.95rem', fontWeight: 600, color: isPositive ? 'var(--bullish)' : 'var(--bearish)'}}>
                        {isPositive ? '▲' : '▼'} {Math.abs(priceDiff)?.toFixed(2)} ({isPositive ? '+' : ''}{pricePct?.toFixed(2)}%)
                      </span>
                    </div>
                  </div>

                  {/* Day's Range Slider like Groww */}
                  <div style={{flex: 1, minWidth: 200, maxWidth: 300}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 8, fontWeight: 500}}>
                      <span>Day Low: ₹{dayLow?.toFixed(2)}</span>
                      <span>Day High: ₹{dayHigh?.toFixed(2)}</span>
                    </div>
                    <div style={{height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, position: 'relative'}}>
                      <div style={{
                        position: 'absolute', 
                        left: `${Math.min(100, Math.max(0, currentPositionPct))}%`, 
                        top: -4, 
                        width: 14, 
                        height: 14, 
                        background: isPositive ? 'var(--bullish)' : 'var(--bearish)', 
                        borderRadius: '50%', 
                        boxShadow: `0 0 10px ${isPositive ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)'}`
                      }} />
                    </div>
                  </div>
                </div>
              );
            })()}

            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16}}>
              <h3 style={{margin: 0}}>Interactive Charting</h3>
              
              {/* Checkboxes for Toggles */}
              <div style={{display: 'flex', gap: 12, flexWrap: 'wrap'}}>
                <label style={{fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer'}}>
                  <input type="checkbox" checked={chartLines.vwap} onChange={() => toggleChartLine('vwap')} /> VWAP
                </label>
                <label style={{fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer'}}>
                  <input type="checkbox" checked={chartLines.ema_20} onChange={() => toggleChartLine('ema_20')} /> EMA 20
                </label>
                <label style={{fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer'}}>
                  <input type="checkbox" checked={chartLines.ema_50} onChange={() => toggleChartLine('ema_50')} /> EMA 50
                </label>
                <label style={{fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer'}}>
                  <input type="checkbox" checked={chartLines.rsi_14} onChange={() => toggleChartLine('rsi_14')} /> RSI
                </label>
              </div>
            </div>
            
            {indicatorsData.length === 0 ? (
              <div style={{width: '100%', height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: 8}}>
                <Activity size={40} className="pulse" />
                <p style={{margin: 0}}>Streaming price data...</p>
              </div>
            ) : (
              <>
                <div style={{width: '100%', height: 320}}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={indicatorsData}>
                      <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="timestamp" stroke="var(--text-muted)" fontSize={10} tickFormatter={(str) => str?.slice(11, 16)} />
                      <YAxis stroke="var(--text-muted)" domain={['auto', 'auto']} />
                      <Tooltip contentStyle={{background: '#0f172a', borderColor: '#334155'}} />
                      <Legend />
                      {chartLines.price && (
                        <Area type="monotone" dataKey="close" stroke="var(--primary)" strokeWidth={2.5} fillOpacity={1} fill="url(#colorPrice)" name="Price" />
                      )}
                      {chartLines.vwap && <Line type="monotone" dataKey="vwap" stroke="#eab308" strokeWidth={1.5} dot={false} name="VWAP" />}
                      {chartLines.ema_20 && <Line type="monotone" dataKey="ema_20" stroke="#0ea5e9" strokeWidth={1.5} dot={false} name="EMA 20" />}
                      {chartLines.ema_50 && <Line type="monotone" dataKey="ema_50" stroke="#6366f1" strokeWidth={1.5} dot={false} name="EMA 50" />}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                
                {chartLines.rsi_14 && (
                  <div style={{width: '100%', height: 120, marginTop: 16}}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={indicatorsData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="timestamp" hide />
                        <YAxis domain={[0, 100]} stroke="var(--text-muted)" ticks={[30, 50, 70]} />
                        <Tooltip contentStyle={{background: '#0f172a', borderColor: '#334155'}} />
                        <Area type="monotone" dataKey="rsi_14" stroke="#818cf8" fill="rgba(99, 102, 241, 0.1)" name="RSI (14)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {activeTab === 'backtest' && (
        <div className="grid-container">
          {/* Backtest Inputs */}
          <div className="card glass side-panel">
            <h3>Backtest Parameters</h3>
            <form onSubmit={handleRunBacktest}>
              <div className="form-group">
                <label>Symbol</label>
                <input type="text" className="form-input" value={btSymbol} onChange={(e) => setBtSymbol(e.target.value)} placeholder="e.g. RELIANCE.NS or NIFTY50" required />
                <span style={{fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', marginTop: 4, display: 'block'}}>
                  Tip: Type <b>NIFTY50</b> or a comma-separated list.
                </span>
              </div>
              <div className="form-group">
                <label>Interval</label>
                <select className="form-input" value={btInterval} onChange={(e) => setBtInterval(e.target.value)}>
                  <option value="5m">5 Minute</option>
                  <option value="15m">15 Minute</option>
                  <option value="60m">1 Hour</option>
                  <option value="1d">1 Day</option>
                </select>
              </div>
              <div className="form-group">
                <label>Start Date</label>
                <input type="date" className="form-input" value={btStartDate} onChange={(e) => setBtStartDate(e.target.value)} required />
              </div>
              <button type="submit" className="btn-primary" style={{width: '100%', marginTop: 8}} disabled={btLoading}>
                {btLoading ? 'Simulating...' : 'Run Analysis'}
              </button>
            </form>
          </div>

          {/* Backtest Output */}
          <div className="card glass chart-card">
            <h3>Backtest Performance Analytics</h3>
            {!btResults ? (
              <div style={{textAlign: 'center', padding: '80px 0', color: 'var(--text-muted)'}}>
                <BarChart2 size={48} style={{opacity: 0.3, marginBottom: 12}} />
                <p>Configure constraints and run engine to assess strategy performance.</p>
              </div>
            ) : (
              <div>
                <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24}}>
                  <div className="sub-stat-card" style={{padding: 16}}>
                    <span className="sub-stat-label">Final Equity</span>
                    <p style={{fontSize: '1.5rem', fontWeight: 600, margin: '4px 0', color: btResults.metrics.total_pnl >= 0 ? 'var(--bullish)' : 'var(--bearish)'}}>
                      ₹{btResults.metrics.final_equity?.toFixed(2)}
                    </p>
                  </div>
                  <div className="sub-stat-card" style={{padding: 16}}>
                    <span className="sub-stat-label">Total Trades</span>
                    <p style={{fontSize: '1.5rem', fontWeight: 600, margin: '4px 0'}}>{btResults.metrics.total_trades}</p>
                  </div>
                  <div className="sub-stat-card" style={{padding: 16}}>
                    <span className="sub-stat-label">Win Rate</span>
                    <p style={{fontSize: '1.5rem', fontWeight: 600, margin: '4px 0'}}>{(btResults.metrics.win_rate * 100).toFixed(1)}%</p>
                  </div>
                  <div className="sub-stat-card" style={{padding: 16}}>
                    <span className="sub-stat-label">Sharpe Ratio</span>
                    <p style={{fontSize: '1.5rem', fontWeight: 600, margin: '4px 0'}}>{btResults.metrics.sharpe_ratio?.toFixed(2)}</p>
                  </div>
                </div>

                <h4 style={{margin: '16px 0 8px 0'}}>Transaction History</h4>
                <div className="table-container" style={{maxHeight: 250}}>
                  <table>
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Type</th>
                        <th>Units</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>PnL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {btResults.trades?.map((trade, idx) => (
                        <tr key={idx}>
                          <td style={{fontWeight: 600, color: '#eab308'}}>{trade.symbol ? trade.symbol.replace('.NS', '') : 'N/A'}</td>
                          <td style={{fontWeight: 600}} className={trade.type === 'LONG' ? 'text-bullish' : 'text-bearish'}>{trade.type}</td>
                          <td>{trade.units}</td>
                          <td>₹{trade.entry_price?.toFixed(2)}</td>
                          <td>₹{trade.exit_price?.toFixed(2)}</td>
                          <td className={trade.pnl >= 0 ? 'text-bullish' : 'text-bearish'}>
                            ₹{trade.pnl >= 0 ? '+' : ''}{trade.pnl?.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


export default App;
