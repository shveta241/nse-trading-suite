import logging
from typing import Dict, Any, Optional
import time
from .base import BaseExecutor
import pyotp

logger = logging.getLogger(__name__)

class AngelOneExecutor(BaseExecutor):
    """
    Executor for Angel One using SmartAPI.
    Requires: smartapi-python installed.
    """
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        self.smartApi = None
        self.is_connected = False
        
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
                return True
            else:
                logger.error(f"Angel One Login Failed: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to Angel One: {str(e)}")
            return False

    def execute_order(self, symbol: str, quantity: int, order_type: str, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes an order on Angel One.
        order_type: 'BUY' or 'SELL'
        """
        if not self.is_connected:
            logger.error("Not connected to Angel One. Cannot execute order.")
            return {"status": "error", "message": "Not connected"}
            
        try:
            # Need to fetch the proper token for the symbol, this is a simplified version
            # Usually you have to look up the token from Angel One's instrument list
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": "3045", # Placeholder token, needs dynamic lookup
                "transactiontype": order_type.upper(),
                "exchange": "NSE",
                "ordertype": "MARKET" if price is None else "LIMIT",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": price if price else 0,
                "squareoff": "0",
                "stoploss": "0",
                "quantity": quantity
            }
            orderId = self.smartApi.placeOrder(orderparams)
            logger.info(f"Order placed successfully: {orderId}")
            return {"status": "success", "order_id": orderId}
            
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
