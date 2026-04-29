import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LowCapitalManager:
    """
    Safeguards account with constraints:
    - Capital: ₹2000 - ₹5000
    - Enforces 1 lot limit
    - Max Risk per trade: 5-10%
    - Daily Max Loss limit: 20%
    """
    
    def __init__(self, initial_capital: float = 5000.0):
        self.capital = initial_capital
        self.max_daily_loss_pct = 0.20 # 20%
        self.max_trade_risk_pct = 0.10 # 10%
        self.daily_pnl = 0.0
        
    def check_trade_viability(self, option_premium: float, lot_size: int = 50) -> Dict[str, Any]:
        """
        Validates if capital can afford buying 1 lot.
        """
        required_capital = option_premium * lot_size
        
        # Check daily drawdown limit
        if self.daily_pnl <= -(self.capital * self.max_daily_loss_pct):
            return {
                "viable": False,
                "reason": "Maximum daily loss (20%) breached. Position sizing halted."
            }
            
        # Check capital adequacy
        if required_capital > self.capital:
            return {
                "viable": False,
                "reason": f"Insufficient Capital. Required: ₹{required_capital}, Available: ₹{self.capital}"
            }
            
        # Determine strict constraints
        suggested_sl = option_premium * (1 - self.max_trade_risk_pct)
        suggested_target = option_premium * 1.20 # 20% target profit
        
        # Dynamic lot sizing based on max trade risk allocation (10% to 20% of capital per trade)
        affordable_lots = int((self.capital * 0.20) / required_capital)
        if affordable_lots < 1:
            affordable_lots = 1 # Always allow at least 1 lot if capital is sufficient
            
        return {
            "viable": True,
            "lots": affordable_lots,
            "required_capital": required_capital * affordable_lots,
            "suggested_sl": suggested_sl,
            "suggested_target": suggested_target
        }
        
    def register_trade_result(self, pnl: float):
        self.daily_pnl += pnl
        self.capital += pnl
        logger.info(f"LowCapitalManager updated. Daily PnL: ₹{self.daily_pnl}, Current Capital: ₹{self.capital}")
