"""
Multi-Asset Allocation System
Portfolio allocation strategies for diversification
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime
import logging

class AllocationStrategy:
    """Base class for allocation strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Allocation.{name}")
    
    def calculate_weights(self, assets: List[str], data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Calculate allocation weights for assets.
        
        Args:
            assets: List of asset symbols
            data: Historical data for each asset
        
        Returns:
            Dictionary of {asset: weight}
        """
        raise NotImplementedError


class EqualWeightAllocation(AllocationStrategy):
    """Equal weight allocation - simplest diversification"""
    
    def __init__(self):
        super().__init__("EqualWeight")
    
    def calculate_weights(self, assets: List[str], data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Equal weight for all assets"""
        weight = 1.0 / len(assets)
        return {asset: weight for asset in assets}


class RiskParityAllocation(AllocationStrategy):
    """Risk parity - allocate based on inverse volatility"""
    
    def __init__(self, lookback: int = 30):
        super().__init__("RiskParity")
        self.lookback = lookback
    
    def calculate_weights(self, assets: List[str], data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Allocate inversely proportional to volatility"""
        volatilities = {}
        
        for asset in assets:
            if asset in data and len(data[asset]) >= self.lookback:
                returns = data[asset]['close'].pct_change().dropna()
                vol = returns.tail(self.lookback).std()
                volatilities[asset] = vol if vol > 0 else 0.01
            else:
                volatilities[asset] = 0.01
        
        # Inverse volatility weights
        inv_vols = {asset: 1.0 / vol for asset, vol in volatilities.items()}
        total_inv_vol = sum(inv_vols.values())
        
        # Normalize
        weights = {asset: inv_vol / total_inv_vol for asset, inv_vol in inv_vols.items()}
        
        return weights


class MomentumAllocation(AllocationStrategy):
    """Momentum-based allocation - favor recent winners"""
    
    def __init__(self, lookback: int = 20, min_weight: float = 0.05):
        super().__init__("Momentum")
        self.lookback = lookback
        self.min_weight = min_weight
    
    def calculate_weights(self, assets: List[str], data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Allocate based on recent performance"""
        returns = {}
        
        for asset in assets:
            if asset in data and len(data[asset]) >= self.lookback:
                price_change = (data[asset]['close'].iloc[-1] - data[asset]['close'].iloc[-self.lookback]) / data[asset]['close'].iloc[-self.lookback]
                returns[asset] = max(price_change, 0)  # Only positive momentum
            else:
                returns[asset] = 0
        
        total_return = sum(returns.values())
        
        if total_return > 0:
            # Momentum-based weights
            weights = {asset: ret / total_return for asset, ret in returns.items()}
        else:
            # Fallback to equal weight
            weights = {asset: 1.0 / len(assets) for asset in assets}
        
        # Ensure minimum weight
        for asset in weights:
            if weights[asset] < self.min_weight:
                weights[asset] = self.min_weight
        
        # Renormalize
        total = sum(weights.values())
        weights = {asset: w / total for asset, w in weights.items()}
        
        return weights


class MarketCapAllocation(AllocationStrategy):
    """Market cap weighted allocation"""
    
    def __init__(self, market_caps: Dict[str, float] = None):
        super().__init__("MarketCap")
        self.market_caps = market_caps or {}
    
    def calculate_weights(self, assets: List[str], data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Allocate based on market capitalization"""
        # Default market caps (approximate, in billions)
        default_caps = {
            'BTC/USDT': 800,
            'ETH/USDT': 300,
            'BNB/USDT': 50,
            'SOL/USDT': 40,
            'ADA/USDT': 15,
            'XRP/USDT': 30
        }
        
        caps = {}
        for asset in assets:
            caps[asset] = self.market_caps.get(asset, default_caps.get(asset, 10))
        
        total_cap = sum(caps.values())
        weights = {asset: cap / total_cap for asset, cap in caps.items()}
        
        return weights


class MultiAssetAllocator:
    """
    Multi-asset portfolio allocator.
    Manages allocation across multiple assets using various strategies.
    """
    
    def __init__(self, total_capital: float, strategy: str = 'equal_weight'):
        """
        Initialize allocator.
        
        Args:
            total_capital: Total capital to allocate
            strategy: Allocation strategy name
        """
        self.total_capital = total_capital
        self.strategy_name = strategy
        self.logger = logging.getLogger("MultiAssetAllocator")
        
        # Initialize strategy
        self.strategy = self._create_strategy(strategy)
        
        # Current allocations
        self.allocations: Dict[str, float] = {}
        self.weights: Dict[str, float] = {}
    
    def _create_strategy(self, strategy_name: str) -> AllocationStrategy:
        """Create allocation strategy"""
        strategies = {
            'equal_weight': EqualWeightAllocation(),
            'risk_parity': RiskParityAllocation(),
            'momentum': MomentumAllocation(),
            'market_cap': MarketCapAllocation()
        }
        
        return strategies.get(strategy_name, EqualWeightAllocation())
    
    def calculate_allocation(self, assets: List[str], data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Calculate capital allocation for each asset.
        
        Args:
            assets: List of asset symbols
            data: Historical data for each asset
        
        Returns:
            Dictionary of {asset: capital_amount}
        """
        # Calculate weights
        self.weights = self.strategy.calculate_weights(assets, data)
        
        # Calculate capital allocations
        self.allocations = {
            asset: self.total_capital * weight 
            for asset, weight in self.weights.items()
        }
        
        self.logger.info(f"Calculated allocation using {self.strategy_name}")
        
        return self.allocations
    
    def rebalance(self, current_values: Dict[str, float], target_weights: Dict[str, float] = None) -> Dict[str, float]:
        """
        Calculate rebalancing trades.
        
        Args:
            current_values: Current value of each asset
            target_weights: Target weights (uses current if None)
        
        Returns:
            Dictionary of {asset: trade_amount} (positive = buy, negative = sell)
        """
        if target_weights is None:
            target_weights = self.weights
        
        total_value = sum(current_values.values())
        
        # Calculate target values
        target_values = {
            asset: total_value * weight
            for asset, weight in target_weights.items()
        }
        
        # Calculate trades needed
        trades = {
            asset: target_values.get(asset, 0) - current_values.get(asset, 0)
            for asset in set(list(target_values.keys()) + list(current_values.keys()))
        }
        
        return trades
    
    def get_allocation_summary(self) -> Dict:
        """Get allocation summary"""
        return {
            'strategy': self.strategy_name,
            'total_capital': self.total_capital,
            'num_assets': len(self.allocations),
            'weights': self.weights,
            'allocations': self.allocations
        }
    
    def print_allocation(self):
        """Print allocation details"""
        print("\n" + "="*70)
        print(f"MULTI-ASSET ALLOCATION ({self.strategy_name.upper()})")
        print("="*70)
        
        print(f"\nTotal Capital: ${self.total_capital:,.2f}")
        print(f"Number of Assets: {len(self.allocations)}")
        print(f"\nAllocation:")
        
        for asset, allocation in sorted(self.allocations.items(), key=lambda x: x[1], reverse=True):
            weight = self.weights[asset]
            print(f"  {asset:<15} ${allocation:>10,.2f}  ({weight*100:>5.1f}%)")
        
        print("="*70)


class DynamicAllocator:
    """
    Dynamic allocator that switches strategies based on market conditions.
    """
    
    def __init__(self, total_capital: float):
        self.total_capital = total_capital
        self.logger = logging.getLogger("DynamicAllocator")
        
        # Available strategies
        self.strategies = {
            'equal_weight': EqualWeightAllocation(),
            'risk_parity': RiskParityAllocation(),
            'momentum': MomentumAllocation(),
            'market_cap': MarketCapAllocation()
        }
        
        self.current_strategy = 'equal_weight'
    
    def select_strategy(self, market_condition: str) -> str:
        """
        Select strategy based on market condition.
        
        Args:
            market_condition: 'bull', 'bear', 'sideways', 'volatile'
        
        Returns:
            Strategy name
        """
        strategy_map = {
            'bull': 'momentum',
            'bear': 'risk_parity',
            'sideways': 'equal_weight',
            'volatile': 'risk_parity'
        }
        
        self.current_strategy = strategy_map.get(market_condition, 'equal_weight')
        self.logger.info(f"Selected {self.current_strategy} for {market_condition} market")
        
        return self.current_strategy
    
    def calculate_allocation(self, assets: List[str], data: Dict[str, pd.DataFrame], 
                           market_condition: str = 'sideways') -> Dict[str, float]:
        """Calculate allocation with dynamic strategy selection"""
        strategy_name = self.select_strategy(market_condition)
        strategy = self.strategies[strategy_name]
        
        weights = strategy.calculate_weights(assets, data)
        allocations = {
            asset: self.total_capital * weight 
            for asset, weight in weights.items()
        }
        
        return allocations
