"""
Risk-Based Position Sizing
Calculate optimal position sizes based on risk metrics
"""

from typing import Dict, Optional
import numpy as np
import pandas as pd
import logging

class PositionSizer:
    """Base class for position sizing strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"PositionSizer.{name}")
    
    def calculate_size(self, capital: float, price: float, **kwargs) -> float:
        """
        Calculate position size.
        
        Args:
            capital: Available capital
            price: Current price
            **kwargs: Additional parameters
        
        Returns:
            Position size (number of units)
        """
        raise NotImplementedError


class FixedFractionalSizing(PositionSizer):
    """Fixed fractional position sizing - simplest approach"""
    
    def __init__(self, fraction: float = 0.02):
        """
        Initialize with risk fraction.
        
        Args:
            fraction: Fraction of capital to risk (default 2%)
        """
        super().__init__("FixedFractional")
        self.fraction = fraction
    
    def calculate_size(self, capital: float, price: float, 
                      stop_loss_pct: float = 0.02, **kwargs) -> float:
        """
        Calculate size based on fixed risk fraction.
        
        Position Size = (Capital * Risk%) / (Price * Stop Loss%)
        """
        risk_amount = capital * self.fraction
        risk_per_unit = price * stop_loss_pct
        
        if risk_per_unit > 0:
            size = risk_amount / risk_per_unit
        else:
            size = 0
        
        return size


class KellyCriterion(PositionSizer):
    """Kelly Criterion - optimal bet sizing"""
    
    def __init__(self, fraction: float = 0.5):
        """
        Initialize Kelly Criterion.
        
        Args:
            fraction: Fraction of Kelly to use (0.5 = Half Kelly, safer)
        """
        super().__init__("KellyCriterion")
        self.fraction = fraction
    
    def calculate_size(self, capital: float, price: float,
                      win_rate: float = 0.55, avg_win: float = 0.05,
                      avg_loss: float = 0.02, **kwargs) -> float:
        """
        Calculate size using Kelly Criterion.
        
        Kelly% = (Win% * Avg Win - Loss% * Avg Loss) / Avg Win
        """
        loss_rate = 1 - win_rate
        
        # Kelly formula
        kelly_pct = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
        
        # Apply fraction (Half Kelly is safer)
        kelly_pct = kelly_pct * self.fraction
        
        # Ensure positive and reasonable
        kelly_pct = max(0, min(kelly_pct, 0.25))  # Cap at 25%
        
        # Calculate position size
        position_value = capital * kelly_pct
        size = position_value / price
        
        return size


class VolatilityBasedSizing(PositionSizer):
    """Size positions inversely to volatility"""
    
    def __init__(self, target_risk: float = 0.02):
        """
        Initialize volatility-based sizing.
        
        Args:
            target_risk: Target risk per trade (default 2%)
        """
        super().__init__("VolatilityBased")
        self.target_risk = target_risk
    
    def calculate_size(self, capital: float, price: float,
                      volatility: float = 0.03, **kwargs) -> float:
        """
        Calculate size based on volatility.
        
        Size = (Capital * Target Risk) / (Price * Volatility)
        """
        if volatility > 0:
            risk_amount = capital * self.target_risk
            size = risk_amount / (price * volatility)
        else:
            size = 0
        
        return size


class ATRBasedSizing(PositionSizer):
    """Size positions based on Average True Range"""
    
    def __init__(self, risk_per_trade: float = 0.02, atr_multiplier: float = 2.0):
        """
        Initialize ATR-based sizing.
        
        Args:
            risk_per_trade: Risk per trade as fraction of capital
            atr_multiplier: ATR multiplier for stop loss
        """
        super().__init__("ATRBased")
        self.risk_per_trade = risk_per_trade
        self.atr_multiplier = atr_multiplier
    
    def calculate_size(self, capital: float, price: float,
                      atr: float = None, data: pd.DataFrame = None, **kwargs) -> float:
        """
        Calculate size based on ATR.
        
        Size = (Capital * Risk%) / (ATR * Multiplier)
        """
        # Calculate ATR if not provided
        if atr is None and data is not None:
            atr = self._calculate_atr(data)
        
        if atr and atr > 0:
            risk_amount = capital * self.risk_per_trade
            stop_distance = atr * self.atr_multiplier
            size = risk_amount / stop_distance
        else:
            size = 0
        
        return size
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(data) < period:
            return 0
        
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        
        tr = []
        for i in range(1, len(data)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr.append(max(tr1, tr2, tr3))
        
        atr = np.mean(tr[-period:]) if len(tr) >= period else 0
        return atr


class RiskBasedPositionSizer:
    """
    Comprehensive position sizing system.
    Combines multiple sizing methods with risk limits.
    """
    
    def __init__(self, capital: float, max_position_pct: float = 0.20,
                 max_risk_per_trade: float = 0.02):
        """
        Initialize position sizer.
        
        Args:
            capital: Total capital
            max_position_pct: Maximum position size as % of capital
            max_risk_per_trade: Maximum risk per trade as % of capital
        """
        self.capital = capital
        self.max_position_pct = max_position_pct
        self.max_risk_per_trade = max_risk_per_trade
        self.logger = logging.getLogger("RiskBasedPositionSizer")
        
        # Available sizing methods
        self.methods = {
            'fixed_fractional': FixedFractionalSizing(max_risk_per_trade),
            'kelly': KellyCriterion(fraction=0.5),
            'volatility': VolatilityBasedSizing(max_risk_per_trade),
            'atr': ATRBasedSizing(max_risk_per_trade)
        }
    
    def calculate_position_size(self, price: float, method: str = 'fixed_fractional',
                               **kwargs) -> Dict:
        """
        Calculate position size with risk limits.
        
        Args:
            price: Current price
            method: Sizing method to use
            **kwargs: Additional parameters for sizing method
        
        Returns:
            Dictionary with size, value, and risk info
        """
        # Get sizing method
        sizer = self.methods.get(method, self.methods['fixed_fractional'])
        
        # Calculate raw size
        raw_size = sizer.calculate_size(self.capital, price, **kwargs)
        
        # Apply position size limit
        max_size = (self.capital * self.max_position_pct) / price
        size = min(raw_size, max_size)
        
        # Calculate position value and risk
        position_value = size * price
        position_pct = position_value / self.capital
        
        # Calculate risk amount
        stop_loss_pct = kwargs.get('stop_loss_pct', 0.02)
        risk_amount = position_value * stop_loss_pct
        risk_pct = risk_amount / self.capital
        
        result = {
            'size': size,
            'value': position_value,
            'position_pct': position_pct,
            'risk_amount': risk_amount,
            'risk_pct': risk_pct,
            'method': method,
            'limited': raw_size > max_size
        }
        
        self.logger.info(f"Position size: {size:.4f} units (${position_value:.2f}, {position_pct*100:.1f}% of capital)")
        
        return result
    
    def calculate_multi_position_sizes(self, positions: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Calculate sizes for multiple positions with total risk limit.
        
        Args:
            positions: Dict of {symbol: {price, method, ...}}
        
        Returns:
            Dict of {symbol: size_info}
        """
        results = {}
        total_risk = 0
        
        for symbol, params in positions.items():
            price = params['price']
            method = params.get('method', 'fixed_fractional')
            
            # Calculate individual position
            size_info = self.calculate_position_size(price, method, **params)
            
            # Check total risk limit
            if total_risk + size_info['risk_pct'] > self.max_risk_per_trade * len(positions):
                # Scale down to fit risk budget
                scale_factor = (self.max_risk_per_trade * len(positions) - total_risk) / size_info['risk_pct']
                size_info['size'] *= scale_factor
                size_info['value'] *= scale_factor
                size_info['risk_amount'] *= scale_factor
                size_info['scaled'] = True
            
            total_risk += size_info['risk_pct']
            results[symbol] = size_info
        
        return results
    
    def get_sizing_summary(self) -> Dict:
        """Get position sizing configuration"""
        return {
            'capital': self.capital,
            'max_position_pct': self.max_position_pct,
            'max_risk_per_trade': self.max_risk_per_trade,
            'available_methods': list(self.methods.keys())
        }
    
    def print_sizing_info(self, symbol: str, size_info: Dict):
        """Print position sizing information"""
        print(f"\n{'='*60}")
        print(f"Position Sizing: {symbol}")
        print(f"{'='*60}")
        print(f"Method: {size_info['method']}")
        print(f"Size: {size_info['size']:.4f} units")
        print(f"Value: ${size_info['value']:,.2f} ({size_info['position_pct']*100:.1f}% of capital)")
        print(f"Risk: ${size_info['risk_amount']:,.2f} ({size_info['risk_pct']*100:.2f}% of capital)")
        
        if size_info.get('limited'):
            print(f"⚠️  Position limited by max position size")
        if size_info.get('scaled'):
            print(f"⚠️  Position scaled to fit risk budget")
        
        print(f"{'='*60}")
