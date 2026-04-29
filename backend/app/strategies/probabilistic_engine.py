import logging
import pandas as pd
from typing import Dict, Any
from .base import Strategy
from app.data.option_chain import OptionChainAnalyzer
from app.data.sentiment_engine import SentimentEngine

logger = logging.getLogger(__name__)

class ProbabilisticEngineStrategy(Strategy):
    """
    Combines:
    1. Technical Score (40%)
    2. Option Chain Score (30%)
    3. Sentiment Score (20%)
    4. Global Market Score (10%)
    
    Only takes trades when Confidence Score > 70%.
    Includes special Expiry Day scalping logic.
    """
    
    def __init__(self, expiry_mode: bool = False):
        super().__init__(name="ProbabilisticEngineStrategy")
        self.expiry_mode = expiry_mode
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes multi-candle DataFrame.
        """
        df = df.copy()
        signals = []
        
        for idx, row in df.iterrows():
            current_data = row.to_dict()
            sig = self._calculate_decision(current_data)
            signals.append(sig)
            
        df['signal'] = signals
        return df

    def check_live_signal(self, current_data: Dict[str, Any]) -> int:
        """
        Calculates signal for the latest live data point.
        """
        return self._calculate_decision(current_data)

    def _calculate_decision(self, data: Dict[str, Any]) -> int:
        """
        Returns: 1 for Buy, -1 for Sell, 0 for Neutral
        """
        # 1. Technical Score (Max 40 points)
        tech_score = 0
        close = data.get('close', 0)
        vwap = data.get('vwap', close)
        rsi = data.get('rsi_14', 50)
        ema_9 = data.get('ema_9', close)
        ema_20 = data.get('ema_20', close)
        ema_50 = data.get('ema_50', close)
        
        # Bullish conditions
        if close > vwap: tech_score += 10
        if rsi > 60: tech_score += 10
        if ema_9 > ema_20: tech_score += 10
        if ema_20 > ema_50: tech_score += 10
        
        # Bearish conditions
        if close < vwap: tech_score -= 10
        if rsi < 40: tech_score -= 10
        if ema_9 < ema_20: tech_score -= 10
        if ema_20 < ema_50: tech_score -= 10
        
        # 2. Option Chain Score (Max 30 points)
        oc_score = 0
        oc_analysis = OptionChainAnalyzer.analyze_chain([], close) # uses fallback
        oc_signal = oc_analysis.get('signal', 'NEUTRAL')
        pcr = oc_analysis.get('pcr', 1.0)
        
        if oc_signal == 'BULLISH': oc_score += 20
        elif oc_signal == 'MILDLY_BULLISH': oc_score += 10
        elif oc_signal == 'BEARISH': oc_score -= 20
        elif oc_signal == 'MILDLY_BEARISH': oc_score -= 10
        
        if pcr > 1.2: oc_score += 10
        elif pcr < 0.7: oc_score -= 10
        
        # 3. Sentiment Score (Max 20 points)
        sent_analysis = SentimentEngine.analyze_news_sentiment()
        sent_score = (sent_analysis.get('score', 0.0) / 100.0) * 20.0
        
        # 4. Global Market Score (Max 10 points)
        global_raw_score = SentimentEngine.get_global_markets_score()
        global_score = (global_raw_score / 100.0) * 10.0
        
        # Aggregate Confidence Score (-100 to 100)
        # Normalize scores safely
        total_confidence = tech_score + oc_score + sent_score + global_score
        
        logger.info(f"AI Probabilistic Score: {total_confidence:.2f} (Tech: {tech_score}, OC: {oc_score}, Sent: {sent_score:.1f}, Global: {global_score:.1f})")
        
        # Expiry Mode logic overrides
        if self.expiry_mode:
            # Scalping condition - needs faster reaction
            if total_confidence > 50:
                return 1 # Buy (Call option ATM/ITM)
            elif total_confidence < -50:
                return -1 # Sell (Put option ATM/ITM)
            return 0
            
        # Normal Mode requires > 70% confidence
        if total_confidence >= 70.0:
            return 1 # Strong Buy
        elif total_confidence <= -70.0:
            return -1 # Strong Sell
            
        return 0
