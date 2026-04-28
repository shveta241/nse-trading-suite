from abc import ABC, abstractmethod
from typing import Dict, Any

class Executor(ABC):
    """
    Abstract Base Class for order execution.
    Can be Zerodha, Angel One, or Mock.
    """

    @abstractmethod
    def place_order(self, symbol: str, quantity: int, side: str, order_type: str, price: float = None) -> Dict[str, Any]:
        """
        Places a buy or sell order.
        side: 'BUY' or 'SELL'
        order_type: 'MARKET', 'LIMIT', 'SL'
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancels an open order.
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Checks order status.
        """
        pass
