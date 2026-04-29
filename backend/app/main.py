from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import asyncio

from app.data.yfinance_client import YFinanceClient
from app.data.mock_client import MockClient
from app.indicators.engine import IndicatorEngine
from app.strategies.vwap_rsi_ema import VwapRsiEmaStrategy
from app.strategies.probabilistic_engine import ProbabilisticEngineStrategy
from app.data.option_chain import OptionChainAnalyzer
from app.data.sentiment_engine import SentimentEngine
from app.backtester.engine import BacktestEngine
from app.execution.mock_executor import MockExecutor
from app.execution.low_capital_manager import LowCapitalManager
from app.utils.logger import get_logger


logger = get_logger("Main")

app = FastAPI(title="NSE Algorithmic Trading System", version="1.0.0")

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Shared in-memory components
yfinance_client = YFinanceClient()
mock_client = MockClient()
mock_executor = MockExecutor(initial_capital=5000.0) # Updated for low capital user
low_capital_manager = LowCapitalManager(initial_capital=5000.0)

# Global flag for the auto-trading loop
auto_trade_state = {"enabled": False}

async def auto_trade_loop():
    logger.info("Auto-Trade background loop initialized.")
    watchlist = ['^NSEI', 'BSE:SENSEX']
    
    while True:
        if auto_trade_state["enabled"]:
            try:
                today = datetime.now().weekday()
                is_auto_expiry = today in [1, 2, 3, 4] # Any weekday can be an expiry for something, trigger hero-zero mode for scalping
                strategy = ProbabilisticEngineStrategy(expiry_mode=is_auto_expiry)
                
                for symbol in watchlist:
                    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
                    
                    if "SENSEX" in symbol:
                        df = mock_client.fetch_historical_data('^BSESN', '5m', start_date)
                    else:
                        df = yfinance_client.fetch_historical_data(symbol, '5m', start_date)
                        
                    if df.empty:
                        df = mock_client.fetch_historical_data(symbol, '5m', start_date)
                        
                    if not df.empty:
                        df_ind = IndicatorEngine.apply_indicators(df)
                        latest = df_ind.iloc[-1].to_dict()
                        
                        sig = strategy.check_live_signal(latest)
                        
                        if sig != 0:
                            side = "BUY" if sig == 1 else "SELL"
                            price = latest.get('close', 100)
                            lot_size = 15 if "SENSEX" in symbol else 50
                            
                            viability = low_capital_manager.check_trade_viability(price, lot_size)
                            
                            if viability.get('viable'):
                                # Prevent duplicate positions in the same direction
                                current_pos = mock_executor.positions.get(symbol, 0)
                                if (side == "BUY" and current_pos <= 0) or (side == "SELL" and current_pos >= 0):
                                    mock_executor.place_order(
                                        symbol=symbol,
                                        quantity=viability.get('lots', 1) * lot_size,
                                        side=side,
                                        order_type="MARKET",
                                        price=price
                                    )
                                    logger.info(f"[AUTO-TRADE EXECUTED] {side} {symbol} @ {price}")
            except Exception as e:
                logger.error(f"Auto-trade loop error: {e}")
                
        await asyncio.sleep(60) # Run every 60 seconds

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auto_trade_loop())

class BacktestRequest(BaseModel):
    symbol: str
    interval: str = '5m'
    start_date: str
    end_date: Optional[str] = None
    capital: float = 100000.0

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/api/health")
def health_check():
    return {"status": "running", "timestamp": datetime.now()}

@app.post("/api/login")
def login(request: LoginRequest):
    if request.username == "admin" and request.password == "admin":
        return {"status": "success", "token": "mock-jwt-token-12345", "username": request.username}
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")


@app.post("/api/autotrade/toggle")
def toggle_autotrade():
    auto_trade_state["enabled"] = not auto_trade_state["enabled"]
    return {"status": "success", "enabled": auto_trade_state["enabled"], "message": f"Auto-trade is now {'ON' if auto_trade_state['enabled'] else 'OFF'}"}

@app.get("/api/autotrade/status")
def get_autotrade_status():
    return {"enabled": auto_trade_state["enabled"]}

@app.get("/api/quote")
def get_quote(symbol: str = Query(..., description="NSE Stock Symbol (e.g., RELIANCE.NS)")):
    # Try YFinance
    quote = yfinance_client.fetch_live_quote(symbol)
    if not quote or quote.get('last_price') == 0:
        # Fallback to Mock
        logger.info("Falling back to MockClient for quote")
        quote = mock_client.fetch_live_quote(symbol)
    return quote

@app.post("/api/backtest")
def run_backtest(request: BacktestRequest):
    # Determine the symbols list
    if request.symbol.upper() in ['NIFTY50', 'ALL', 'WATCHLIST']:
        symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS']
    else:
        symbols = [s.strip() for s in request.symbol.split(',')]

    all_trades = []
    total_pnl = 0.0
    total_trades = 0
    win_trades = 0
    sharpe_ratios = []

    for symbol in symbols:
        try:
            # Fetch historical data
            df = yfinance_client.fetch_historical_data(
                symbol=symbol,
                interval=request.interval,
                start_date=request.start_date,
                end_date=request.end_date
            )
            
            if df.empty:
                # Try Mock fallback
                logger.info(f"Falling back to MockClient for backtest data for {symbol}")
                df = mock_client.fetch_historical_data(
                    symbol=symbol,
                    interval=request.interval,
                    start_date=request.start_date,
                    end_date=request.end_date
                )

            if df.empty:
                logger.warning(f"Could not fetch data for {symbol}, skipping.")
                continue

            # Calculate indicators
            df_with_indicators = IndicatorEngine.apply_indicators(df)
            
            # Run Backtest
            strategy = VwapRsiEmaStrategy()
            engine = BacktestEngine(initial_capital=request.capital)
            results = engine.run(strategy, df_with_indicators)
            
            # Enrich trades
            for t in results.get('trades', []):
                t['symbol'] = symbol
                if 'exit_time' in t and isinstance(t['exit_time'], pd.Timestamp):
                    t['exit_time'] = t['exit_time'].isoformat()
                if 'entry_time' in t and isinstance(t['entry_time'], pd.Timestamp):
                    t['entry_time'] = t['entry_time'].isoformat()
                all_trades.append(t)
                
            total_pnl += results.get("total_pnl", 0.0)
            total_trades += results.get("total_trades", 0)
            
            # Calculate win trades for this symbol
            pnl_series = [t['pnl'] for t in results.get('trades', [])]
            win_trades += len([p for p in pnl_series if p > 0])
            
            if results.get("sharpe_ratio"):
                sharpe_ratios.append(results["sharpe_ratio"])
                
        except Exception as e:
            logger.error(f"Error backtesting {symbol}: {str(e)}")
            continue

    if not all_trades and len(symbols) == 1:
        raise HTTPException(status_code=400, detail=f"Could not fetch data or run backtest for {symbols[0]}.")
    elif not all_trades:
        raise HTTPException(status_code=400, detail="Could not fetch data or run backtest for any of the requested symbols.")

    # Aggregate metrics
    final_equity = request.capital + total_pnl
    win_rate = win_trades / total_trades if total_trades > 0 else 0.0
    avg_sharpe = sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0.0

    # Sort all trades by exit_time if available
    try:
        all_trades.sort(key=lambda x: x.get('exit_time', '') or '', reverse=True)
    except Exception:
        pass

    return {
        "symbol": request.symbol,
        "metrics": {
            "initial_capital": request.capital,
            "final_equity": final_equity,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "sharpe_ratio": avg_sharpe
        },
        "trades": all_trades[:100]  # limit payload
    }

@app.get("/api/indicators")
def get_indicators(symbol: str, interval: str = '5m'):
    # Default to past 5 days for intraday intervals
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    
    df = yfinance_client.fetch_historical_data(symbol, interval, start_date)
    if df.empty:
        df = mock_client.fetch_historical_data(symbol, interval, start_date)

    if df.empty:
        raise HTTPException(status_code=404, detail="No data found")

    df_with_indicators = IndicatorEngine.apply_indicators(df)
    
    # Take the last 50 data points for UI
    recent_df = df_with_indicators.tail(50).reset_index()

    # After reset_index(), the datetime index column could be named
    # 'Datetime', 'Date', or 'index' depending on the data source.
    # Rename whatever it is to 'timestamp' safely.
    dt_col = recent_df.columns[0]  # first column after reset_index is always the old index
    recent_df.rename(columns={dt_col: 'timestamp'}, inplace=True)
    recent_df['timestamp'] = recent_df['timestamp'].astype(str)

    data = recent_df.replace({np.nan: None}).to_dict(orient='records')
    return data

@app.get("/api/signals")
def get_live_signals(expiry_mode: bool = False):
    """
    Checks real-time signals for predefined watchlist using AI Probabilistic Scoring.
    """
    watchlist = ['^NSEI', 'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'BSE:SENSEX']
    signals = []
    
    strategy = ProbabilisticEngineStrategy(expiry_mode=expiry_mode)
    
    for symbol in watchlist:
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        if "SENSEX" in symbol:
            # Fallback for SENSEX data mapping
            df = mock_client.fetch_historical_data('^BSESN', '5m', start_date)
        else:
            df = yfinance_client.fetch_historical_data(symbol, '5m', start_date)
            
        if df.empty:
            df = mock_client.fetch_historical_data(symbol, '5m', start_date)
            
        if not df.empty:
            df_ind = IndicatorEngine.apply_indicators(df)
            latest = df_ind.iloc[-1].to_dict()
            latest['symbol'] = symbol
            
            sig = strategy.check_live_signal(latest)
            
            signals.append({
                "symbol": symbol,
                "price": float(latest['close']) if pd.notnull(latest['close']) else None,
                "vwap": float(latest['vwap']) if pd.notnull(latest['vwap']) else None,
                "rsi_14": float(latest['rsi_14']) if pd.notnull(latest['rsi_14']) else None,
                "ema_20": float(latest['ema_20']) if pd.notnull(latest['ema_20']) else None,
                "ema_50": float(latest['ema_50']) if pd.notnull(latest['ema_50']) else None,
                "signal": "BUY" if sig == 1 else "SELL" if sig == -1 else "NEUTRAL",
                "timestamp": datetime.now()
            })
            
    return signals

@app.get("/api/option_chain")
def get_option_chain_analysis(symbol: str = "NIFTY", spot_price: float = 22000.0):
    """
    Returns Support, Resistance, ATM strike, and PCR metrics.
    """
    # Uses fallback simulation for rapid computation
    analysis = OptionChainAnalyzer.analyze_chain([], spot_price)
    return analysis

@app.get("/api/global_sentiment")
def get_sentiment():
    """
    Returns scores for global indicators & news sentiment.
    """
    sent = SentimentEngine.analyze_news_sentiment()
    glob_score = SentimentEngine.get_global_markets_score()
    return {
        "sentiment": sent,
        "global_score": glob_score,
        "overall_impact": "BULLISH" if (sent['score'] + glob_score) > 30 else "BEARISH" if (sent['score'] + glob_score) < -30 else "NEUTRAL"
    }



@app.get("/api/analysis")
def get_advanced_analysis(symbol: str = Query(..., description="NSE Stock Symbol")):
    # Base Data for fundamentals (simulated for high speed and resilience)
    fa_database = {
        "RELIANCE.NS": {
            "pe_ratio": 26.8,
            "market_cap": "₹18,54,320 Cr",
            "pb_ratio": 2.4,
            "dividend_yield": "0.35%",
            "eps": 98.4,
            "business_summary": "Energy, Retail, and Digital Services leader with strong multi-sector moats.",
            "advisor_advice": "Strong momentum. Accumulate on dips near support levels. Avoid chasing at all-time highs."
        },
        "TCS.NS": {
            "pe_ratio": 29.5,
            "market_cap": "₹14,80,450 Cr",
            "pb_ratio": 12.1,
            "dividend_yield": "1.15%",
            "eps": 134.5,
            "business_summary": "Premier global IT services firm with stellar cash conversion and client stickiness.",
            "advisor_advice": "Defensive play. Excellent yield. Suitable for risk-averse portfolios during market chop."
        },
        "HDFCBANK.NS": {
            "pe_ratio": 18.2,
            "market_cap": "₹11,60,920 Cr",
            "pb_ratio": 2.8,
            "dividend_yield": "0.95%",
            "eps": 82.3,
            "business_summary": "India's largest private bank with superior asset quality and post-merger scale advantages.",
            "advisor_advice": "Undervalued based on historical averages. High safety margin for mid-to-long term positions."
        },
        "INFY.NS": {
            "pe_ratio": 25.1,
            "market_cap": "₹6,15,400 Cr",
            "pb_ratio": 7.4,
            "dividend_yield": "1.80%",
            "eps": 63.2,
            "business_summary": "Leading digital transformation partner with a robust cloud & automation services portfolio.",
            "advisor_advice": "Watch for resistance breakout. Support holding well. Good risk-reward for intraday momentum."
        }
    }

    # Fetch tiny historical chunk to calculate tech analysis
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    df = yfinance_client.fetch_historical_data(symbol, '5m', start_date)
    
    if df.empty:
        df = mock_client.fetch_historical_data(symbol, '5m', start_date)

    tech_analysis = {
        "trend_strength": "Medium",
        "is_sideways": False,
        "rsi_status": "Neutral",
        "vwap_proximity": "Near VWAP"
    }

    if not df.empty:
        df_ind = IndicatorEngine.apply_indicators(df)
        latest = df_ind.iloc[-1]
        
        # Calculate trend strength & sideways status
        tech_analysis["is_sideways"] = bool(latest.get('sideways', False))
        
        rsi = float(latest.get('rsi_14', 50))
        tech_analysis["rsi_status"] = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Bullish" if rsi > 55 else "Bearish" if rsi < 45 else "Neutral"
        
        close = float(latest.get('close', 0))
        vwap = float(latest.get('vwap', close))
        vwap_diff = ((close - vwap) / vwap) * 100.0
        
        tech_analysis["vwap_proximity"] = f"{vwap_diff:+.2f}% from VWAP"
        
        ema_20 = float(latest.get('ema_20', close))
        ema_50 = float(latest.get('ema_50', close))
        tech_analysis["trend_strength"] = "Strong Uptrend" if (close > ema_20 > ema_50) else "Strong Downtrend" if (close < ema_20 < ema_50) else "Consolidation"

    fa_data = fa_database.get(symbol, {
        "pe_ratio": 20.0,
        "market_cap": "₹1,00,000 Cr",
        "pb_ratio": 3.0,
        "dividend_yield": "1.0%",
        "eps": 50.0,
        "business_summary": "Standard corporate overview available for listed entities.",
        "advisor_advice": "Maintain neutral stance. Monitor earnings updates and volume expansion."
    })

    return {
        "symbol": symbol,
        "fundamentals": fa_data,
        "technicals": tech_analysis
    }

class OrderRequest(BaseModel):
    symbol: str
    quantity: int
    side: str
    order_type: str = 'MARKET'
    price: Optional[float] = None

@app.post("/api/orders")
def place_order(request: OrderRequest):
    if request.order_type == 'MARKET' and not request.price:
        try:
            quote = get_quote(request.symbol)
            request.price = quote.get('last_price', 100.0)
        except Exception:
            request.price = 100.0

    try:
        order = mock_executor.place_order(
            symbol=request.symbol,
            quantity=request.quantity,
            side=request.side,
            order_type=request.order_type,
            price=request.price
        )
        return {"status": "success", "order": order}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str):
    success = mock_executor.cancel_order(order_id)
    if success:
        return {"status": "success", "message": f"Order {order_id} cancelled"}
    else:
        raise HTTPException(status_code=404, detail="Order not found or already filled")

@app.get("/api/positions")
def get_positions():
    return {
        "capital": mock_executor.capital,
        "positions": mock_executor.positions,
        "order_history": mock_executor.order_history[-10:] # Last 10
    }


