import sys
import pandas as pd
from datetime import datetime, timedelta
from app.data.yfinance_client import YFinanceClient
from app.indicators.engine import IndicatorEngine
from app.strategies.scalping import NiftyScalpingStrategy
from app.backtester.engine import BacktestEngine

def run():
    print("Initializing scalping backtest for Nifty 50...")
    client = YFinanceClient()
    
    # Let's fetch data for the last 30 days on a 5m interval
    start_date = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    symbol = "^NSEI" # Nifty 50
    print(f"Fetching 5m data for {symbol} from {start_date} to {end_date}...")
    
    df = client.fetch_historical_data(symbol, "5m", start_date, end_date)
    
    if df.empty:
        print("Failed to fetch historical data for backtest.")
        return
        
    print(f"Data fetched successfully! Total candles: {len(df)}")
    
    print("Running Nifty 50 Scalping Strategy (9/21 EMA)...")
    strategy = NiftyScalpingStrategy()
    engine = BacktestEngine(initial_capital=100000.0)
    
    results = engine.run(strategy, df, risk_per_trade_pct=0.5)
    
    print("\n" + "="*40)
    print("BACKTEST RESULTS (Nifty 50 Intraday)")
    print("="*40)
    print(f"Initial Capital: Rs {results['initial_capital']}")
    print(f"Final Equity: Rs {results['final_equity']:.2f}")
    print(f"Total Profit/Loss: Rs {results['total_pnl']:.2f}")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate'] * 100:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    
    print("\nExit Reasons Breakdown:")
    reasons = [t.get('exit_reason') for t in results['trades']]
    from collections import Counter
    for reason, count in Counter(reasons).items():
        print(f" - {reason}: {count}")
    print("="*40)

if __name__ == "__main__":
    run()
