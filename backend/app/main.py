import sys
import subprocess

# Failsafe: Programmatically install missing dependencies for Render
try:
    import logzero
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "logzero", "websocket-client"])

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
from app.data.angel_client import AngelOneClient
from app.indicators.engine import IndicatorEngine
from app.strategies.vwap_rsi_ema import VwapRsiEmaStrategy
from app.strategies.probabilistic_engine import ProbabilisticEngineStrategy
from app.data.option_chain import OptionChainAnalyzer
from app.data.sentiment_engine import SentimentEngine
from app.backtester.engine import BacktestEngine
from app.execution.mock_executor import MockExecutor
from app.execution.angel_one import AngelOneExecutor
from app.execution.low_capital_manager import LowCapitalManager
from app.utils.logger import get_logger
import os

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
angel_client = AngelOneClient()
yfinance_client = YFinanceClient()
mock_client = MockClient()
mock_executor = MockExecutor(initial_capital=5000.0) # Updated for low capital user
real_executor = AngelOneExecutor(
    api_key=os.getenv("ANGEL_API_KEY"),
    client_id=os.getenv("ANGEL_CLIENT_ID"),
    password=os.getenv("ANGEL_PASSWORD"),
    totp_secret=os.getenv("ANGEL_TOTP_SECRET")
)
real_executor.connect()

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
                # Strict Data Source Management for Auto-Trade
                now = datetime.now()
                is_market_open = now.weekday() < 5 and (now.hour > 9 or (now.hour == 9 and now.minute >= 15)) and (now.hour < 15 or (now.hour == 15 and now.minute <= 30))

                for symbol in watchlist:
                    # Expiry logic strictly bound to respective days: Nifty (Tue=1), Sensex (Thu=3)
                    current_expiry_mode = False
                    if symbol == '^NSEI' and today == 1:
                        current_expiry_mode = True
                    elif symbol == 'BSE:SENSEX' and today == 3:
                        current_expiry_mode = True
                        
                    strategy = ProbabilisticEngineStrategy(expiry_mode=current_expiry_mode)
                    
                    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
                    yf_symbol = '^BSESN' if 'SENSEX' in symbol else symbol
                    
                    # Primary: Angel One
                    df = angel_client.fetch_historical_data(symbol, '5m', start_date)
                    if df.empty:
                        df = yfinance_client.fetch_historical_data(yf_symbol, '5m', start_date)
                        
                    # Tertiary: Mock Data (RESTRICTED during market hours)
                    if df.empty and not is_market_open:
                        logger.info(f"Using Mock Data for Auto-Trade: {symbol} (Market Closed)")
                        df = mock_client.fetch_historical_data(symbol, '5m', start_date)
                        
                    if not df.empty:
                        df_ind = IndicatorEngine.apply_indicators(df)
                        latest = df_ind.iloc[-1].to_dict()
                        
                        # Fetch real option chain for PCR and ATM strike
                        opt_data = angel_client.fetch_option_chain(symbol, float(latest['close']))
                        
                        sig = strategy.check_live_signal(latest, option_data=opt_data)
                        
                        if sig != 0:
                            side = "BUY" if sig == 1 else "SELL"
                            price = latest.get('close', 100)
                            lot_size = 20 if "SENSEX" in symbol else 65
                            
                            viability = low_capital_manager.check_trade_viability(price, lot_size)
                            
                            if viability.get('viable'):
                                # Prevent duplicate positions in the same direction
                                current_pos = mock_executor.positions.get(symbol, 0)
                                if (side == "BUY" and current_pos <= 0) or (side == "SELL" and current_pos >= 0):
                                    qty = viability.get('lots', 1) * lot_size
                                    
                                    # Execute real order
                                    real_res = real_executor.place_order(
                                        symbol=symbol,
                                        quantity=qty,
                                        side=side,
                                        price=price
                                    )
                                    
                                    if real_res.get("status") == "success":
                                        # Use actual trading symbol and fetch its price for tracking
                                        actual_sym = real_res.get("trading_symbol", symbol)
                                        actual_price = price
                                        if actual_sym != symbol:
                                            try:
                                                q = angel_client.fetch_live_quote(actual_sym)
                                                actual_price = q.get('last_price', price)
                                            except: pass
                                            
                                        # Record in UI state manager
                                        mock_executor.place_order(
                                            symbol=actual_sym,
                                            quantity=qty,
                                            side=side,
                                            order_type="MARKET",
                                            price=actual_price
                                        )
                                        logger.info(f"[REAL AUTO-TRADE EXECUTED] {side} {actual_sym} @ {actual_price} | OrderID: {real_res.get('order_id')}")
                                    else:
                                        logger.error(f"[AUTO-TRADE REJECTED] {symbol}: {real_res.get('message')}")
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
    yf_symbol = '^BSESN' if 'SENSEX' in symbol else symbol
    
    # Try Angel One
    quote = angel_client.fetch_live_quote(symbol)
    
    # Try YFinance
    if not quote or quote.get('last_price') == 0:
        quote = yfinance_client.fetch_live_quote(yf_symbol)
        
    if not quote or quote.get('last_price') == 0:
        # Fallback to Mock only if NOT Nifty/Sensex
        if "NIFTY" in symbol.upper() or "SENSEX" in symbol.upper():
             logger.error(f"Live data failed for {symbol}. No mock fallback allowed for indices.")
             raise HTTPException(status_code=503, detail=f"Live data unavailable for {symbol}. Please check connection.")
        
        logger.info("Falling back to MockClient for quote")
        quote = mock_client.fetch_live_quote(symbol)
    
    # ensure returned symbol matches requested symbol
    if quote and "symbol" in quote:
        quote["symbol"] = symbol
        
    return quote

@app.post("/api/backtest")
def run_backtest(request: BacktestRequest):
    # Determine the symbols list
    if request.symbol.upper() in ['NIFTY50', 'ALL', 'WATCHLIST']:
        symbols = ['^NSEI', 'BSE:SENSEX']
    else:
        symbols = [s.strip() for s in request.symbol.split(',')]

    all_trades = []
    total_pnl = 0.0
    total_trades = 0
    win_trades = 0
    sharpe_ratios = []

    for symbol in symbols:
        try:
            yf_symbol = '^BSESN' if 'SENSEX' in symbol else symbol
            # Fetch historical data
            df = angel_client.fetch_historical_data(
                symbol=symbol,
                interval=request.interval,
                start_date=request.start_date,
                end_date=request.end_date
            )
            if df.empty:
                df = yfinance_client.fetch_historical_data(
                    symbol=yf_symbol,
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
    yf_symbol = '^BSESN' if 'SENSEX' in symbol else symbol
    df = angel_client.fetch_historical_data(symbol, interval, start_date)
    if df.empty:
        df = yfinance_client.fetch_historical_data(yf_symbol, interval, start_date)
        
    if df.empty:
        if "NIFTY" in symbol.upper() or "SENSEX" in symbol.upper():
             logger.error(f"Historical live data failed for {symbol}. No mock fallback allowed for indices.")
             raise HTTPException(status_code=503, detail=f"Market data unavailable for {symbol}.")
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
def get_live_signals(expiry_target: Optional[str] = None):
    """
    Checks real-time signals for predefined watchlist using AI Probabilistic Scoring.
    """
    watchlist = ['^NSEI', 'BSE:SENSEX']
    signals = []
    
    for symbol in watchlist:
        # User explicitly chooses the target index from the UI, so we just match it
        current_expiry_mode = False
        if expiry_target and expiry_target == symbol:
            current_expiry_mode = True
            
        strategy = ProbabilisticEngineStrategy(expiry_mode=current_expiry_mode)
        
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        yf_symbol = '^BSESN' if 'SENSEX' in symbol else symbol
        
        # Strict Data Source Management
        now = datetime.now()
        is_market_open = now.weekday() < 5 and (now.hour > 9 or (now.hour == 9 and now.minute >= 15)) and (now.hour < 15 or (now.hour == 15 and now.minute <= 30))

        # Primary: Angel One (Real Broker)
        df = angel_client.fetch_historical_data(symbol, '5m', start_date)
        
        # Secondary: Yahoo Finance (Real but potentially delayed)
        if df.empty:
            df = yfinance_client.fetch_historical_data(yf_symbol, '5m', start_date)
        
        # Tertiary: Mock Data (ONLY allowed outside market hours for demo/testing)
        if df.empty and not is_market_open:
            logger.info(f"Using Mock Data for {symbol} (Market is Closed/Weekend)")
            df = mock_client.fetch_historical_data(symbol, '5m', start_date)
        if df.empty:
            logger.warning(f"No real data available for {symbol} right now.")
            continue
            
        df_ind = IndicatorEngine.apply_indicators(df)
        latest = df_ind.iloc[-1].to_dict()
        latest['symbol'] = symbol
        
        # Fetch real option chain data for this symbol to provide real signal
        opt_data = angel_client.fetch_option_chain(symbol, float(latest['close']))
        
        sig = strategy.check_live_signal(latest, option_data=opt_data)
        
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
def get_option_chain_analysis(symbol: str = "NIFTY", spot_price: float = 24000.0):
    """
    Returns Support, Resistance, ATM strike, and PCR metrics using REAL Angel One data.
    """
    # 1. Fetch real index price if spot_price is default or old
    if spot_price == 22000.0 or spot_price == 24000.0:
        quote = angel_client.fetch_live_quote(symbol)
        if quote and quote.get('last_price'):
            spot_price = quote['last_price']
            
    # 2. Fetch real option chain structure
    option_data = angel_client.fetch_option_chain(symbol, spot_price)
    
    # 3. Analyze
    analysis = OptionChainAnalyzer.analyze_chain(option_data, spot_price)
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
    yf_symbol = '^BSESN' if 'SENSEX' in symbol else symbol
    df = angel_client.fetch_historical_data(symbol, '5m', start_date)
    if df.empty:
        df = yfinance_client.fetch_historical_data(yf_symbol, '5m', start_date)
    
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
        # Place real order via Angel One
        real_res = real_executor.place_order(
            symbol=request.symbol,
            quantity=request.quantity,
            side=request.side,
            order_type=request.order_type,
            price=request.price
        )
        
        if real_res.get("status") != "success":
            raise HTTPException(status_code=400, detail=real_res.get("message", "Order execution failed"))

        # Use the actual symbol from the broker (important for Options)
        actual_symbol = real_res.get("trading_symbol", request.symbol)
        
        # Fetch the actual fill price for the option/stock if it was an index order
        actual_price = request.price
        if actual_symbol != request.symbol:
            try:
                quote = get_quote(actual_symbol)
                actual_price = quote.get('last_price', request.price)
                logger.info(f"Actual fill price for {actual_symbol}: {actual_price} (Index was {request.price})")
            except Exception:
                pass
                
        order = mock_executor.place_order(
            symbol=actual_symbol,
            quantity=request.quantity,
            side=request.side,
            order_type=request.order_type,
            price=actual_price
        )
        return {"status": "success", "order": order, "broker_order_id": real_res.get("order_id")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/positions/reset")
def reset_positions():
    mock_executor.positions = {}
    mock_executor.order_history = []
    mock_executor.capital = 100000.0 # Reset to default
    mock_executor._save_state()
    return {"status": "success", "message": "All positions and history cleared."}

@app.post("/api/positions/exit")
def exit_position(symbol: str = Query(...)):
    # Find the position
    pos_data = mock_executor.positions.get(symbol)
    if not pos_data or pos_data.get('qty', 0) == 0:
        raise HTTPException(status_code=400, detail="No active position for this symbol.")
        
    qty = abs(pos_data['qty'])
    side = "SELL" if pos_data['qty'] > 0 else "BUY"
    
    # Place opposite market order
    try:
        # Use existing place_order logic for real execution and mock sync
        from fastapi import Request
        from pydantic import BaseModel
        class InternalOrder(BaseModel):
            symbol: str
            quantity: int
            side: str
            order_type: str
            
        dummy_req = InternalOrder(symbol=symbol, quantity=qty, side=side, order_type="MARKET")
        return place_order(dummy_req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Exit failed: {str(e)}")

@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str):
    success = mock_executor.cancel_order(order_id)
    if success:
        return {"status": "success", "message": f"Order {order_id} cancelled"}
    else:
        raise HTTPException(status_code=404, detail="Order not found or already filled")

@app.get("/api/positions")
def get_positions():
    detailed_positions = []
    total_pnl = 0.0
    
    for symbol, pos_data in mock_executor.positions.items():
        qty = pos_data.get("qty", 0)
        avg_price = pos_data.get("avg_price", 0.0)
        
        if qty == 0:
            continue
            
        # Fetch LTP
        ltp = 0.0
        try:
            quote = get_quote(symbol)
            ltp = quote.get('last_price', 0.0)
        except Exception:
            # Fallback to last filled price or 0
            ltp = avg_price
            
        pnl = (ltp - avg_price) * qty
        
        # Determine Type and Strike
        pos_type = "EQ"
        strike = ""
        if "CE" in symbol.upper() or "PE" in symbol.upper():
            pos_type = "CE" if "CE" in symbol.upper() else "PE"
            import re
            # Extract last numeric part before CE/PE (usually 5 digits for indices)
            match = re.search(r'(\d+)(?:CE|PE)', symbol.upper())
            if match:
                full_num = match.group(1)
                # Strike is usually the last 5 digits (e.g., 24200) in index options
                strike = full_num[-5:] if len(full_num) > 5 else full_num
        
        # PNL Correction: If avg_price is > 10000 and LTP < 1000 for an OPTION,
        # it means the index price was recorded as avg_price in a previous bugged version.
        display_pnl = pnl
        display_pnl_pct = ((ltp - avg_price) / avg_price * 100) if avg_price != 0 else 0
        
        if pos_type != "EQ" and avg_price > 10000 and ltp < 1000:
            display_pnl = 0.0
            display_pnl_pct = 0.0
            
        # Accumulate corrected PNL
        total_pnl += display_pnl
        
        detailed_positions.append({
            "symbol": symbol,
            "display_name": symbol.replace(".NS", ""),
            "type": pos_type,
            "strike": strike,
            "quantity": qty,
            "avg_price": avg_price,
            "ltp": ltp,
            "pnl": display_pnl,
            "pnl_pct": display_pnl_pct
        })

    # Enrich Order History with types and strikes
    enriched_history = []
    for order in mock_executor.order_history[-15:]:
        o_copy = order.copy()
        o_symbol = str(order.get('symbol', '')).upper()
        o_type = "EQ"
        o_strike = ""
        if "CE" in o_symbol or "PE" in o_symbol:
            o_type = "CE" if "CE" in o_symbol else "PE"
            import re
            match = re.search(r'(\d+)(?:CE|PE)', o_symbol)
            if match:
                full_num = match.group(1)
                o_strike = full_num[-5:] if len(full_num) > 5 else full_num
        
        o_copy["type"] = o_type
        o_copy["strike"] = o_strike
        enriched_history.append(o_copy)

    return {
        "capital": mock_executor.capital,
        "total_pnl": total_pnl,
        "positions": detailed_positions,
        "raw_positions": mock_executor.positions, # for internal use
        "order_history": enriched_history
    }


