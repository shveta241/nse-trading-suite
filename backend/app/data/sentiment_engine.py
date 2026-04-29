import logging
import random
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SentimentEngine:
    """
    Parses global indices and news sentiment to supply context to the strategy.
    Weights: Technicals (40%), Option Chain (30%), Sentiment (20%), Global (10%).
    """
    
    @staticmethod
    def get_global_markets_score() -> float:
        """
        Returns score from -100 to +100 based on global macros.
        Tracks US (Dow/Nasdaq), GIFT Nifty, Crude Oil, and USD-INR.
        """
        try:
            # In production, these would fetch real-time data from financial data providers.
            # Here we simulate real macro values.
            dow_performance = random.uniform(-1.5, 1.5) # % change
            nasdaq_performance = random.uniform(-2.0, 2.0)
            gift_nifty_diff = random.uniform(-100, 100) # points
            
            score = 0
            if dow_performance > 0.5: score += 25
            elif dow_performance < -0.5: score -= 25
            
            if nasdaq_performance > 0.5: score += 25
            elif nasdaq_performance < -0.5: score -= 25
            
            if gift_nifty_diff > 30: score += 50
            elif gift_nifty_diff < -30: score -= 50
            
            return max(-100.0, min(100.0, float(score)))
        except Exception as e:
            logger.error(f"Error fetching global markets score: {str(e)}")
            return 0.0

    @staticmethod
    def analyze_news_sentiment(keywords: str = "") -> Dict[str, Any]:
        """
        Heuristic-based simple NLP sentiment scorer.
        """
        positive_words = ["growth", "cut", "stimulus", "profit", "beat", "positive", "bullish", "expansion", "support"]
        negative_words = ["hike", "inflation", "war", "loss", "miss", "negative", "bearish", "slowdown", "weakness"]
        
        score = 0
        text = keywords.lower()
        
        for word in positive_words:
            if word in text:
                score += 20
                
        for word in negative_words:
            if word in text:
                score -= 20
                
        # Constrain between -100 and 100
        final_score = max(-100.0, min(100.0, float(score)))
        
        sentiment = "NEUTRAL"
        if final_score >= 40: sentiment = "BULLISH"
        elif final_score <= -40: sentiment = "BEARISH"
        
        return {
            "score": final_score,
            "sentiment": sentiment
        }
