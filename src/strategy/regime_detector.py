"""
Market Regime Detector
Identify market conditions and adapt trading strategy
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
import logging

class RegimeDetector:
    """
    Detect market regimes and provide regime-specific parameters.
    Helps avoid unfavorable market conditions.
    """
    
    # Regime definitions
    REGIMES = {
        'bull_low_vol': {
            'description': 'Strong uptrend, low volatility',
            'strategy': 'trend_following',
            'favorable': True,
            'position_size_multiplier': 1.2
        },
        'bull_high_vol': {
            'description': 'Uptrend with high volatility',
            'strategy': 'trend_following',
            'favorable': True,
            'position_size_multiplier': 0.8
        },
        'bear_low_vol': {
            'description': 'Downtrend, low volatility',
            'strategy': 'avoid',
            'favorable': False,
            'position_size_multiplier': 0.0
        },
        'bear_high_vol': {
            'description': 'Downtrend with high volatility',
            'strategy': 'avoid',
            'favorable': False,
            'position_size_multiplier': 0.0
        },
        'sideways_low_vol': {
            'description': 'Range-bound, low volatility',
            'strategy': 'mean_reversion',
            'favorable': True,
            'position_size_multiplier': 0.7
        },
        'sideways_high_vol': {
            'description': 'Choppy, high volatility',
            'strategy': 'avoid',
            'favorable': False,
            'position_size_multiplier': 0.0
        }
    }
    
    def __init__(self, lookback: int = 20, vol_threshold: float = 0.025):
        """
        Initialize regime detector.
        
        Args:
            lookback: Periods for regime calculation
            vol_threshold: Volatility threshold (2.5% daily)
        """
        self.lookback = lookback
        self.vol_threshold = vol_threshold
        self.logger = logging.getLogger("RegimeDetector")
        
        self.current_regime = None
        self.regime_history = []
    
    def detect_regime(self, data: pd.DataFrame) -> str:
        """
        Detect current market regime.
        
        Args:
            data: OHLC price data
        
        Returns:
            Regime name
        """
        if len(data) < self.lookback:
            return 'unknown'
        
        # Calculate returns
        returns = data['close'].pct_change().dropna()
        recent_returns = returns.tail(self.lookback)
        
        # Calculate metrics
        mean_return = recent_returns.mean()
        volatility = recent_returns.std()
        
        # Determine trend
        if mean_return > 0.001:  # 0.1% daily
            trend = 'bull'
        elif mean_return < -0.001:
            trend = 'bear'
        else:
            trend = 'sideways'
        
        # Determine volatility level
        if volatility > self.vol_threshold:
            vol_level = 'high_vol'
        else:
            vol_level = 'low_vol'
        
        # Combine to get regime
        regime = f"{trend}_{vol_level}"
        
        # Update state
        self.current_regime = regime
        self.regime_history.append({
            'regime': regime,
            'mean_return': mean_return,
            'volatility': volatility
        })
        
        self.logger.info(f"Detected regime: {regime} (return={mean_return*100:.2f}%, vol={volatility*100:.2f}%)")
        
        return regime
    
    def should_trade(self, regime: str = None) -> bool:
        """
        Determine if should trade in current regime.
        
        Args:
            regime: Regime name (uses current if None)
        
        Returns:
            True if should trade
        """
        if regime is None:
            regime = self.current_regime
        
        if regime not in self.REGIMES:
            return False
        
        return self.REGIMES[regime]['favorable']
    
    def get_regime_strategy(self, regime: str = None) -> str:
        """
        Get recommended strategy for regime.
        
        Args:
            regime: Regime name (uses current if None)
        
        Returns:
            Strategy name
        """
        if regime is None:
            regime = self.current_regime
        
        if regime not in self.REGIMES:
            return 'avoid'
        
        return self.REGIMES[regime]['strategy']
    
    def get_position_size_multiplier(self, regime: str = None) -> float:
        """
        Get position size multiplier for regime.
        
        Args:
            regime: Regime name (uses current if None)
        
        Returns:
            Multiplier (0.0 = no trading, 1.0 = normal, >1.0 = increase)
        """
        if regime is None:
            regime = self.current_regime
        
        if regime not in self.REGIMES:
            return 0.0
        
        return self.REGIMES[regime]['position_size_multiplier']
    
    def get_regime_parameters(self, regime: str = None) -> Dict:
        """
        Get all parameters for regime.
        
        Args:
            regime: Regime name (uses current if None)
        
        Returns:
            Dictionary of parameters
        """
        if regime is None:
            regime = self.current_regime
        
        if regime not in self.REGIMES:
            return {
                'favorable': False,
                'strategy': 'avoid',
                'position_size_multiplier': 0.0
            }
        
        return self.REGIMES[regime].copy()
    
    def get_regime_description(self, regime: str = None) -> str:
        """Get human-readable regime description"""
        if regime is None:
            regime = self.current_regime
        
        if regime not in self.REGIMES:
            return "Unknown regime"
        
        return self.REGIMES[regime]['description']
    
    def get_regime_stats(self) -> Dict:
        """Get statistics about regime history"""
        if not self.regime_history:
            return {}
        
        regimes = [r['regime'] for r in self.regime_history]
        
        # Count occurrences
        regime_counts = {}
        for regime in regimes:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        # Calculate percentages
        total = len(regimes)
        regime_pcts = {r: count/total for r, count in regime_counts.items()}
        
        return {
            'current_regime': self.current_regime,
            'total_periods': total,
            'regime_counts': regime_counts,
            'regime_percentages': regime_pcts,
            'favorable_pct': sum(1 for r in regimes if self.REGIMES.get(r, {}).get('favorable', False)) / total
        }
    
    def print_regime_analysis(self):
        """Print regime analysis"""
        stats = self.get_regime_stats()
        
        if not stats:
            print("No regime history available")
            return
        
        print("\n" + "="*70)
        print("MARKET REGIME ANALYSIS")
        print("="*70)
        
        print(f"\nCurrent Regime: {stats['current_regime']}")
        print(f"Description: {self.get_regime_description()}")
        print(f"Should Trade: {'✅ Yes' if self.should_trade() else '❌ No'}")
        
        print(f"\nRegime Distribution ({stats['total_periods']} periods):")
        for regime, pct in sorted(stats['regime_percentages'].items(), key=lambda x: x[1], reverse=True):
            count = stats['regime_counts'][regime]
            favorable = "✅" if self.REGIMES[regime]['favorable'] else "❌"
            print(f"  {favorable} {regime:<20} {count:>4} ({pct*100:>5.1f}%)")
        
        print(f"\nFavorable Conditions: {stats['favorable_pct']*100:.1f}% of time")
        
        print("="*70)
