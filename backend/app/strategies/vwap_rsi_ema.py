import pandas as pd
import numpy as np
from typing import Dict, Any
from app.strategies.base import Strategy
from app.indicators.engine import IndicatorEngine
from app.utils.logger import get_logger

logger = get_logger("VwapRsiEmaStrategy")

class VwapRsiEmaStrategy(Strategy):
    """
    Intraday Strategy using VWAP, RSI, and EMA crossover.
    
    Rules:
    - Buy (1): Close > VWAP, RSI > 60, EMA 20 > EMA 50
    - Sell (-1): Close < VWAP, RSI < 40, EMA 20 < EMA 50
    - Hold (0): Otherwise
    """

    def __init__(self):
        super().__init__("VWAP_RSI_EMA_Intraday")

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Generating signals for historical data")
        
        # Ensure indicators are present
        if 'ema_20' not in df.columns or 'ema_50' not in df.columns or \
           'rsi_14' not in df.columns or 'vwap' not in df.columns or \
           'sideways' not in df.columns:
            logger.info("Applying missing technical indicators")
            df = IndicatorEngine.apply_indicators(df)

        df = df.copy()
        
        # Initialize signal column
        df['signal'] = 0

        # Buy conditions
        buy_cond = (
            (df['close'] > df['vwap']) & 
            (df['rsi_14'] > 60) & 
            (df['ema_20'] > df['ema_50']) &
            (~df['sideways'])
        )

        # Sell conditions
        sell_cond = (
            (df['close'] < df['vwap']) & 
            (df['rsi_14'] < 40) & 
            (df['ema_20'] < df['ema_50']) &
            (~df['sideways'])
        )

        # Set signals (1 for Buy, -1 for Sell)
        df.loc[buy_cond, 'signal'] = 1
        df.loc[sell_cond, 'signal'] = -1
        
        return df

    def check_live_signal(self, current_data: Dict[str, Any]) -> int:
        """
        Expects current data to have keys: ['close', 'vwap', 'rsi_14', 'ema_20', 'ema_50', 'sideways']
        """
        try:
            close = float(current_data.get('close', 0.0))
            vwap = float(current_data.get('vwap', 0.0))
            rsi = float(current_data.get('rsi_14', 50.0))
            ema_20 = float(current_data.get('ema_20', 0.0))
            ema_50 = float(current_data.get('ema_50', 0.0))
            is_sideways = bool(current_data.get('sideways', False))

            if is_sideways:
                logger.info("LIVE SIGNAL: Suppressed (Sideways Market Detected)")
                return 0

            if close > vwap and rsi > 60 and ema_20 > ema_50:

                logger.info("LIVE SIGNAL: BUY")
                return 1
            elif close < vwap and rsi < 40 and ema_20 < ema_50:
                logger.info("LIVE SIGNAL: SELL")
                return -1
                
            return 0
        except Exception as e:
            logger.error(f"Error checking live signal: {e}")
            return 0
