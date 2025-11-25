"""
Portfolio Rebalancing System
Automated rebalancing to maintain target allocations
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import logging

class RebalancingStrategy:
    """Base class for rebalancing strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Rebalancing.{name}")
    
    def should_rebalance(self, current_weights: Dict[str, float], 
                        target_weights: Dict[str, float], **kwargs) -> bool:
        """
        Determine if rebalancing is needed.
        
        Args:
            current_weights: Current portfolio weights
            target_weights: Target portfolio weights
            **kwargs: Additional parameters
        
        Returns:
            True if rebalancing needed
        """
        raise NotImplementedError


class ThresholdRebalancing(RebalancingStrategy):
    """Rebalance when drift exceeds threshold"""
    
    def __init__(self, threshold: float = 0.05):
        """
        Initialize threshold rebalancing.
        
        Args:
            threshold: Maximum allowed drift (default 5%)
        """
        super().__init__("Threshold")
        self.threshold = threshold
    
    def should_rebalance(self, current_weights: Dict[str, float],
                        target_weights: Dict[str, float], **kwargs) -> bool:
        """Check if any asset drifted beyond threshold"""
        max_drift = 0
        
        for asset in target_weights:
            current = current_weights.get(asset, 0)
            target = target_weights[asset]
            drift = abs(current - target)
            max_drift = max(max_drift, drift)
        
        needs_rebalance = max_drift > self.threshold
        
        if needs_rebalance:
            self.logger.info(f"Rebalancing triggered: max drift {max_drift*100:.1f}%")
        
        return needs_rebalance


class CalendarRebalancing(RebalancingStrategy):
    """Rebalance on fixed schedule"""
    
    def __init__(self, frequency: str = 'monthly'):
        """
        Initialize calendar rebalancing.
        
        Args:
            frequency: 'daily', 'weekly', 'monthly', 'quarterly'
        """
        super().__init__("Calendar")
        self.frequency = frequency
        self.last_rebalance = None
    
    def should_rebalance(self, current_weights: Dict[str, float],
                        target_weights: Dict[str, float], **kwargs) -> bool:
        """Check if rebalancing period has passed"""
        now = datetime.now()
        
        if self.last_rebalance is None:
            self.last_rebalance = now
            return True
        
        time_since_last = now - self.last_rebalance
        
        # Determine if enough time has passed
        if self.frequency == 'daily':
            should_rebalance = time_since_last >= timedelta(days=1)
        elif self.frequency == 'weekly':
            should_rebalance = time_since_last >= timedelta(weeks=1)
        elif self.frequency == 'monthly':
            should_rebalance = time_since_last >= timedelta(days=30)
        elif self.frequency == 'quarterly':
            should_rebalance = time_since_last >= timedelta(days=90)
        else:
            should_rebalance = False
        
        if should_rebalance:
            self.last_rebalance = now
            self.logger.info(f"Rebalancing triggered: {self.frequency} schedule")
        
        return should_rebalance


class VolatilityRebalancing(RebalancingStrategy):
    """Rebalance more frequently during high volatility"""
    
    def __init__(self, base_threshold: float = 0.05, vol_multiplier: float = 2.0):
        """
        Initialize volatility-based rebalancing.
        
        Args:
            base_threshold: Base drift threshold
            vol_multiplier: Multiplier for high volatility
        """
        super().__init__("Volatility")
        self.base_threshold = base_threshold
        self.vol_multiplier = vol_multiplier
    
    def should_rebalance(self, current_weights: Dict[str, float],
                        target_weights: Dict[str, float],
                        volatility: float = 0.02, **kwargs) -> bool:
        """Adjust threshold based on volatility"""
        # Higher volatility = lower threshold (more frequent rebalancing)
        if volatility > 0.05:  # High volatility
            threshold = self.base_threshold / self.vol_multiplier
        else:
            threshold = self.base_threshold
        
        max_drift = max(abs(current_weights.get(asset, 0) - target_weights[asset])
                       for asset in target_weights)
        
        needs_rebalance = max_drift > threshold
        
        if needs_rebalance:
            self.logger.info(f"Rebalancing triggered: drift {max_drift*100:.1f}% (threshold {threshold*100:.1f}%)")
        
        return needs_rebalance


class PortfolioRebalancer:
    """
    Comprehensive portfolio rebalancing system.
    Calculates trades needed to restore target allocations.
    """
    
    def __init__(self, strategy: str = 'threshold', **strategy_params):
        """
        Initialize rebalancer.
        
        Args:
            strategy: Rebalancing strategy ('threshold', 'calendar', 'volatility')
            **strategy_params: Parameters for the strategy
        """
        self.strategy_name = strategy
        self.logger = logging.getLogger("PortfolioRebalancer")
        
        # Create strategy
        self.strategy = self._create_strategy(strategy, **strategy_params)
        
        # Rebalancing history
        self.rebalance_history: List[Dict] = []
    
    def _create_strategy(self, strategy_name: str, **params) -> RebalancingStrategy:
        """Create rebalancing strategy"""
        if strategy_name == 'threshold':
            return ThresholdRebalancing(params.get('threshold', 0.05))
        elif strategy_name == 'calendar':
            return CalendarRebalancing(params.get('frequency', 'monthly'))
        elif strategy_name == 'volatility':
            return VolatilityRebalancing(
                params.get('base_threshold', 0.05),
                params.get('vol_multiplier', 2.0)
            )
        else:
            return ThresholdRebalancing()
    
    def calculate_rebalance_trades(self, current_values: Dict[str, float],
                                   target_weights: Dict[str, float],
                                   min_trade_value: float = 100) -> Dict[str, Dict]:
        """
        Calculate trades needed to rebalance portfolio.
        
        Args:
            current_values: Current value of each asset
            target_weights: Target allocation weights
            min_trade_value: Minimum trade value to execute
        
        Returns:
            Dictionary of {asset: {action, amount, value}}
        """
        total_value = sum(current_values.values())
        
        # Calculate current weights
        current_weights = {
            asset: value / total_value if total_value > 0 else 0
            for asset, value in current_values.items()
        }
        
        # Check if rebalancing needed
        if not self.strategy.should_rebalance(current_weights, target_weights):
            self.logger.info("No rebalancing needed")
            return {}
        
        # Calculate target values
        target_values = {
            asset: total_value * weight
            for asset, weight in target_weights.items()
        }
        
        # Calculate trades
        trades = {}
        
        for asset in set(list(current_values.keys()) + list(target_values.keys())):
            current_value = current_values.get(asset, 0)
            target_value = target_values.get(asset, 0)
            
            trade_value = target_value - current_value
            
            # Skip small trades
            if abs(trade_value) < min_trade_value:
                continue
            
            trades[asset] = {
                'action': 'BUY' if trade_value > 0 else 'SELL',
                'amount': abs(trade_value),
                'value': trade_value,
                'current': current_value,
                'target': target_value
            }
        
        # Log rebalancing
        self._log_rebalance(current_weights, target_weights, trades)
        
        return trades
    
    def _log_rebalance(self, current_weights: Dict[str, float],
                      target_weights: Dict[str, float],
                      trades: Dict[str, Dict]):
        """Log rebalancing event"""
        rebalance_event = {
            'timestamp': datetime.now(),
            'strategy': self.strategy_name,
            'current_weights': current_weights.copy(),
            'target_weights': target_weights.copy(),
            'num_trades': len(trades),
            'total_trade_value': sum(abs(t['value']) for t in trades.values())
        }
        
        self.rebalance_history.append(rebalance_event)
        self.logger.info(f"Rebalancing: {len(trades)} trades, ${rebalance_event['total_trade_value']:,.2f}")
    
    def get_drift_analysis(self, current_weights: Dict[str, float],
                          target_weights: Dict[str, float]) -> Dict:
        """Analyze portfolio drift"""
        drifts = {}
        max_drift = 0
        avg_drift = 0
        
        for asset in target_weights:
            current = current_weights.get(asset, 0)
            target = target_weights[asset]
            drift = current - target
            
            drifts[asset] = {
                'current': current,
                'target': target,
                'drift': drift,
                'drift_pct': (drift / target * 100) if target > 0 else 0
            }
            
            max_drift = max(max_drift, abs(drift))
            avg_drift += abs(drift)
        
        avg_drift = avg_drift / len(target_weights) if target_weights else 0
        
        return {
            'drifts': drifts,
            'max_drift': max_drift,
            'avg_drift': avg_drift,
            'needs_rebalance': max_drift > 0.05
        }
    
    def print_rebalance_plan(self, trades: Dict[str, Dict]):
        """Print rebalancing plan"""
        if not trades:
            print("\n✅ Portfolio is balanced - no trades needed")
            return
        
        print("\n" + "="*70)
        print("REBALANCING PLAN")
        print("="*70)
        
        total_buy = sum(t['amount'] for t in trades.values() if t['action'] == 'BUY')
        total_sell = sum(t['amount'] for t in trades.values() if t['action'] == 'SELL')
        
        print(f"\nTotal Trades: {len(trades)}")
        print(f"Total Buy: ${total_buy:,.2f}")
        print(f"Total Sell: ${total_sell:,.2f}")
        
        print(f"\nTrades:")
        for asset, trade in sorted(trades.items()):
            action_symbol = "📈" if trade['action'] == 'BUY' else "📉"
            print(f"  {action_symbol} {trade['action']:<4} {asset:<15} ${trade['amount']:>10,.2f}")
            print(f"     Current: ${trade['current']:>10,.2f} → Target: ${trade['target']:>10,.2f}")
        
        print("="*70)
    
    def get_rebalance_summary(self) -> Dict:
        """Get rebalancing summary"""
        return {
            'strategy': self.strategy_name,
            'total_rebalances': len(self.rebalance_history),
            'last_rebalance': self.rebalance_history[-1] if self.rebalance_history else None
        }
