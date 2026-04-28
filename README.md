# Antigravity Quant - NSE Algorithmic Trading System

An open-source, modular algorithmic trading system built for the Indian Stock Market (NSE).

## 🚀 Features
- **Data Layer**: Multi-source data fetching capability (Yahoo Finance, Mock, and extensible broker APIs).
- **Indicator Engine**: Custom, dependency-light calculation of RSI, EMA, and VWAP.
- **Strategy Suite**: Rule-based setups (including custom VWAP + RSI + EMA combination & RSI Mean Reversion).
- **Backtesting Platform**: Fast historical simulation, execution logs, and risk checks.
- **Execution & Risk Management**: Integrated Stop Loss (1.5%), Take Profit (3%), and dynamically scaled position sizing.

---

## 📂 Project Architecture & Structure

```
bit/
├── backend/
│   ├── app/
│   │   ├── backtester/        # Simulates strategies on historical data
│   │   ├── data/              # Base classes + Data provider integrations
│   │   ├── execution/         # Order orchestration & risk checks 
│   │   ├── indicators/        # Technical indicator formulas
│   │   ├── strategies/        # Core alpha generator logic
│   │   └── main.py            # FastAPI Application gateway
│   ├── logs/                  # System operational journals
│   └── requirements.txt       # Back-end dependencies
└── frontend/
    ├── src/                   # React files (App.jsx, index.css)
    ├── package.json           # Front-end dependencies
    └── vite.config.js         # Frontend compiler configuration
```

---

## 🛠️ Step-by-Step Setup Guide

### 1. Backend Setup
Navigate into the backend directory:
```bash
cd backend
```

Create a virtual environment & activate it:
```bash
python -m venv venv
.\venv\Scripts\activate   # For Windows
source venv/bin/activate  # For Linux/Mac
```

Install backend requirements:
```bash
pip install fastapi uvicorn pandas numpy yfinance requests pydantic python-dotenv pytest
```

Launch the server locally:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup
Navigate into the frontend directory from the root:
```bash
cd frontend
npm install
npm run dev
```

The React dashboard will be running at `http://localhost:5173/`.

---

## ⚡ Broker Integrations (Zerodha Kite & Angel One)

To implement a live connection with Indian brokers, place appropriate wrapper logic inside `backend/app/data/`.

### Zerodha Kite Connect Snippet:
```python
from kiteconnect import KiteConnect

class ZerodhaClient(DataFetcher):
    def __init__(self, api_key, access_token):
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
```

---

## 📦 Deployment Steps
1. **Containerization**: Deploy the FastAPI server via Docker.
2. **Reverse Proxy**: Map domains securely using Nginx with TLS encryption.
3. **Frontend Distribution**: Build modern static files using `npm run build` and serve instantly over high-speed CDNs.
