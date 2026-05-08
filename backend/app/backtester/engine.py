import pandas as pd
import numpy as np
from typing import Dict, Any, List
from app.strategies.base import Strategy
from app.execution.risk_manager import RiskManager
from app.utils.logger import get_logger

logger = get_logger("BacktestEngine")

class BacktestEngine:
    """
    Simulates a strategy on historical OHLCV data using strict risk limits.
    """

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.equity_curve = []

    def run(self, strategy: Strategy, df: pd.DataFrame, risk_per_trade_pct: float = 0.5) -> Dict[str, Any]:
        logger.info(f"Starting backtest for {strategy.name} with strict risk limits.")
        
        if df.empty:
            logger.warning("Backtest aborted: Empty DataFrame.")
            return {"error": "Empty data"}

        # 1. Generate Signals
        processed_df = strategy.generate_signals(df)
        
        position = 0  # 1 for Long, -1 for Short, 0 for Flat
        entry_price = 0.0
        entry_time = None
        units = 0
        stop_loss_price = 0.0
        target_price = 0.0
        last_action_signal = 0
        trades: List[Dict[str, Any]] = []
        
        capital = self.initial_capital
        equity = capital
        equity_curve = []
        
        # Instantiate RiskManager
        rm = RiskManager(max_risk_per_trade_pct=risk_per_trade_pct)

        for i in range(1, len(processed_df)):
            row = processed_df.iloc[i]
            prev_row = processed_df.iloc[i-1]
            current_time = processed_df.index[i]
            price = row['close']
            
            # Signal transitions
            signal = prev_row['signal'] # Use previous bar's signal to avoid look-ahead bias

            # Update last_action_signal if it changes to 0
            if signal == 0:
                last_action_signal = 0

            # 1. Manage existing positions (Check SL, TP, or Reversal)
            if position != 0:
                is_exit = False
                exit_reason = ""
                exit_price = 0.0
                
                if position == 1: # Long
                    if row['low'] <= stop_loss_price:
                        is_exit = True
                        exit_reason = "STOP_LOSS"
                        exit_price = stop_loss_price
                    elif row['high'] >= target_price:
                        is_exit = True
                        exit_reason = "TAKE_PROFIT"
                        exit_price = target_price
                    elif signal == -1:
                        is_exit = True
                        exit_reason = "SIGNAL_REVERSAL"
                        exit_price = price
                elif position == -1: # Short
                    if row['high'] >= stop_loss_price:
                        is_exit = True
                        exit_reason = "STOP_LOSS"
                        exit_price = stop_loss_price
                    elif row['low'] <= target_price:
                        is_exit = True
                        exit_reason = "TAKE_PROFIT"
                        exit_price = target_price
                    elif signal == 1:
                        is_exit = True
                        exit_reason = "SIGNAL_REVERSAL"
                        exit_price = price
                        
                if is_exit:
                    if position == 1:
                        profit = (exit_price - entry_price) * units
                        capital += units * exit_price
                    else:
                        profit = (entry_price - exit_price) * units
                        capital += (entry_price * units) + profit
                        
                    trades.append({
                        "type": "LONG" if position == 1 else "SHORT",
                        "entry_time": entry_time.isoformat() if isinstance(entry_time, pd.Timestamp) else str(entry_time) if entry_time else None,
                        "exit_time": current_time.isoformat() if isinstance(current_time, pd.Timestamp) else str(current_time) if current_time else None,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "units": units,
                        "pnl": profit,
                        "exit_reason": exit_reason
                    })
                    logger.info(f"Backtest EXIT ({exit_reason}): {'SELL' if position == 1 else 'COVER'} {units} @ {exit_price} | PnL: {profit}")
                    position = 0
                    units = 0
                    entry_time = None

            # 2. Process NEW signals (If flat and fresh signal)
            if position == 0 and signal != 0 and signal != last_action_signal:
                entry_price = price
                entry_time = current_time
                position = signal
                last_action_signal = signal
                
                # Use RiskManager for exits & position sizing
                stop_loss_price, target_price = rm.get_trade_exits(entry_price, position)
                units = rm.calculate_position_size(capital, entry_price)

                if units > 0:
                    capital -= units * entry_price
                    logger.info(f"Backtest ENTRY: {'BUY' if signal == 1 else 'SELL'} {units} @ {entry_price} on {current_time} | SL: {stop_loss_price:.2f}, TP: {target_price:.2f}")
                else:
                    position = 0
                    entry_time = None
                    last_action_signal = 0

            # 3. Calculate current equity
            current_equity = capital
            if position == 1:
                current_equity += units * price
            elif position == -1:
                current_equity += (entry_price * units) + ((entry_price - price) * units)

            equity_curve.append({"timestamp": current_time, "equity": current_equity})
            equity = current_equity

        # Calculate metrics
        pnl_series = [t['pnl'] for t in trades]
        total_pnl = sum(pnl_series)
        win_trades = len([p for p in pnl_series if p > 0])
        win_rate = win_trades / len(pnl_series) if pnl_series else 0.0

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
            "equity_curve": equity_curve[-200:], # Last 200 points for UI
            "trades": trades
        }

        return metrics
