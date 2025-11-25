"""
Sentiment Analysis
Market sentiment scoring and filtering
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
import logging

class SentimentAnalyzer:
    """
    Analyze market sentiment to improve trading decisions.
    Simulates sentiment from multiple sources.
    """
    
    SENTIMENT_LEVELS = {
        'extreme_fear': (-1.0, -0.7),
        'fear': (-0.7, -0.3),
        'neutral': (-0.3, 0.3),
        'greed': (0.3, 0.7),
        'extreme_greed': (0.7, 1.0)
    }
    
    def __init__(self):
        self.logger = logging.getLogger("SentimentAnalyzer")
        self.sentiment_history = []
    
    def calculate_price_sentiment(self, data: pd.DataFrame) -> float:
        """
        Calculate sentiment from price action.
        
        Args:
            data: OHLCV data
        
        Returns:
            Sentiment score (-1 to 1)
        """
        if len(data) < 20:
            return 0.0
        
        # Recent returns
        returns = data['close'].pct_change().tail(20)
        
        # Positive days ratio
        positive_days = (returns > 0).sum() / len(returns)
        
        # Average return
        avg_return = returns.mean()
        
        # Volatility
        volatility = returns.std()
        
        # Combine factors
        sentiment = (positive_days - 0.5) * 2  # -1 to 1
        sentiment += np.clip(avg_return * 100, -0.5, 0.5)  # Adjust for returns
        
        # Reduce confidence in high volatility
        if volatility > 0.03:
            sentiment *= 0.7
        
        return np.clip(sentiment, -1.0, 1.0)
    
    def calculate_volume_sentiment(self, data: pd.DataFrame) -> float:
        """
        Calculate sentiment from volume patterns.
        
        Args:
            data: OHLCV data
        
        Returns:
            Sentiment score (-1 to 1)
        """
        if len(data) < 20:
            return 0.0
        
        recent_volume = data['volume'].tail(10).mean()
        avg_volume = data['volume'].tail(50).mean()
        
        # Volume ratio
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        
        # High volume = more conviction
        if volume_ratio > 1.5:
            return 0.3  # Positive sentiment
        elif volume_ratio < 0.7:
            return -0.2  # Negative sentiment
        else:
            return 0.0
    
    def calculate_momentum_sentiment(self, data: pd.DataFrame) -> float:
        """
        Calculate sentiment from momentum indicators.
        
        Args:
            data: OHLCV data
        
        Returns:
            Sentiment score (-1 to 1)
        """
        if len(data) < 50:
            return 0.0
        
        # RSI-like calculation
        returns = data['close'].pct_change()
        gains = returns.where(returns > 0, 0).tail(14).sum()
        losses = -returns.where(returns < 0, 0).tail(14).sum()
        
        if losses == 0:
            rsi = 100
        else:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))
        
        # Convert RSI to sentiment
        if rsi > 70:
            return 0.5  # Overbought (greed)
        elif rsi < 30:
            return -0.5  # Oversold (fear)
        else:
            return (rsi - 50) / 50  # Normalized
    
    def get_fear_greed_index(self) -> float:
        """
        Simulate Fear & Greed Index.
        In production, this would call external API.
        
        Returns:
            Index value (-1 to 1)
        """
        # Simulate with random but realistic values
        # In production: fetch from Alternative.me API
        base_sentiment = np.random.uniform(-0.3, 0.3)
        return base_sentiment
    
    def get_sentiment_score(self, data: pd.DataFrame) -> Dict:
        """
        Calculate overall sentiment score.
        
        Args:
            data: OHLCV data
        
        Returns:
            Sentiment analysis results
        """
        # Calculate individual sentiments
        price_sentiment = self.calculate_price_sentiment(data)
        volume_sentiment = self.calculate_volume_sentiment(data)
        momentum_sentiment = self.calculate_momentum_sentiment(data)
        fear_greed = self.get_fear_greed_index()
        
        # Weighted average
        overall_sentiment = (
            price_sentiment * 0.35 +
            volume_sentiment * 0.15 +
            momentum_sentiment * 0.30 +
            fear_greed * 0.20
        )
        
        # Classify sentiment level
        sentiment_level = self.classify_sentiment(overall_sentiment)
        
        # Calculate confidence
        # Higher when all indicators agree
        sentiments = [price_sentiment, volume_sentiment, momentum_sentiment, fear_greed]
        std_dev = np.std(sentiments)
        confidence = 1.0 - min(std_dev, 1.0)
        
        result = {
            'overall': overall_sentiment,
            'level': sentiment_level,
            'confidence': confidence,
            'components': {
                'price': price_sentiment,
                'volume': volume_sentiment,
                'momentum': momentum_sentiment,
                'fear_greed': fear_greed
            }
        }
        
        self.sentiment_history.append(result)
        
        return result
    
    def classify_sentiment(self, score: float) -> str:
        """Classify sentiment score into level"""
        for level, (min_val, max_val) in self.SENTIMENT_LEVELS.items():
            if min_val <= score < max_val:
                return level
        return 'neutral'
    
    def should_trade(self, sentiment: Dict) -> bool:
        """
        Determine if should trade based on sentiment.
        
        Args:
            sentiment: Sentiment analysis results
        
        Returns:
            True if should trade
        """
        # Avoid extreme sentiment
        if sentiment['level'] in ['extreme_fear', 'extreme_greed']:
            self.logger.info(f"Avoiding trade: {sentiment['level']}")
            return False
        
        # Require minimum confidence
        if sentiment['confidence'] < 0.5:
            self.logger.info(f"Low sentiment confidence: {sentiment['confidence']:.1%}")
            return False
        
        return True
    
    def get_position_size_adjustment(self, sentiment: Dict) -> float:
        """
        Get position size adjustment based on sentiment.
        
        Args:
            sentiment: Sentiment analysis results
        
        Returns:
            Multiplier (0.5 to 1.2)
        """
        score = sentiment['overall']
        
        if score > 0.5:  # Strong greed
            return 0.8  # Reduce size
        elif score > 0.3:  # Moderate greed
            return 0.9
        elif score > -0.3:  # Neutral
            return 1.0
        elif score > -0.5:  # Moderate fear
            return 1.1  # Slightly increase (contrarian)
        else:  # Strong fear
            return 0.7  # Reduce size
    
    def print_sentiment_analysis(self, sentiment: Dict):
        """Print sentiment analysis"""
        print(f"\n{'='*70}")
        print("SENTIMENT ANALYSIS")
        print(f"{'='*70}")
        
        # Overall
        score = sentiment['overall']
        level = sentiment['level']
        confidence = sentiment['confidence']
        
        emoji = "😱" if 'fear' in level else "🤑" if 'greed' in level else "😐"
        
        print(f"\n{emoji} Overall Sentiment: {score:+.2f} ({level})")
        print(f"   Confidence: {confidence:.1%}")
        
        # Components
        print(f"\n   Components:")
        for name, value in sentiment['components'].items():
            print(f"     {name.capitalize():<15} {value:+.2f}")
        
        # Trading decision
        should_trade = self.should_trade(sentiment)
        adjustment = self.get_position_size_adjustment(sentiment)
        
        print(f"\n   Should Trade: {'✅ Yes' if should_trade else '❌ No'}")
        print(f"   Position Size: {adjustment*100:.0f}% of normal")
        
        print(f"{'='*70}")
