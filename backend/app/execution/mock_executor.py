import uuid
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
from app.execution.base import Executor
from app.utils.logger import get_logger

logger = get_logger("MockExecutor")

class MockExecutor(Executor):
    """
    Mock execution for backtesting and paper trading.
    Simulates placing and filling orders.
    """

    def __init__(self, initial_capital: float = 5000.0, persistence_file: str = "mock_state.json"):
        self.persistence_file = persistence_file
        self.capital = initial_capital
        self.positions: Dict[str, Dict[str, Any]] = {}  # symbol -> {qty, avg_price}
        self.order_history: List[Dict[str, Any]] = []
        self.open_orders: Dict[str, Dict[str, Any]] = {}
        self._load_state()

    def _load_state(self):
        import os, json
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, 'r') as f:
                    state = json.load(f)
                    self.capital = state.get('capital', self.capital)
                    self.positions = state.get('positions', {})
                    
                    # Backward compatibility and validation
                    for sym, val in list(self.positions.items()):
                        if isinstance(val, (int, float)):
                            self.positions[sym] = {"qty": int(val), "avg_price": 0.0}
                            
                    self.order_history = state.get('order_history', [])
                    logger.info(f"Mock state loaded from {self.persistence_file}")
            except Exception as e:
                logger.error(f"Error loading mock state: {e}")

    def _save_state(self):
        import json
        try:
            state = {
                'capital': self.capital,
                'positions': self.positions,
                'order_history': self.order_history
            }
            # Handle non-serializable objects in order_history (like datetime)
            def serializer(obj):
                if isinstance(obj, (datetime, pd.Timestamp)):
                    return obj.isoformat()
                return str(obj)

            with open(self.persistence_file, 'w') as f:
                json.dump(state, f, default=serializer)
        except Exception as e:
            logger.error(f"Error saving mock state: {e}")

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

        self._save_state()
        return order_record

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.open_orders:
            logger.info(f"Mock Order Cancelled: {order_id}")
            order = self.open_orders.pop(order_id)
            order['status'] = 'CANCELLED'
            self._save_state()
            return True
        return False

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        for order in self.order_history:
            if order['order_id'] == order_id:
                return order
        return {}

    def _update_position(self, symbol: str, quantity: int, side: str, fill_price: float):
        pos = self.positions.get(symbol, {"qty": 0, "avg_price": 0.0})
        current_qty = pos["qty"]
        current_avg = pos["avg_price"]
        
        if side == 'BUY':
            new_qty = current_qty + quantity
            if new_qty > 0:
                # Update average price for long positions
                if current_qty >= 0:
                    new_avg = ((current_qty * current_avg) + (quantity * fill_price)) / new_qty
                else:
                    # Closing a short position
                    new_avg = current_avg if new_qty < 0 else fill_price
            else:
                new_avg = current_avg if new_qty != 0 else 0.0
                
            self.positions[symbol] = {"qty": new_qty, "avg_price": new_avg}
            self.capital -= (quantity * fill_price)
        elif side == 'SELL':
            new_qty = current_qty - quantity
            if new_qty < 0:
                # Update average price for short positions
                if current_qty <= 0:
                    new_avg = ((abs(current_qty) * current_avg) + (quantity * fill_price)) / abs(new_qty)
                else:
                    # Closing a long position
                    new_avg = current_avg if new_qty > 0 else fill_price
            else:
                new_avg = current_avg if new_qty != 0 else 0.0
                
            self.positions[symbol] = {"qty": new_qty, "avg_price": new_avg}
            self.capital += (quantity * fill_price)

        logger.info(f"Updated Position for {symbol}: {self.positions[symbol]['qty']} units @ {self.positions[symbol]['avg_price']}. Remaining Capital: {self.capital}")
        self._save_state()
