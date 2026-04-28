import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger("IndicatorEngine")

class IndicatorEngine:
    """
    Engine for calculating technical indicators.
    Avoids external dependencies like TA-Lib for cross-platform compatibility.
    """

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """
        Calculates Exponential Moving Average (EMA).
        """
        logger.debug(f"Calculating EMA ({period}) for {column}")
        return df[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
        """
        Calculates Relative Strength Index (RSI) using Wilder's smoothing.
        """
        logger.debug(f"Calculating RSI ({period}) for {column}")
        delta = df[column].diff()
        
        # Make two series: one for gains and one for losses
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # Calculate Wilder's EMA
        # alpha = 1 / period
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

        # Handle division by zero
        rs = pd.Series(np.where(avg_loss == 0, np.nan, avg_gain / avg_loss), index=df.index)
        rsi = 100 - (100 / (1 + rs))
        
        # Fill NaN values (e.g., if avg_loss was 0, RSI is 100)
        rsi = rsi.fillna(100.0)
        return rsi

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """
        Calculates Volume Weighted Average Price (VWAP).
        Resets daily for intraday data.
        """
        logger.debug("Calculating VWAP")
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be a DatetimeIndex to calculate VWAP.")

        # Typical Price
        tp = (df['high'] + df['low'] + df['close']) / 3.0
        tp_v = tp * df['volume']

        # Group by date and calculate cumulative sum
        # Using df.index.date handles daily resets
        dates = df.index.date
        
        cum_tp_v = tp_v.groupby(dates).cumsum()
        cum_v = df['volume'].groupby(dates).cumsum()

        # Handle zero volume to avoid division by zero
        vwap = cum_tp_v / cum_v.replace(0, np.nan)
        
        # Forward fill in case of zero volume intervals
        return vwap.ffill()

    @staticmethod
    def calculate_sideways(df: pd.DataFrame, period: int = 14, threshold: float = 0.15) -> pd.Series:
        """
        Detects sideways markets by evaluating the percentage range over the last N candles.
        If the range is extremely narrow (e.g., less than threshold%), it considers it sideways.
        """
        logger.debug(f"Calculating Sideways Market Filter ({period})")
        rolling_high = df['high'].rolling(window=period).max()
        rolling_low = df['low'].rolling(window=period).min()
        range_pct = (rolling_high - rolling_low) / df['close'] * 100.0
        return range_pct < threshold

    @classmethod
    def apply_indicators(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies standard indicators requested (RSI 14, EMA 20, EMA 50, VWAP, Sideways) to the dataframe.
        """
        if df.empty:
            return df
            
        df = df.copy()
        df['ema_20'] = cls.calculate_ema(df, 20)
        df['ema_50'] = cls.calculate_ema(df, 50)
        df['rsi_14'] = cls.calculate_rsi(df, 14)
        df['vwap'] = cls.calculate_vwap(df)
        df['sideways'] = cls.calculate_sideways(df)
        
        return df

