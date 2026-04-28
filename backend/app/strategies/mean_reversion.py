import pandas as pd
from typing import Dict, Any
from app.strategies.base import Strategy
from app.indicators.engine import IndicatorEngine
from app.utils.logger import get_logger

logger = get_logger("MeanReversionStrategy")

class MeanReversionStrategy(Strategy):
    """
    Simple RSI Mean Reversion Strategy.
    
    Rules:
    - Buy (1): RSI_14 < 30 (Oversold, expect bounce)
    - Sell (-1): RSI_14 > 70 (Overbought, expect drop)
    - Hold (0): Otherwise
    """

    def __init__(self):
        super().__init__("RSI_Mean_Reversion")

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Generating mean reversion signals")
        
        if 'rsi_14' not in df.columns:
            df = IndicatorEngine.apply_indicators(df)

        df = df.copy()
        df['signal'] = 0

        df.loc[df['rsi_14'] < 30, 'signal'] = 1
        df.loc[df['rsi_14'] > 70, 'signal'] = -1

        return df

    def check_live_signal(self, current_data: Dict[str, Any]) -> int:
        try:
            rsi = float(current_data.get('rsi_14', 50.0))
            if rsi < 30:
                logger.info("LIVE MEAN REVERSION SIGNAL: BUY")
                return 1
            elif rsi > 70:
                logger.info("LIVE MEAN REVERSION SIGNAL: SELL")
                return -1
            return 0
        except Exception as e:
            logger.error(f"Error in mean reversion: {e}")
            return 0
