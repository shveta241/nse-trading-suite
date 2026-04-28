# 🚀 Nifty 50 Algorithmic Trading Software - User Guide

This documentation guides you through exploring, testing, and running the Nifty 50 automated intraday trading software.

## 📁 Project Structure overview
Understanding the core components:
- `backend/app/execution/angel_one.py`: Connects with the **Angel One SmartAPI** for order execution.
- `backend/app/strategies/nifty_intraday.py`: Contains the technical logic utilizing **VWAP**, **RSI**, and **EMA 20** to predict entry & exits.
- `backend/app/execution/risk_manager.py`: Safeguards your capital using custom limits (**0.4% Stop Loss**, **0.8% Profit Target**).

---

## ⚙️ How to use the Software

### Step 1: Environment Setup (`.env`)
Make sure your `backend/.env` file looks like this:
```env
ANGEL_API_KEY=your_smartapi_api_key
ANGEL_CLIENT_ID=your_angel_one_client_id
ANGEL_PASSWORD=your_4_digit_pin
ANGEL_TOTP_SECRET=your_base32_totp_secret_from_angel
```

### Step 2: Backtesting on Historical Data
To see how well your strategy performs historically before putting real money:
1. Open your terminal in the backend directory.
2. Run the backtest script:
   ```bash
   python scratch_backtest.py
   ```
This calculates results (Returns, Sharpe Ratio, Net profit). Note that if no trades are found, it indicates that current safety constraints (strict crossovers of all 3 parameters) were not triggered in this exact window.

### Step 3: Starting the System
Once you are confident with technical constraints and ready:
- Execute your FastAPI server:
  ```bash
  uvicorn app.main:app --reload
  ```
- Your React Dashboard can visually track quotes at `http://localhost:5173`.

> [!CAUTION]
> Always trade with capital that you can safely afford to risk. Algorithmic execution is subjected to internet drops and broker lags.
