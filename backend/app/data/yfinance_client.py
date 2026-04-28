import yfinance as yf
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime
from app.data.base import DataFetcher
from app.utils.logger import get_logger

logger = get_logger("YFinanceClient")

class YFinanceClient(DataFetcher):
    """
    Data fetcher implementation using Yahoo Finance.
    Best for historical data and backtesting.
    Note: For Indian stocks, append '.NS' to the symbol (e.g., 'RELIANCE.NS').
    """

    def fetch_historical_data(
        self, 
        symbol: str, 
        interval: str, 
        start_date: str, 
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        logger.info(f"Fetching historical data for {symbol} ({interval}) from {start_date} to {end_date}")
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Standardize columns to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
                    
            return df[required_cols]
        except Exception as e:
            logger.error(f"Error fetching data from YFinance: {e}")
            return pd.DataFrame()

    def fetch_live_quote(self, symbol: str) -> Dict[str, Any]:
        logger.info(f"Fetching live quote for {symbol}")
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            
            return {
                "symbol": symbol,
                "last_price": float(info.get("last_price", 0.0)),
                "volume": int(info.get("last_volume", 0)),
                "timestamp": datetime.now()
            }
        except Exception as e:
            logger.error(f"Error fetching live quote from YFinance: {e}")
            return {}
