from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any

class DataFetcher(ABC):
    """
    Abstract Base Class for Data Fetching.
    Allows switching between Yahoo Finance, Zerodha Kite, Angel One, or Mock Data.
    """
    
    @abstractmethod
    def fetch_historical_data(
        self, 
        symbol: str, 
        interval: str, 
        start_date: str, 
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetches historical OHLCV data.
        Returns a pandas DataFrame with columns: ['open', 'high', 'low', 'close', 'volume']
        and a DatetimeIndex.
        """
        pass

    @abstractmethod
    def fetch_live_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches the latest live quote for a symbol.
        Returns a dictionary with at least: {'symbol': str, 'last_price': float, 'volume': int, 'timestamp': datetime}
        """
        pass
