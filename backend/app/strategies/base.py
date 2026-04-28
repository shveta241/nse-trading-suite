from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, List

class Strategy(ABC):
    """
    Base class for all trading strategies.
    """
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a DataFrame with technical indicators and returns signals.
        Returns the DataFrame with an added 'signal' column.
        1: Buy, -1: Sell, 0: Hold/None
        """
        pass
        
    @abstractmethod
    def check_live_signal(self, current_data: Dict[str, Any]) -> int:
        """
        Check for a signal in real-time based on the latest data tick.
        Returns 1 for Buy, -1 for Sell, 0 for None.
        """
        pass
