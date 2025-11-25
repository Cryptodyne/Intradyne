"""
Advanced Risk Manager
ATR-based stops, volume confirmation, trailing stops
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
import logging

class AdvancedRiskManager:
    """
    Advanced risk management with dynamic stops and filters.
    Improves win rate and reduces drawdown.
    """
    
    def __init__(self, atr_period: int = 14, atr_multiplier: float = 2.0,
                 volume_threshold: float = 1.5, volume_lookback: int = 20):
        """
        Initialize advanced risk manager.
        
        Args:
            atr_period: Period for ATR calculation
            atr_multiplier: Multiplier for ATR-based stops
            volume_threshold: Volume spike threshold (1.5 = 150% of average)
            volume_lookback: Periods for volume average
        """
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.volume_threshold = volume_threshold
        self.volume_lookback = volume_lookback
        self.logger = logging.getLogger("AdvancedRiskManager")
        
        # Trailing stop tracking
        self.trailing_stops: Dict[str, Dict] = {}
    
    def calculate_atr(self, data: pd.DataFrame, period: int = None) -> float:
        """
        Calculate Average True Range.
        
        Args:
            data: OHLC data
            period: ATR period (uses default if None)
        
        Returns:
            ATR value
        """
        if period is None:
            period = self.atr_period
        
        if len(data) < period:
            return 0
        
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        
        # Calculate True Range
        tr = []
        for i in range(1, len(data)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr.append(max(tr1, tr2, tr3))
        
        # Average True Range
        atr = np.mean(tr[-period:]) if len(tr) >= period else 0
        return atr
    
    def calculate_atr_stop_loss(self, entry_price: float, atr: float,
                                direction: str = 'long',
                                min_stop_pct: float = 0.02,
                                max_stop_pct: float = 0.05) -> float:
        """
        Calculate ATR-based stop loss.
        
        Args:
            entry_price: Entry price
            atr: Current ATR value
            direction: 'long' or 'short'
            min_stop_pct: Minimum stop loss percentage
            max_stop_pct: Maximum stop loss percentage
        
        Returns:
            Stop loss price
        """
        # Calculate ATR-based stop distance
        stop_distance = atr * self.atr_multiplier
        
        # Convert to percentage
        stop_pct = stop_distance / entry_price
        
        # Clamp to min/max
        stop_pct = max(min_stop_pct, min(stop_pct, max_stop_pct))
        
        # Calculate stop price
        if direction == 'long':
            stop_price = entry_price * (1 - stop_pct)
        else:  # short
            stop_price = entry_price * (1 + stop_pct)
        
        self.logger.debug(f"ATR stop: {stop_price:.2f} ({stop_pct*100:.1f}% from entry)")
        
        return stop_price
    
    def check_volume_confirmation(self, data: pd.DataFrame,
                                  threshold: float = None,
                                  lookback: int = None) -> bool:
        """
        Check if current volume confirms the signal.
        
        Args:
            data: OHLC data with volume
            threshold: Volume threshold multiplier
            lookback: Periods for average calculation
        
        Returns:
            True if volume is confirmed
        """
        if threshold is None:
            threshold = self.volume_threshold
        if lookback is None:
            lookback = self.volume_lookback
        
        if len(data) < lookback + 1:
            return False
        
        current_volume = data['volume'].iloc[-1]
        avg_volume = data['volume'].iloc[-lookback-1:-1].mean()
        
        is_confirmed = current_volume >= avg_volume * threshold
        
        if is_confirmed:
            self.logger.debug(f"Volume confirmed: {current_volume:.0f} vs avg {avg_volume:.0f}")
        else:
            self.logger.debug(f"Volume too low: {current_volume:.0f} vs avg {avg_volume:.0f}")
        
        return is_confirmed
    
    def initialize_trailing_stop(self, symbol: str, entry_price: float,
                                 direction: str = 'long',
                                 activation_pct: float = 0.03,
                                 trail_distance_pct: float = 0.02):
        """
        Initialize trailing stop for a position.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            direction: 'long' or 'short'
            activation_pct: Profit % to activate trailing stop
            trail_distance_pct: Distance % to trail
        """
        self.trailing_stops[symbol] = {
            'entry_price': entry_price,
            'direction': direction,
            'activation_pct': activation_pct,
            'trail_distance_pct': trail_distance_pct,
            'highest_price': entry_price if direction == 'long' else entry_price,
            'lowest_price': entry_price if direction == 'short' else entry_price,
            'stop_price': None,
            'activated': False
        }
        
        self.logger.info(f"Initialized trailing stop for {symbol} at {entry_price}")
    
    def update_trailing_stop(self, symbol: str, current_price: float) -> Optional[float]:
        """
        Update trailing stop based on current price.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
        
        Returns:
            Current stop price or None if not activated
        """
        if symbol not in self.trailing_stops:
            return None
        
        stop_info = self.trailing_stops[symbol]
        entry_price = stop_info['entry_price']
        direction = stop_info['direction']
        
        if direction == 'long':
            # Update highest price
            if current_price > stop_info['highest_price']:
                stop_info['highest_price'] = current_price
            
            # Check if trailing stop should activate
            profit_pct = (current_price - entry_price) / entry_price
            
            if not stop_info['activated'] and profit_pct >= stop_info['activation_pct']:
                stop_info['activated'] = True
                self.logger.info(f"Trailing stop activated for {symbol} at {profit_pct*100:.1f}% profit")
            
            # Update stop price if activated
            if stop_info['activated']:
                stop_info['stop_price'] = stop_info['highest_price'] * (1 - stop_info['trail_distance_pct'])
        
        else:  # short
            # Update lowest price
            if current_price < stop_info['lowest_price']:
                stop_info['lowest_price'] = current_price
            
            # Check if trailing stop should activate
            profit_pct = (entry_price - current_price) / entry_price
            
            if not stop_info['activated'] and profit_pct >= stop_info['activation_pct']:
                stop_info['activated'] = True
                self.logger.info(f"Trailing stop activated for {symbol} at {profit_pct*100:.1f}% profit")
            
            # Update stop price if activated
            if stop_info['activated']:
                stop_info['stop_price'] = stop_info['lowest_price'] * (1 + stop_info['trail_distance_pct'])
        
        return stop_info['stop_price']
    
    def check_stop_hit(self, symbol: str, current_price: float) -> Tuple[bool, str]:
        """
        Check if stop loss was hit.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
        
        Returns:
            (stop_hit, reason)
        """
        if symbol not in self.trailing_stops:
            return False, ""
        
        stop_info = self.trailing_stops[symbol]
        
        if stop_info['stop_price'] is None:
            return False, ""
        
        direction = stop_info['direction']
        
        if direction == 'long':
            if current_price <= stop_info['stop_price']:
                return True, "trailing_stop"
        else:  # short
            if current_price >= stop_info['stop_price']:
                return True, "trailing_stop"
        
        return False, ""
    
    def remove_trailing_stop(self, symbol: str):
        """Remove trailing stop for closed position"""
        if symbol in self.trailing_stops:
            del self.trailing_stops[symbol]
            self.logger.info(f"Removed trailing stop for {symbol}")
    
    def calculate_dynamic_position_size(self, capital: float, price: float,
                                       atr: float, risk_pct: float = 0.02) -> float:
        """
        Calculate position size based on ATR risk.
        
        Args:
            capital: Available capital
            price: Current price
            atr: Current ATR
            risk_pct: Risk per trade (default 2%)
        
        Returns:
            Position size in units
        """
        risk_amount = capital * risk_pct
        stop_distance = atr * self.atr_multiplier
        
        if stop_distance > 0:
            size = risk_amount / stop_distance
        else:
            size = 0
        
        return size
    
    def get_risk_metrics(self, symbol: str) -> Dict:
        """Get current risk metrics for a position"""
        if symbol not in self.trailing_stops:
            return {}
        
        stop_info = self.trailing_stops[symbol]
        
        return {
            'entry_price': stop_info['entry_price'],
            'current_stop': stop_info['stop_price'],
            'highest_price': stop_info['highest_price'],
            'trailing_activated': stop_info['activated'],
            'direction': stop_info['direction']
        }
