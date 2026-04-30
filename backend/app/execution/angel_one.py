import logging
from typing import Dict, Any, Optional, List
import time
import requests
import pandas as pd

from .base import BaseExecutor
import pyotp

logger = logging.getLogger(__name__)

class AngelOneExecutor(BaseExecutor):
    """
    Executor for Angel One using SmartAPI.
    Supports Equity and Index Option (Expiry) trading.
    """
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        self.smartApi = None
        self.is_connected = False
        
        self.token_map = {
            "BSE:SENSEX": {"exchange": "BSE", "token": "99919000", "trading_symbol": "SENSEX", "is_index": True, "strike_step": 100, "expiry_prefix": "SENSEX"},
            "^BSESN": {"exchange": "BSE", "token": "99919000", "trading_symbol": "SENSEX", "is_index": True, "strike_step": 100, "expiry_prefix": "SENSEX"},
            "^NSEI": {"exchange": "NSE", "token": "26000", "trading_symbol": "NIFTY", "is_index": True, "strike_step": 50, "expiry_prefix": "NIFTY"},
            "RELIANCE.NS": {"exchange": "NSE", "token": "2885", "trading_symbol": "RELIANCE-EQ", "is_index": False},
            "TCS.NS": {"exchange": "NSE", "token": "11536", "trading_symbol": "TCS-EQ", "is_index": False},
            "HDFCBANK.NS": {"exchange": "NSE", "token": "1333", "trading_symbol": "HDFCBANK-EQ", "is_index": False},
            "INFY.NS": {"exchange": "NSE", "token": "1594", "trading_symbol": "INFY-EQ", "is_index": False},
        }
        self.scrip_master = None
        self.last_scrip_update = 0
        
        try:
            from SmartApi import SmartConnect
            self.smartApi = SmartConnect(api_key=self.api_key)
        except ImportError:
            logger.error("SmartApi not installed. Run: pip install smartapi-python")
            
    def connect(self) -> bool:
        if not self.smartApi:
            return False
            
        try:
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret).now()
            
            data = self.smartApi.generateSession(self.client_id, self.password, totp)
            if data['status'] == True:
                self.is_connected = True
                logger.info("Successfully connected to Angel One.")
                # Load scrip master for option trading
                self._update_scrip_master()
                return True
            else:
                logger.error(f"Angel One Login Failed: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to Angel One: {str(e)}")
            return False

    def _update_scrip_master(self):
        # Update scrip master if not updated in last 24 hours
        if time.time() - self.last_scrip_update < 86400 and self.scrip_master is not None:
            return
            
        logger.info("Downloading Angel One scrip master...")
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            res = requests.get(url, timeout=10)
            self.scrip_master = res.json()
            self.last_scrip_update = time.time()
            logger.info("Scrip master updated successfully.")
        except Exception as e:
            logger.error(f"Failed to update scrip master: {e}")

    def _get_option_token(self, symbol_pattern: str, exchange: str) -> Optional[Dict[str, str]]:
        if not self.scrip_master:
            return None
            
        # Optimization: Filter by exchange and symbol pattern
        for item in self.scrip_master:
            if item.get('exch_seg') == exchange and symbol_pattern in item.get('symbol', ''):
                return {"token": item['token'], "trading_symbol": item['symbol']}
        return None

    def execute_order(self, symbol: str, quantity: int, order_type: str, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes an order on Angel One.
        order_type: 'BUY' or 'SELL'
        """
        if not self.is_connected:
            logger.error("Not connected to Angel One. Cannot execute order.")
            return {"status": "error", "message": "Not connected"}
            
        token_info = self.token_map.get(symbol)
        if not token_info:
            return {"status": "error", "message": f"Symbol {symbol} not supported for real execution yet."}

        # Handling Index Options (Expiry Trading)
        if token_info.get("is_index"):
            logger.info(f"Indexing detected for {symbol}. Selecting ATM Option...")
            try:
                # 1. Get Live Index Price
                ltp_res = self.smartApi.ltpData(token_info["exchange"], token_info["trading_symbol"], token_info["token"])
                if not ltp_res or not ltp_res.get('status'):
                    return {"status": "error", "message": "Failed to get live index price for strike selection."}
                
                ltp = float(ltp_res['data']['ltp'])
                strike_step = token_info.get("strike_step", 100)
                atm_strike = round(ltp / strike_step) * strike_step
                
                # 2. Determine Option Type (BUY -> CE, SELL -> PE)
                opt_type = "CE" if order_type.upper() == "BUY" else "PE"
                
                # 3. Find latest expiry token (Simplified search)
                # In production, we should filter by specific expiry date. 
                # For today's expiry, we search for SENSEX + STRIKE + CE/PE
                search_pattern = f"{token_info['expiry_prefix']}{int(atm_strike)}{opt_type}"
                option_exchange = "BFO" if token_info["exchange"] == "BSE" else "NFO"
                
                opt_data = self._get_option_token(search_pattern, option_exchange)
                if not opt_data:
                    # Try alternative pattern (some symbols have month/date)
                    # For simplicity in this demo, we'll try a broader search if exact fails
                    logger.warning(f"Exact option match not found for {search_pattern}. Trying broad search...")
                    search_pattern = f"{token_info['expiry_prefix']}"
                    # This would ideally be more precise
                    return {"status": "error", "message": f"Could not find exact ATM Option for {atm_strike} {opt_type}. Please check expiry symbols."}
                
                # Update order params for Option
                trading_symbol = opt_data["trading_symbol"]
                symbol_token = opt_data["token"]
                exchange = option_exchange
                logger.info(f"Selected ATM Option: {trading_symbol} ({symbol_token}) for strike {atm_strike}")
                
            except Exception as e:
                logger.error(f"Error in Option Selection: {e}")
                return {"status": "error", "message": f"Option Selection Error: {str(e)}"}
        else:
            # Standard Equity
            trading_symbol = token_info["trading_symbol"]
            symbol_token = token_info["token"]
            exchange = token_info["exchange"]

        try:
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": trading_symbol,
                "symboltoken": symbol_token,
                "transactiontype": order_type.upper(),
                "exchange": exchange,
                "ordertype": "MARKET" if price is None else "LIMIT",
                "producttype": "INTRADAY" if exchange == "NSE" else "CARRYOVER", # BSE Options often use CARRYOVER/NORMAL
                "duration": "DAY",
                "price": price if price else 0,
                "squareoff": "0",
                "stoploss": "0",
                "quantity": quantity
            }
            orderId = self.smartApi.placeOrder(orderparams)
            
            if orderId and isinstance(orderId, str):
                logger.info(f"Order placed successfully: {orderId}")
                return {"status": "success", "order_id": orderId}
            else:
                logger.error(f"Order placement failed: {orderId}")
                return {"status": "error", "message": str(orderId)}
            
        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_positions(self) -> Dict[str, Any]:
        if not self.is_connected:
            return {}
        try:
            return self.smartApi.position()
        except Exception as e:
            logger.error(f"Failed to fetch positions: {str(e)}")
            return {}
