import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.data.base import DataFetcher
from app.utils.logger import get_logger

logger = get_logger("MockClient")

class MockClient(DataFetcher):
    """
    Mock Data Fetcher for testing and demonstration purposes.
    Generates synthetic stock data.
    """

    def fetch_historical_data(
        self, 
        symbol: str, 
        interval: str, 
        start_date: str, 
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        logger.info(f"Generating mock historical data for {symbol}")
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end = datetime.now()

        # Create datetime index
        if interval == '1d':
            freq = 'B' # Business days
        elif interval == '1m':
            freq = 'min'
        elif interval == '5m':
            freq = '5min'
        else:
            freq = '15min'

        date_range = pd.date_range(start=start, end=end, freq=freq)
        n = len(date_range)
        
        if n == 0:
            return pd.DataFrame()

        # Generate synthetic prices using random walk
        np.random.seed(42)
        returns = np.random.normal(0.0001, 0.01, n)
        price = 1000.0 * np.exp(np.cumsum(returns))
        
        # Create OHLC
        volatility = 0.005
        open_p = price * (1 + np.random.normal(0, volatility, n))
        close_p = price * (1 + np.random.normal(0, volatility, n))
        high_p = np.maximum(open_p, close_p) * (1 + np.abs(np.random.normal(0, volatility, n)))
        low_p = np.minimum(open_p, close_p) * (1 - np.abs(np.random.normal(0, volatility, n)))
        volume = np.random.randint(1000, 100000, n)

        df = pd.DataFrame({
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
            'volume': volume
        }, index=date_range)

        return df

    def fetch_live_quote(self, symbol: str) -> Dict[str, Any]:
        logger.info(f"Generating mock live quote for {symbol}")
        return {
            "symbol": symbol,
            "last_price": float(np.random.uniform(1000, 1500)),
            "volume": int(np.random.randint(100, 5000)),
            "timestamp": datetime.now()
        }
