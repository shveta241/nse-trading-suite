import uuid
from datetime import datetime
from typing import Dict, Any, List
from app.execution.base import Executor
from app.utils.logger import get_logger

logger = get_logger("MockExecutor")

class MockExecutor(Executor):
    """
    Mock execution for backtesting and paper trading.
    Simulates placing and filling orders.
    """

    def __init__(self, initial_capital: float = 100000.0):
        self.capital = initial_capital
        self.positions: Dict[str, int] = {}  # symbol -> quantity
        self.order_history: List[Dict[str, Any]] = []
        self.open_orders: Dict[str, Dict[str, Any]] = {}

    def place_order(self, symbol: str, quantity: int, side: str, order_type: str, price: float = None) -> Dict[str, Any]:
        order_id = str(uuid.uuid4())[:8]
        logger.info(f"Mock Order Placed: {side} {quantity} {symbol} via {order_type} @ {price}")
        
        # Simulate instant fill for Market orders
        if order_type == 'MARKET':
            order_status = 'FILLED'
            fill_price = price if price else 100.0  # fallback
            self._update_position(symbol, quantity, side, fill_price)
        else:
            order_status = 'OPEN'
            fill_price = None

        order_record = {
            "order_id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "order_type": order_type,
            "price": price,
            "fill_price": fill_price,
            "status": order_status,
            "timestamp": datetime.now()
        }

        self.order_history.append(order_record)
        if order_status == 'OPEN':
            self.open_orders[order_id] = order_record

        return order_record

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.open_orders:
            logger.info(f"Mock Order Cancelled: {order_id}")
            order = self.open_orders.pop(order_id)
            order['status'] = 'CANCELLED'
            return True
        return False

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        for order in self.order_history:
            if order['order_id'] == order_id:
                return order
        return {}

    def _update_position(self, symbol: str, quantity: int, side: str, fill_price: float):
        current_qty = self.positions.get(symbol, 0)
        
        if side == 'BUY':
            self.positions[symbol] = current_qty + quantity
            self.capital -= (quantity * fill_price)
        elif side == 'SELL':
            self.positions[symbol] = current_qty - quantity
            self.capital += (quantity * fill_price)

        logger.info(f"Updated Position for {symbol}: {self.positions[symbol]} units. Remaining Capital: {self.capital}")
