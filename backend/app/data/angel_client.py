import os
import pyotp
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from SmartApi import SmartConnect
from app.data.base import DataFetcher
from app.utils.logger import get_logger

logger = get_logger("AngelOneClient")
load_dotenv()

class AngelOneClient(DataFetcher):
    """
    Data fetcher implementation using Angel One SmartAPI.
    Provides real-time tick data and historical data for Indian markets.
    """

    def __init__(self):
        self.api_key = os.getenv("ANGEL_API_KEY")
        self.client_id = os.getenv("ANGEL_CLIENT_ID")
        self.password = os.getenv("ANGEL_PASSWORD")
        self.totp_secret = os.getenv("ANGEL_TOTP_SECRET")
        self.smartApi = None
        self.is_connected = False
        
        # Token mapping for Angel One (Exchange: Token)
        # ^BSESN -> BSE: 999901
        # ^NSEI -> NSE: 26000
        # RELIANCE -> NSE: 2885
        # TCS -> NSE: 11536
        # HDFCBANK -> NSE: 1333
        # INFY -> NSE: 1594
        self.token_map = {
            "^BSESN": {"exchange": "BSE", "token": "999901"},
            "^NSEI": {"exchange": "NSE", "token": "26000"},
            "RELIANCE.NS": {"exchange": "NSE", "token": "2885"},
            "TCS.NS": {"exchange": "NSE", "token": "11536"},
            "HDFCBANK.NS": {"exchange": "NSE", "token": "1333"},
            "INFY.NS": {"exchange": "NSE", "token": "1594"},
        }
        
        self.connect()

    def connect(self):
        try:
            if not all([self.api_key, self.client_id, self.password, self.totp_secret]):
                logger.error("Missing Angel One credentials in .env")
                return

            self.smartApi = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_secret).now()
            
            data = self.smartApi.generateSession(self.client_id, self.password, totp)
            
            if data.get('status'):
                self.is_connected = True
                logger.info("Successfully connected to Angel One SmartAPI")
            else:
                logger.error(f"Failed to connect to Angel One: {data.get('message')}")
        except Exception as e:
            logger.error(f"Error connecting to Angel One: {e}")

    def fetch_historical_data(
        self, 
        symbol: str, 
        interval: str, 
        start_date: str, 
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        if not self.is_connected or not self.smartApi:
            return pd.DataFrame()

        token_info = self.token_map.get(symbol)
        if not token_info:
            return pd.DataFrame()

        # Map interval
        # Angel One intervals: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY
        interval_map = {
            "1m": "ONE_MINUTE",
            "5m": "FIVE_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "30m": "THIRTY_MINUTE",
            "1h": "ONE_HOUR",
            "1d": "ONE_DAY"
        }
        angel_interval = interval_map.get(interval, "FIVE_MINUTE")

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            end_date = end_date + " 15:30"
            
        start_date = start_date + " 09:15"

        try:
            historicParam = {
                "exchange": token_info["exchange"],
                "symboltoken": token_info["token"],
                "interval": angel_interval,
                "fromdate": start_date,
                "todate": end_date
            }
            response = self.smartApi.getCandleData(historicParam)
            
            if response and response.get("status") and response.get("data"):
                data = response["data"]
                # Format: [timestamp, open, high, low, close, volume]
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                return df
            else:
                logger.warning(f"Failed to fetch historical data from Angel One for {symbol}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching historical data from Angel One: {e}")
            return pd.DataFrame()

    def fetch_live_quote(self, symbol: str) -> Dict[str, Any]:
        logger.info(f"Fetching live quote from Angel One for {symbol}")
        
        if not self.is_connected or not self.smartApi:
            logger.warning("Angel One not connected.")
            return {}

        token_info = self.token_map.get(symbol)
        if not token_info:
            logger.warning(f"Symbol {symbol} not mapped in Angel One token map.")
            return {}

        try:
            exchange = token_info["exchange"]
            token = token_info["token"]
            
            response = self.smartApi.ltpData(exchange, symbol.replace(".NS", "").replace("^", ""), token)
            
            if response and response.get('status'):
                data = response['data']
                return {
                    "symbol": symbol,
                    "last_price": float(data.get("ltp", 0.0)),
                    "volume": 0, # LTP API doesn't return volume
                    "timestamp": datetime.now()
                }
            else:
                logger.warning(f"Failed to get LTP from Angel One for {symbol}: {response}")
                return {}
        except Exception as e:
            logger.error(f"Error fetching live quote from Angel One: {e}")
            return {}
