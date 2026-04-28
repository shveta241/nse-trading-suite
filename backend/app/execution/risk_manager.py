from app.utils.logger import get_logger

logger = get_logger("RiskManager")

class RiskManager:
    """
    Manages Risk, Position Sizing, Stop Loss, and Take Profit.
    """

    def __init__(
        self, 
        max_risk_per_trade_pct: float = 0.5, 
        default_stop_loss_pct: float = 0.4, 
        default_target_pct: float = 0.8
    ):
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_target_pct = default_target_pct

    def calculate_position_size(self, capital: float, entry_price: float, stop_loss_pct: float = None) -> int:
        """
        Calculates position size based on risk per trade.
        Formula: Quantity = (Capital * Max Risk %) / (Entry Price * Stop Loss %)
        """
        if stop_loss_pct is None:
            stop_loss_pct = self.default_stop_loss_pct

        # Risk amount in currency
        risk_amount = capital * (self.max_risk_per_trade_pct / 100.0)
        
        # Risk per share
        risk_per_share = entry_price * (stop_loss_pct / 100.0)

        if risk_per_share <= 0:
            logger.warning("Risk per share is <= 0. Returning 0 quantity.")
            return 0

        quantity = int(risk_amount // risk_per_share)
        
        # Ensure we don't exceed total capital
        max_qty_possible = int(capital // entry_price)
        final_qty = min(quantity, max_qty_possible)

        logger.info(f"Calculated position size: {final_qty} units (Risk: {self.max_risk_per_trade_pct}%, Capital: {capital})")
        return final_qty

    def get_trade_exits(self, entry_price: float, signal_type: int, stop_loss_pct: float = None, target_pct: float = None):
        """
        Calculates Stop Loss and Take Profit price targets.
        signal_type: 1 for Long/Buy, -1 for Short/Sell
        """
        if stop_loss_pct is None:
            stop_loss_pct = self.default_stop_loss_pct
        if target_pct is None:
            target_pct = self.default_target_pct

        if signal_type == 1:  # Long
            stop_loss_price = entry_price * (1.0 - (stop_loss_pct / 100.0))
            target_price = entry_price * (1.0 + (target_pct / 100.0))
        elif signal_type == -1:  # Short
            stop_loss_price = entry_price * (1.0 + (stop_loss_pct / 100.0))
            target_price = entry_price * (1.0 - (target_pct / 100.0))
        else:
            return None, None

        logger.debug(f"Calculated exit prices - SL: {stop_loss_price}, Target: {target_price}")
        return stop_loss_price, target_price
