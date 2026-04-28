import pandas as pd
from typing import Dict, Any
from app.strategies.base import Strategy
from app.indicators.engine import IndicatorEngine
from app.execution.risk_manager import RiskManager
from app.utils.logger import get_logger

logger = get_logger("Nifty50_Intraday")
risk_manager = RiskManager()

class Nifty50IntradayStrategy(Strategy):
    """
    Intraday Strategy specifically for Nifty 50.
    Combines VWAP (Volume Weighted Average Price) and RSI.
    
    Rules:
    - BUY (1): Price crosses ABOVE VWAP AND RSI > 50 (Momentum is building upwards)
    - SELL (-1): Price crosses BELOW VWAP AND RSI < 50 (Momentum is falling downwards)
    - HOLD (0): Otherwise
    """

    def __init__(self):
        super().__init__("Nifty50_VWAP_RSI_Intraday")

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Generating Nifty 50 Intraday signals")
        
        # Ensure we have VWAP and RSI
        if 'vwap' not in df.columns or 'rsi_14' not in df.columns:
            df = IndicatorEngine.apply_indicators(df)

        df = df.copy()
        df['signal'] = 0

        # We assume df has 'close', 'vwap', 'rsi_14', 'ema_20', 'sideways'
        if 'sideways' not in df.columns:
            df['sideways'] = False

        # Signal 1 (Buy): Close > VWAP & RSI > 50 & Close > EMA20 & NOT Sideways
        df.loc[(df['close'] > df['vwap']) & (df['rsi_14'] > 50) & (df['close'] > df['ema_20']) & (~df['sideways']), 'signal'] = 1
        
        # Signal -1 (Sell/Short): Close < VWAP & RSI < 50 & Close < EMA20 & NOT Sideways
        df.loc[(df['close'] < df['vwap']) & (df['rsi_14'] < 50) & (df['close'] < df['ema_20']) & (~df['sideways']), 'signal'] = -1

        return df

    def check_live_signal(self, current_data: Dict[str, Any]) -> int:
        try:
            close = float(current_data.get('close', 0.0))
            vwap = float(current_data.get('vwap', 0.0))
            rsi = float(current_data.get('rsi_14', 50.0))
            ema20 = float(current_data.get('ema_20', close)) # fallback to close
            is_sideways = bool(current_data.get('sideways', False))
            
            if close == 0.0 or vwap == 0.0 or is_sideways:
                if is_sideways:
                    logger.info("NIFTY 50 LIVE SIGNAL: Suppressed (Sideways Market Detected)")
                return 0

            # Signal 1: Buy (Above VWAP, RSI > 55, Above EMA 20)
            if close > vwap and rsi > 55 and close > ema20:
                logger.info("NIFTY 50 LIVE SIGNAL: BUY (Uptrend Confirmed by VWAP, RSI, EMA)")
                return 1
            # Signal -1: Sell (Below VWAP, RSI < 45, Below EMA 20)
            elif close < vwap and rsi < 45 and close < ema20:
                logger.info("NIFTY 50 LIVE SIGNAL: SELL (Downtrend Confirmed by VWAP, RSI, EMA)")
                return -1
                
            return 0
        except Exception as e:
            logger.error(f"Error in Nifty 50 Intraday strategy: {e}")
            return 0
