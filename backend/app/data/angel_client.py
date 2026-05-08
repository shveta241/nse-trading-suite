import os
import pyotp
import pandas as pd
import requests
import time
from typing import Optional, Dict, Any, List
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
        
        self.token_map = {
            "NIFTY": {"exchange": "NSE", "token": "26000", "trading_symbol": "NIFTY", "name": "NIFTY"},
            "SENSEX": {"exchange": "BSE", "token": "99919000", "trading_symbol": "SENSEX", "name": "SENSEX"},
            "NIFTY 50": {"exchange": "NSE", "token": "26000", "trading_symbol": "NIFTY", "name": "NIFTY"},
            "^NSEI": {"exchange": "NSE", "token": "26000", "trading_symbol": "NIFTY", "name": "NIFTY"},
            "^BSESN": {"exchange": "BSE", "token": "99919000", "trading_symbol": "SENSEX", "name": "SENSEX"},
        }
        self.scrip_master = None
        self.last_scrip_update = 0
        
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
                self._update_scrip_master()
            else:
                logger.error(f"Failed to connect to Angel One: {data.get('message')}")
        except Exception as e:
            logger.error(f"Error connecting to Angel One: {e}")

    def _update_scrip_master(self):
        if time.time() - self.last_scrip_update < 86400 and self.scrip_master is not None:
            return
            
        logger.info("Downloading Angel One scrip master for option chain...")
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            res = requests.get(url, timeout=10)
            self.scrip_master = res.json()
            self.last_scrip_update = time.time()
        except Exception as e:
            logger.error(f"Failed to update scrip master: {e}")

    def fetch_option_chain(self, symbol: str, spot_price: float) -> List[Dict[str, Any]]:
        if not self.is_connected or not self.scrip_master:
            return []
            
        token_info = self.token_map.get(symbol)
        if not token_info:
            # Try to guess
            name = "NIFTY" if "NIFTY" in symbol.upper() else "SENSEX" if "SENSEX" in symbol.upper() else None
            exchange = "NSE" if name == "NIFTY" else "BSE"
        else:
            name = token_info.get('name')
            exchange = token_info.get('exchange')
            
        if not name: return []
        
        option_exchange = "NFO" if exchange == "NSE" else "BFO"
        strike_range = 500 # +/- 500 points
        
        # Filter relevant options from scrip master
        relevant_options = []
        for item in self.scrip_master:
            if (item.get('exch_seg') == option_exchange and 
                item.get('name') == name):
                try:
                    strike = float(item.get('strike', 0)) / 100.0
                    if abs(strike - spot_price) <= strike_range:
                        relevant_options.append(item)
                except: continue
        
        if not relevant_options: return []
        
        # Sort by expiry and pick the nearest one
        try:
            relevant_options.sort(key=lambda x: datetime.strptime(x['expiry'], '%d%b%Y') if x.get('expiry') else datetime.max)
            nearest_expiry = relevant_options[0]['expiry']
            current_expiry_options = [o for o in relevant_options if o['expiry'] == nearest_expiry]
        except:
            return []
            
        # 1. Prepare token list for batch request
        # Focus on closest 10 strikes (5 above, 5 below) to stay within API limits
        current_expiry_options.sort(key=lambda x: abs(float(x['strike']) - spot_price))
        target_options = current_expiry_options[:20] # 10 strikes * 2 (CE/PE)
        
        token_list = [{"exchangeType": 2 if exchange == "NSE" else 3, "tokens": [o['token'] for o in target_options]}]
        
        try:
            # Mode 3 = FULL (LTP, OI, etc.)
            response = self.smartApi.getMarketData("FULL", token_list)
            
            if response and response.get('status') and response.get('data'):
                market_data = response['data']['fetched']
                # Create a map for quick lookup
                data_map = {item['token']: item for item in market_data if item}
                
                chain_data = []
                for opt in target_options:
                    m_data = data_map.get(opt['token'], {})
                    chain_data.append({
                        "strike": float(opt['strike']) / 100.0,
                        "type": "CE" if opt['symbol'].endswith('CE') else "PE",
                        "oi": float(m_data.get('oi', 0)),
                        "oi_change": float(m_data.get('oi', 0)) * 0.01, # Simplified change
                        "price": float(m_data.get('ltp', 0)),
                        "token": opt['token']
                    })
                return chain_data
        except Exception as e:
            logger.error(f"Error fetching market data for option chain: {e}")
            
        # Fallback if market data API fails
        return []

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
        exchange = None
        token = None
        trading_symbol = None

        if token_info:
            exchange = token_info["exchange"]
            token = token_info["token"]
            trading_symbol = token_info.get("trading_symbol", symbol.replace(".NS", "").replace("^", ""))
        elif self.scrip_master:
            # Search in scrip master
            # Option symbols like NIFTY12MAY2624200CE
            # Equity symbols like RELIANCE-EQ
            for item in self.scrip_master:
                if item.get('symbol') == symbol or item.get('tradingsymbol') == symbol:
                    token = item.get('token')
                    exchange = item.get('exch_seg')
                    trading_symbol = item.get('symbol')
                    break
        
        if not token or not exchange:
            logger.warning(f"Symbol {symbol} not found in Angel One map or scrip master.")
            return {}

        try:
            # Map exch_seg to SmartAPI exchange string
            # SmartAPI expects: NSE, BSE, NFO, BFO, MCX, NCDEX
            exch_map = {
                "NSE": "NSE", "BSE": "BSE", 
                "NFO": "NFO", "BFO": "BFO",
                "MCX": "MCX", "NCDEX": "NCDEX"
            }
            api_exchange = exch_map.get(exchange, exchange)
            
            response = self.smartApi.ltpData(api_exchange, trading_symbol, token)
            
            if response and response.get('status'):
                data = response['data']
                return {
                    "symbol": symbol,
                    "last_price": float(data.get("ltp", 0.0)),
                    "volume": 0,
                    "timestamp": datetime.now()
                }
            else:
                logger.warning(f"Failed to get LTP from Angel One for {symbol}: {response}")
                return {}
        except Exception as e:
            logger.error(f"Error fetching live quote from Angel One: {e}")
            return {}
