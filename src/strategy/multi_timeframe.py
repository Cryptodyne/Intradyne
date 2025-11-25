"""
Multi-Timeframe Analysis
Confirm trading signals across multiple timeframes
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

class MultiTimeframeAnalyzer:
    """
    Analyze multiple timeframes to confirm trading signals.
    Reduces false signals and improves win rate.
    """
    
    TIMEFRAMES = ['15m', '1h', '4h', '1d']
    
    def __init__(self, timeframes: List[str] = None, alignment_threshold: int = 3):
        """
        Initialize multi-timeframe analyzer.
        
        Args:
            timeframes: List of timeframes to analyze
            alignment_threshold: Minimum aligned timeframes for signal
        """
        self.timeframes = timeframes or self.TIMEFRAMES
        self.alignment_threshold = alignment_threshold
        self.logger = logging.getLogger("MultiTimeframeAnalyzer")
        
        # Cache for timeframe data
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
    
    def analyze_timeframe(self, data: pd.DataFrame) -> Dict:
        """
        Analyze single timeframe.
        
        Args:
            data: OHLCV data
        
        Returns:
            Analysis results
        """
        if len(data) < 50:
            return {'signal': 0, 'strength': 0, 'trend': 'unknown'}
        
        # Calculate indicators
        sma_20 = data['close'].tail(20).mean()
        sma_50 = data['close'].tail(50).mean()
        current_price = data['close'].iloc[-1]
        
        # Trend direction
        if sma_20 > sma_50:
            trend = 'bullish'
            signal = 1
        elif sma_20 < sma_50:
            trend = 'bearish'
            signal = -1
        else:
            trend = 'neutral'
            signal = 0
        
        # Trend strength (distance between SMAs)
        strength = abs(sma_20 - sma_50) / sma_50 if sma_50 > 0 else 0
        
        # Price position relative to SMAs
        above_sma20 = current_price > sma_20
        above_sma50 = current_price > sma_50
        
        return {
            'signal': signal,
            'trend': trend,
            'strength': strength,
            'above_sma20': above_sma20,
            'above_sma50': above_sma50,
            'sma_20': sma_20,
            'sma_50': sma_50
        }
    
    def analyze_all_timeframes(self, symbol: str, 
                               data_dict: Dict[str, pd.DataFrame]) -> Dict:
        """
        Analyze all timeframes for a symbol.
        
        Args:
            symbol: Trading symbol
            data_dict: Dictionary of {timeframe: data}
        
        Returns:
            Combined analysis
        """
        analyses = {}
        
        for tf in self.timeframes:
            if tf in data_dict and data_dict[tf] is not None:
                analyses[tf] = self.analyze_timeframe(data_dict[tf])
            else:
                self.logger.warning(f"No data for {symbol} {tf}")
                analyses[tf] = {'signal': 0, 'strength': 0, 'trend': 'unknown'}
        
        return analyses
    
    def get_combined_signal(self, analyses: Dict[str, Dict]) -> Dict:
        """
        Combine signals from all timeframes.
        
        Args:
            analyses: Analysis results for each timeframe
        
        Returns:
            Combined signal and metadata
        """
        signals = [a['signal'] for a in analyses.values()]
        strengths = [a['strength'] for a in analyses.values()]
        trends = [a['trend'] for a in analyses.values()]
        
        # Count aligned signals
        bullish_count = sum(1 for s in signals if s > 0)
        bearish_count = sum(1 for s in signals if s < 0)
        
        # Determine overall signal
        if bullish_count >= self.alignment_threshold:
            combined_signal = 'STRONG_BUY'
            signal_value = 1
        elif bullish_count >= 2:
            combined_signal = 'BUY'
            signal_value = 0.5
        elif bearish_count >= self.alignment_threshold:
            combined_signal = 'STRONG_SELL'
            signal_value = -1
        elif bearish_count >= 2:
            combined_signal = 'SELL'
            signal_value = -0.5
        else:
            combined_signal = 'NEUTRAL'
            signal_value = 0
        
        # Calculate confidence (alignment percentage)
        max_aligned = max(bullish_count, bearish_count)
        confidence = max_aligned / len(self.timeframes)
        
        # Average strength
        avg_strength = np.mean([s for s in strengths if s > 0]) if strengths else 0
        
        return {
            'signal': combined_signal,
            'signal_value': signal_value,
            'confidence': confidence,
            'strength': avg_strength,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'aligned': max_aligned >= self.alignment_threshold,
            'timeframe_analyses': analyses
        }
    
    def should_enter_trade(self, combined_signal: Dict, 
                          min_confidence: float = 0.75) -> bool:
        """
        Determine if should enter trade based on multi-timeframe analysis.
        
        Args:
            combined_signal: Combined signal from all timeframes
            min_confidence: Minimum confidence required
        
        Returns:
            True if should enter trade
        """
        # Require alignment and sufficient confidence
        if not combined_signal['aligned']:
            self.logger.info("Timeframes not aligned - skipping trade")
            return False
        
        if combined_signal['confidence'] < min_confidence:
            self.logger.info(f"Confidence too low: {combined_signal['confidence']:.1%}")
            return False
        
        # Must be bullish signal
        if combined_signal['signal_value'] <= 0:
            return False
        
        return True
    
    def get_timeframe_weights(self) -> Dict[str, float]:
        """Get importance weights for each timeframe"""
        return {
            '15m': 0.15,  # Short-term momentum
            '1h': 0.30,   # Entry timing (most important)
            '4h': 0.35,   # Trend confirmation
            '1d': 0.20    # Major trend
        }
    
    def get_weighted_signal(self, analyses: Dict[str, Dict]) -> float:
        """
        Calculate weighted signal based on timeframe importance.
        
        Args:
            analyses: Analysis results for each timeframe
        
        Returns:
            Weighted signal value (-1 to 1)
        """
        weights = self.get_timeframe_weights()
        
        weighted_sum = 0
        total_weight = 0
        
        for tf, analysis in analyses.items():
            if tf in weights:
                weighted_sum += analysis['signal'] * weights[tf]
                total_weight += weights[tf]
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    def print_analysis(self, symbol: str, combined_signal: Dict):
        """Print multi-timeframe analysis"""
        print(f"\n{'='*70}")
        print(f"MULTI-TIMEFRAME ANALYSIS: {symbol}")
        print(f"{'='*70}")
        
        print(f"\nTimeframe Signals:")
        for tf, analysis in combined_signal['timeframe_analyses'].items():
            signal_emoji = "🟢" if analysis['signal'] > 0 else "🔴" if analysis['signal'] < 0 else "⚪"
            print(f"  {signal_emoji} {tf:<6} {analysis['trend']:<10} (strength: {analysis['strength']:.2%})")
        
        print(f"\nCombined Signal: {combined_signal['signal']}")
        print(f"Confidence: {combined_signal['confidence']:.1%}")
        print(f"Alignment: {combined_signal['bullish_count']}/{len(self.timeframes)} bullish")
        print(f"Should Trade: {'✅ Yes' if self.should_enter_trade(combined_signal) else '❌ No'}")
        
        print(f"{'='*70}")
