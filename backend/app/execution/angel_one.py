import logging
from typing import Dict, Any, Optional, List
import time
import requests
import pandas as pd
from datetime import datetime

from .base import Executor
import pyotp

from app.utils.logger import get_logger
logger = get_logger("AngelOneExecutor")

class AngelOneExecutor(Executor):
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
            "NIFTY 50": {"exchange": "NSE", "token": "26000", "trading_symbol": "Nifty 50", "is_index": True, "strike_step": 50, "expiry_prefix": "NIFTY", "name": "NIFTY"},
            "SENSEX": {"exchange": "BSE", "token": "99919000", "trading_symbol": "SENSEX", "is_index": True, "strike_step": 100, "expiry_prefix": "SENSEX", "name": "SENSEX"},
            "^NSEI": {"exchange": "NSE", "token": "26000", "trading_symbol": "Nifty 50", "is_index": True, "strike_step": 50, "expiry_prefix": "NIFTY", "name": "NIFTY"},
            "^BSESN": {"exchange": "BSE", "token": "99919000", "trading_symbol": "SENSEX", "is_index": True, "strike_step": 100, "expiry_prefix": "SENSEX", "name": "SENSEX"},
            "RELIANCE.NS": {"exchange": "NSE", "token": "2885", "trading_symbol": "RELIANCE-EQ", "is_index": False, "lotsize": "1", "name": "RELIANCE"},
            "TCS.NS": {"exchange": "NSE", "token": "11536", "trading_symbol": "TCS-EQ", "is_index": False, "lotsize": "1", "name": "TCS"},
            "HDFCBANK.NS": {"exchange": "NSE", "token": "1333", "trading_symbol": "HDFCBANK-EQ", "is_index": False, "lotsize": "1", "name": "HDFCBANK"},
            "INFY.NS": {"exchange": "NSE", "token": "1594", "trading_symbol": "INFY-EQ", "is_index": False, "lotsize": "1", "name": "INFY"},
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

    def _get_option_token(self, name: str, strike: int, opt_type: str, exchange: str) -> Optional[Dict[str, str]]:
        if not self.scrip_master:
            return None
            
        # Filter for relevant options
        options = []
        for item in self.scrip_master:
            if (item.get('exch_seg') == exchange and 
                item.get('name') == name and 
                str(int(float(item.get('strike', 0)))) == str(strike * 100) and 
                item.get('symbol', '').endswith(opt_type)):
                options.append(item)
        
        if not options:
            return None
            
        # Sort by expiry to get the nearest one
        try:
            # Expiry format is usually 'DDMMMYYYY' like '08MAY2026'
            options.sort(key=lambda x: datetime.strptime(x['expiry'], '%d%b%Y') if x.get('expiry') else datetime.max)
        except Exception as e:
            logger.warning(f"Error sorting expiries: {e}")
            
        selected = options[0]
        return {
            "token": selected['token'], 
            "trading_symbol": selected['symbol'],
            "lot_size": int(selected.get('lotsize', 1))
        }

    def place_order(self, symbol: str, quantity: int, side: str, order_type: str = "MARKET", price: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes an order on Angel One.
        side: 'BUY' or 'SELL'
        """
        order_type_val = side.upper() # Map 'side' to Angel's transactiontype
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
                opt_type = "CE" if order_type_val == "BUY" else "PE"
                
                # 3. Find latest expiry token using robust matching
                option_exchange = "BFO" if token_info["exchange"] == "BSE" else "NFO"
                
                opt_data = self._get_option_token(token_info['name'], int(atm_strike), opt_type, option_exchange)
                if not opt_data:
                    return {"status": "error", "message": f"Could not find exact ATM Option for {token_info['name']} {atm_strike} {opt_type}."}
                
                # Update order params for Option
                trading_symbol = opt_data["trading_symbol"]
                symbol_token = opt_data["token"]
                exchange = option_exchange
                current_lot_size = opt_data["lot_size"]
                logger.info(f"Selected ATM Option: {trading_symbol} ({symbol_token}) for strike {atm_strike} with lot size {current_lot_size}")
                
            except Exception as e:
                logger.error(f"Error in Option Selection: {e}")
                return {"status": "error", "message": f"Option Selection Error: {str(e)}"}
        else:
            # Standard Equity
            trading_symbol = token_info["trading_symbol"]
            symbol_token = token_info["token"]
            exchange = token_info["exchange"]

        # Lot size adjustment to multiples
        if 'current_lot_size' in locals():
            min_lot = current_lot_size
        else:
            lot_map = {"NIFTY": 25, "SENSEX": 10} # Fallbacks
            min_lot = int(token_info.get('lotsize', lot_map.get(token_info.get('name', ''), 1)))
            
        if quantity < min_lot:
            quantity = min_lot
        else:
            quantity = (quantity // min_lot) * min_lot
            
        logger.info(f"Final Adjusted Quantity: {quantity} (Min Lot: {min_lot})")

        try:
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": str(trading_symbol),
                "symboltoken": str(symbol_token),
                "transactiontype": str(order_type_val),
                "exchange": str(exchange),
                "ordertype": str(order_type).upper(),
                "producttype": "INTRADAY" if exchange in ["NSE", "BSE"] else "CARRYFORWARD",
                "duration": "DAY",
                "price": str(price) if order_type.upper() == "LIMIT" and price and price > 0 else "0",
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(quantity)
            }
            logger.info(f"Placing {order_type} Order with params: {orderparams}")
            orderId = self.smartApi.placeOrder(orderparams)
            
            if orderId and isinstance(orderId, str):
                logger.info(f"Order placed successfully: {orderId}")
                return {
                    "status": "success", 
                    "order_id": orderId,
                    "trading_symbol": str(trading_symbol)
                }
            elif isinstance(orderId, dict):
                msg = orderId.get('message', 'Unknown broker error')
                logger.error(f"Order placement failed: {msg}")
                return {"status": "error", "message": msg}
            else:
                logger.error(f"Order placement failed with unexpected response: {orderId}")
                return {"status": "error", "message": f"Broker Error: {orderId}"}
            
        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            return {"status": "error", "message": f"Execution Exception: {str(e)}"}

    def cancel_order(self, order_id: str) -> bool:
        if not self.is_connected: return False
        try:
            res = self.smartApi.cancelOrder("NORMAL", order_id)
            return res.get('status') == True
        except: return False

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return {"status": "unknown", "order_id": order_id}

    def get_positions(self) -> Dict[str, Any]:
        if not self.is_connected:
            return {}
        try:
            return self.smartApi.position()
        except Exception as e:
            logger.error(f"Failed to fetch positions: {str(e)}")
            return {}
