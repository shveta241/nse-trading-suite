import pandas as pd
from typing import Dict, Any
from app.strategies.base import Strategy
from app.indicators.engine import IndicatorEngine
from app.utils.logger import get_logger

logger = get_logger("Nifty50_Scalping")

class NiftyScalpingStrategy(Strategy):
    """
    High-Frequency Scalping Strategy for Nifty 50.
    Operates best on 1-Minute or 3-Minute charts.
    
    Rules:
    - BUY (1): 9 EMA crosses ABOVE 21 EMA
    - SELL (-1): 9 EMA crosses BELOW 21 EMA
    """

    def __init__(self):
        super().__init__("Nifty50_9_21_EMA_Scalping")

    def is_sideways(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Detects sideways markets by evaluating the percentage range over the last N candles.
        If the range is extremely narrow (e.g., less than 0.12%), it considers it sideways.
        """
        rolling_high = df['high'].rolling(window=period).max()
        rolling_low = df['low'].rolling(window=period).min()
        range_pct = (rolling_high - rolling_low) / df['close'] * 100.0
        return range_pct < 0.12

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Generating Scalping signals for Nifty 50 with Sideways Filter")
        
        df = df.copy()
        df['ema_9'] = IndicatorEngine.calculate_ema(df, 9)
        df['ema_21'] = IndicatorEngine.calculate_ema(df, 21)
        df['sideways'] = self.is_sideways(df)
        
        df['signal'] = 0

        # EMA Crossover + Trend Filter (Not sideways)
        # Buy: EMA 9 crosses above EMA 21 AND market is NOT sideways
        buy_cond = (df['ema_9'] > df['ema_21']) & (df['ema_9'].shift(1) <= df['ema_21'].shift(1)) & (~df['sideways'])
        df.loc[buy_cond, 'signal'] = 1
        
        # Sell: EMA 9 crosses below EMA 21 AND market is NOT sideways
        sell_cond = (df['ema_9'] < df['ema_21']) & (df['ema_9'].shift(1) >= df['ema_21'].shift(1)) & (~df['sideways'])
        df.loc[sell_cond, 'signal'] = -1

        return df

    def check_live_signal(self, current_data: Dict[str, Any]) -> int:
        try:
            ema_9 = float(current_data.get('ema_9', 0.0))
            ema_21 = float(current_data.get('ema_21', 0.0))
            
            if ema_9 == 0.0 or ema_21 == 0.0:
                return 0

            if ema_9 > ema_21:
                return 1
            elif ema_9 < ema_21:
                return -1
                
            return 0
        except Exception as e:
            logger.error(f"Error in scalping strategy: {e}")
            return 0
