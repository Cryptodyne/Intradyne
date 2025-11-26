"""
Technical Indicators Module
Provides RSI, MACD, Bollinger Bands, and other technical analysis tools.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        prices: Series of closing prices
        period: RSI period (default 14)
    
    Returns:
        RSI value (0-100)
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral if insufficient data
    
    # Calculate price changes
    delta = prices.diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Calculate average gains and losses
    avg_gain = gains.rolling(window=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period).mean().iloc[-1]
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: Series of closing prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)
    
    Returns:
        (macd_line, signal_line, histogram)
    """
    if len(prices) < slow + signal:
        return 0.0, 0.0, 0.0
    
    # Calculate EMAs
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    # MACD line
    macd_line = ema_fast - ema_slow
    
    # Signal line
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    # Histogram
    histogram = macd_line - signal_line
    
    return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: Series of closing prices
        period: Moving average period (default 20)
        std_dev: Number of standard deviations (default 2)
    
    Returns:
        (upper_band, middle_band, lower_band)
    """
    if len(prices) < period:
        current = prices.iloc[-1]
        return current * 1.02, current, current * 0.98
    
    # Calculate middle band (SMA)
    middle = prices.rolling(window=period).mean().iloc[-1]
    
    # Calculate standard deviation
    std = prices.rolling(window=period).std().iloc[-1]
    
    # Calculate bands
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    return upper, middle, lower


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """
    Calculate Average True Range (ATR) for volatility measurement.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: ATR period (default 14)
    
    Returns:
        ATR value
    """
    if len(close) < period + 1:
        return 0.0
    
    # Calculate True Range
    high_low = high - low
    high_close = abs(high - close.shift())
    low_close = abs(low - close.shift())
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # Calculate ATR
    atr = true_range.rolling(window=period).mean().iloc[-1]
    
    return atr


def calculate_ema(prices: pd.Series, period: int) -> float:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: Series of prices
        period: EMA period
    
    Returns:
        EMA value
    """
    if len(prices) < period:
        return prices.mean()
    
    return prices.ewm(span=period, adjust=False).mean().iloc[-1]


def calculate_volume_sma(volumes: pd.Series, period: int = 20) -> float:
    """
    Calculate Simple Moving Average of volume.
    
    Args:
        volumes: Series of volume data
        period: SMA period (default 20)
    
    Returns:
        Volume SMA value
    """
    if len(volumes) < period:
        return volumes.mean()
    
    return volumes.rolling(window=period).mean().iloc[-1]


class TechnicalAnalyzer:
    """
    Comprehensive technical analysis for trading signals.
    """
    
    def __init__(self):
        self.indicators = {}
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze price data and calculate all technical indicators.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume, timestamp
        
        Returns:
            Dictionary of indicator values and signals
        """
        if len(df) < 30:
            return self._get_default_indicators()
        
        close = df['close']
        high = df['high'] if 'high' in df.columns else close
        low = df['low'] if 'low' in df.columns else close
        volume = df['volume'] if 'volume' in df.columns else pd.Series([0] * len(df))
        
        # Calculate indicators
        rsi = calculate_rsi(close)
        macd_line, signal_line, histogram = calculate_macd(close)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close)
        atr = calculate_atr(high, low, close)
        
        current_price = close.iloc[-1]
        
        # Calculate signals
        indicators = {
            # Raw values
            'rsi': rsi,
            'macd': macd_line,
            'macd_signal': signal_line,
            'macd_histogram': histogram,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'atr': atr,
            'current_price': current_price,
            
            # Interpreted signals
            'rsi_signal': self._get_rsi_signal(rsi),
            'macd_signal': 'BULLISH' if histogram > 0 else 'BEARISH',
            'bb_position': self._get_bb_position(current_price, bb_upper, bb_middle, bb_lower),
            'trend': self._get_trend(close),
            'volatility': self._get_volatility_level(atr, current_price),
            
            # Volume
            'volume_avg': calculate_volume_sma(volume),
            'volume_ratio': volume.iloc[-1] / calculate_volume_sma(volume) if calculate_volume_sma(volume) > 0 else 1.0,
            
            # Composite score
            'technical_score': self._calculate_technical_score(rsi, histogram, current_price, bb_lower, bb_upper)
        }
        
        self.indicators = indicators
        return indicators
    
    def _get_default_indicators(self) -> Dict:
        """Return neutral indicators when data is insufficient."""
        return {
            'rsi': 50.0,
            'macd': 0.0,
            'macd_signal': 0.0,
            'macd_histogram': 0.0,
            'bb_upper': 0.0,
            'bb_middle': 0.0,
            'bb_lower': 0.0,
            'atr': 0.0,
            'current_price': 0.0,
            'rsi_signal': 'NEUTRAL',
            'macd_signal': 'NEUTRAL',
            'bb_position': 'MIDDLE',
            'trend': 'SIDEWAYS',
            'volatility': 'MEDIUM',
            'volume_avg': 0.0,
            'volume_ratio': 1.0,
            'technical_score': 0.0
        }
    
    def _get_rsi_signal(self, rsi: float) -> str:
        """Interpret RSI value."""
        if rsi > 70:
            return 'OVERBOUGHT'
        elif rsi < 30:
            return 'OVERSOLD'
        elif rsi > 55:
            return 'BULLISH'
        elif rsi < 45:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
    
    def _get_bb_position(self, price: float, upper: float, middle: float, lower: float) -> str:
        """Determine price position relative to Bollinger Bands."""
        if price > upper:
            return 'ABOVE_UPPER'
        elif price < lower:
            return 'BELOW_LOWER'
        elif price > middle:
            return 'UPPER_HALF'
        else:
            return 'LOWER_HALF'
    
    def _get_trend(self, prices: pd.Series) -> str:
        """Determine overall trend."""
        if len(prices) < 20:
            return 'SIDEWAYS'
        
        # Calculate short and long term EMAs
        ema_short = calculate_ema(prices, 10)
        ema_long = calculate_ema(prices, 20)
        
        diff_pct = (ema_short - ema_long) / ema_long
        
        if diff_pct > 0.02:
            return 'STRONG_UP'
        elif diff_pct > 0.005:
            return 'UP'
        elif diff_pct < -0.02:
            return 'STRONG_DOWN'
        elif diff_pct < -0.005:
            return 'DOWN'
        else:
            return 'SIDEWAYS'
    
    def _get_volatility_level(self, atr: float, price: float) -> str:
        """Determine volatility level."""
        if price == 0:
            return 'MEDIUM'
        
        atr_pct = (atr / price) * 100
        
        if atr_pct > 3.0:
            return 'HIGH'
        elif atr_pct > 1.5:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _calculate_technical_score(self, rsi: float, macd_hist: float, price: float, bb_lower: float, bb_upper: float) -> float:
        """
        Calculate composite technical score (-1 to +1).
        Positive = bullish, Negative = bearish
        """
        score = 0.0
        
        # RSI component (-0.3 to +0.3)
        if rsi < 30:
            score += 0.3  # Oversold = bullish
        elif rsi > 70:
            score -= 0.3  # Overbought = bearish
        else:
            score += (50 - rsi) / 100  # Gradual
        
        # MACD component (-0.4 to +0.4)
        macd_contribution = min(max(macd_hist / 100, -0.4), 0.4)
        score += macd_contribution
        
        # Bollinger Band component (-0.3 to +0.3)
        if bb_upper > bb_lower and bb_lower > 0:
            bb_range = bb_upper - bb_lower
            bb_position = (price - bb_lower) / bb_range
            
            if bb_position < 0.2:
                score += 0.3  # Near lower band = bullish
            elif bb_position > 0.8:
                score -= 0.3  # Near upper band = bearish
        
        return max(min(score, 1.0), -1.0)
