# Chandra Quant - Advanced Algorithmic Trading Suite

Welcome to the **Chandra Quant** algorithmic trading platform. This project is a comprehensive, multi-source algorithmic trading system tailored specifically for Indian Markets (NIFTY 50, BANKNIFTY, SENSEX, and major equities). It leverages Technical Analysis (TA), Options Chain Analytics, and Global Sentiment to execute data-driven probabilistic trades.

---

## 1. System Architecture & How It Works

The project is divided into a robust **Python FastAPI backend** and a dynamic, real-time **React (Vite) frontend**. 

### 1.1 Backend (FastAPI + Pandas + SmartAPI)
The backend acts as the brain of the trading system. It fetches real-time market data, calculates mathematical indicators, and manages the execution gateways.
- **Data Integrations**: Uses Yahoo Finance (`yfinance`) for historical data and **Angel One SmartAPI** for live ticks and Option Chain data. A Mock Client is available as an automated fallback if the live API is unavailable.
- **Computation Engine**: Uses `pandas` and `numpy` for vectorized calculation of indicators (RSI, MACD, EMA, VWAP).
- **Execution Engine**: Manages orders (Market, Limit), calculates PnL, applies trailing Stop Losses, and handles risk management rules.

### 1.2 Frontend (React + Recharts)
The frontend serves as the control center, communicating with the backend over REST APIs.
- **Live Execution Terminal**: Allows manual quick-execution of trades (Buy/Sell) while visually tracking live prices.
- **AI Analytics Dashboard**: Synthesizes complex data into simple bullish/bearish visual alerts.
- **Charting**: High-performance rendering of live candlesticks, VWAP, EMA lines, and RSI bands using `Recharts`.

---

## 2. Trading Logics & Strategies Implemented

### 2.1 The Probabilistic Engine Strategy
Unlike standard crossover strategies, this engine does not rely on a single indicator. It aggregates variables across multiple domains to generate an **AI Confidence Score**.
- **Conditions**: It evaluates if `Score > 70%` for a STRONG BUY.
- **Variables**: It blends VWAP pullbacks, MACD crossovers, RSI divergences, and Option Chain Put Writing.

### 2.2 Option Chain Analysis Engine
Especially crucial for Expiry-Day trades on NIFTY/BANKNIFTY:
- **Support & Resistance Detection**: Scans the Option Chain to find the strike prices with the **Highest Put OI** (Strong Support) and **Highest Call OI** (Strong Resistance).
- **Put-Call Ratio (PCR)**: Computes real-time PCR. A PCR > 1.0 indicates bullishness (put writing), while PCR < 1.0 implies bearishness.
- **Trend Bias**: Analyzes OI shifts (e.g., Short Covering vs. Long Unwinding) to predict immediate breakout direction.

### 2.3 Global Sentiment & Macro Engine
Local markets do not operate in isolation.
- The engine fetches live global market data (Dow Jones, Nasdaq, SGX/GIFT Nifty).
- It scores the overall global bias (BULLISH vs BEARISH) and adds this weight to the local Probabilistic Engine to prevent taking long trades on days when global markets are crashing.

### 2.4 Low Capital Guardrails
Designed to protect small accounts (₹2,000 - ₹5,000):
- Hard limit of **1 Lot per trade** for Options.
- Strict per-trade Maximum Risk exposure to prevent margin blowouts.

---

## 3. How Auto-Trading Execution Flows

Here is the exact step-by-step lifecycle of an automated trade:

1. **Market Pulse (Every 15 Seconds)**:
   - The backend `yfinance` or `SmartAPI` fetches the latest 5-minute candle data and Option Chain data.
2. **Data Enrichment**:
   - The data is pushed through the `IndicatorEngine` to append live RSI, VWAP, EMA 20, EMA 50, and MACD values.
3. **Condition Evaluation**:
   - The `ProbabilisticEngineStrategy` scores the current data point. 
   - *Example*: Price > VWAP (Score +2), PCR > 1.2 (Score +3), Global Markets Green (Score +1). Total Score = 6 (Bullish).
4. **Risk Validation**:
   - The generated signal ("BUY NIFTY50") is sent to the `RiskManager` / `LowCapitalManager`. It checks if there is sufficient margin and if the user hasn't exceeded the daily trade limit.
5. **Broker Execution**:
   - The `AngelOne` execution class maps the signal to the broker's specific API payload (Token, Exchange segment, Order type).
   - The order is pushed via SmartAPI as an Intraday (MIS) Market order.
6. **Trade Lifecycle Management**:
   - Once filled, the Execution Engine begins tracking the position.
   - It continually updates the PnL. If the PnL crosses the Take Profit threshold or drops below the Stop Loss, the system fires a rapid Exit Market order.

---

## 4. Frequently Asked Questions (FAQ)

**Q1: How do I switch from Paper Trading to Live Trading?**
**A**: Ensure your `backend/.env` file contains valid Angel One credentials (`ANGEL_API_KEY`, `ANGEL_CLIENT_ID`, `ANGEL_PASSWORD`, `ANGEL_TOTP_SECRET`). The backend automatically switches to Live Execution when valid credentials exist and the Mock Executor is disabled in `main.py`.

**Q2: Does the system trade automatically when I am not watching?**
**A**: Only if the automated strategy background task is enabled. Currently, signals are fetched and shown on the dashboard for you to click "Quick Buy". To fully automate, a background loop must continuously call `engine.run_live()` in the FastAPI application.

**Q3: Why is my Option Chain data showing simulated/fallback data?**
**A**: If the Angel One API hits a rate limit, or outside of market hours, the `OptionChainAnalyzer` falls back to smart simulated bounds based on the current spot price to keep the frontend running without crashing.

**Q4: How are expiry day strategies different?**
**A**: On Tuesdays (Nifty Expiry) and Thursdays (Sensex Expiry), the `ProbabilisticEngine` enables `expiry_mode`. It reduces reliance on lagging indicators like MACD and heavily weighs **Option Chain PCR** and **OI un-winding** to catch rapid Gamma spikes (Hero-Zero trades).

**Q5: What happens if my internet disconnects?**
**A**: The backend runs independently on your server (e.g., Render). Even if your browser frontend closes, the backend will continue to monitor open positions and execute Stop Losses.

---

*Documentation maintained by Chandra Quant Team. Last updated: April 2026.*
