import pandas as pd
import numpy as np
from typing import Dict, Any, List
from app.strategies.base import Strategy
from app.utils.logger import get_logger

logger = get_logger("BacktestEngine")

class BacktestEngine:
    """
    Simulates a strategy on historical OHLCV data.
    """

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.equity_curve = []

    def run(self, strategy: Strategy, df: pd.DataFrame, risk_per_trade_pct: float = 1.0) -> Dict[str, Any]:
        logger.info(f"Starting backtest for {strategy.name}")
        
        if df.empty:
            logger.warning("Backtest aborted: Empty DataFrame.")
            return {"error": "Empty data"}

        # 1. Generate Signals
        processed_df = strategy.generate_signals(df)
        
        # 2. Iterate through rows and simulate trades
        # We assume entry at the CLOSE of the signal bar (or open of next bar)
        # For simplicity, we execute on signal bar's close price
        
        position = 0  # 1 for Long, -1 for Short (if shorting allowed), 0 for Flat
        entry_price = 0.0
        entry_time = None
        units = 0
        trades: List[Dict[str, Any]] = []
        
        capital = self.initial_capital
        equity = capital
        equity_curve = []

        for i in range(1, len(processed_df)):
            row = processed_df.iloc[i]
            prev_row = processed_df.iloc[i-1]
            current_time = processed_df.index[i]
            price = row['close']
            
            # Risk calculation
            # Risk 1% of equity per trade
            risk_amt = equity * (risk_per_trade_pct / 100.0)

            # Signal transitions
            signal = prev_row['signal'] # Use previous bar's signal to avoid look-ahead bias

            # 1. Manage existing positions (check Stop Loss or Target Profit - simplified for backtester)
            # In a robust engine, you'd check high/low against SL/TP. 
            # We'll just exit on opposite signal or end of day for simplicity.

            # 2. Process signals
            if position == 0 and signal != 0:
                # Enter Trade
                entry_price = price
                entry_time = current_time
                position = signal
                # Target units based on risk
                stop_loss_dist = entry_price * 0.015  # 1.5% SL
                units = int(risk_amt // stop_loss_dist)
                
                # Check capital constraints
                max_units = int(capital // entry_price)
                units = min(units, max_units)

                if units > 0:
                    capital -= units * entry_price
                    logger.info(f"Backtest ENTRY: {'BUY' if signal == 1 else 'SELL'} {units} @ {entry_price} on {current_time}")

            elif position == 1 and signal == -1:
                # Exit Long
                exit_price = price
                profit = (exit_price - entry_price) * units
                capital += units * exit_price
                
                trades.append({
                    "type": "LONG",
                    "entry_time": entry_time.isoformat() if isinstance(entry_time, pd.Timestamp) else str(entry_time) if entry_time else None,
                    "exit_time": current_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "units": units,
                    "pnl": profit
                })
                logger.info(f"Backtest EXIT: SELL {units} @ {exit_price} | PnL: {profit}")
                position = 0
                units = 0
                entry_time = None

            elif position == -1 and signal == 1:
                # Exit Short (simulated)
                exit_price = price
                # For short, profit = (entry - exit) * units
                profit = (entry_price - exit_price) * units
                # Short covers by buying back
                capital += (entry_price * units) + profit
                
                trades.append({
                    "type": "SHORT",
                    "entry_time": entry_time.isoformat() if isinstance(entry_time, pd.Timestamp) else str(entry_time) if entry_time else None,
                    "exit_time": current_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "units": units,
                    "pnl": profit
                })
                logger.info(f"Backtest EXIT: COVER {units} @ {exit_price} | PnL: {profit}")
                position = 0
                units = 0
                entry_time = None

            # Calculate current equity
            current_equity = capital
            if position == 1:
                current_equity += units * price
            elif position == -1:
                # Equity for short = capital + initial short value + unrealized PnL
                # Unrealized PnL = (entry_price - price) * units
                current_equity += (entry_price * units) + ((entry_price - price) * units)

            equity_curve.append({"timestamp": current_time, "equity": current_equity})
            equity = current_equity

        # Calculate metrics
        pnl_series = [t['pnl'] for t in trades]
        total_pnl = sum(pnl_series)
        win_rate = len([p for p in pnl_series if p > 0]) / len(pnl_series) if pnl_series else 0.0

        # Equity Curve metrics
        eq_df = pd.DataFrame(equity_curve)
        if not eq_df.empty:
            eq_df['returns'] = eq_df['equity'].pct_change()
            sharpe = (eq_df['returns'].mean() / eq_df['returns'].std() * np.sqrt(252)) if eq_df['returns'].std() > 0 else 0
        else:
            sharpe = 0

        metrics = {
            "initial_capital": self.initial_capital,
            "final_equity": equity,
            "total_trades": len(trades),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "sharpe_ratio": float(sharpe),
            "trades": trades
        }

        return metrics
