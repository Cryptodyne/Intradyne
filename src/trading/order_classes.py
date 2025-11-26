"""
Advanced Order Classes - Limit and OCO Orders
"""

from typing import Dict, Optional
from datetime import datetime
from src.trading.order_manager import AdvancedOrder, OrderType, OrderStatus, TimeConstraint


class LimitOrder(AdvancedOrder):
    """Buy or sell at specific price limit"""
    
    def __init__(self, order_id: str, symbol: str, quantity: float,
                 limit_price: float, side: str, position_id: Optional[str] = None,
                 time_constraint: TimeConstraint = TimeConstraint.GTC):
        super().__init__(order_id, symbol, quantity, position_id)
        self.limit_price = limit_price
        self.side = side  # 'BUY' or 'SELL'
        self.time_constraint = time_constraint
        self.order_type = OrderType.LIMIT
        
    def check_trigger(self, current_price: float) -> bool:
        """Check if limit order should execute"""
        if self.status != OrderStatus.ACTIVE:
            return False
        
        # Buy limit: execute when price drops to/below limit
        if self.side == 'BUY' and current_price <= self.limit_price:
            self.status = OrderStatus.TRIGGERED
            self.triggered_at = datetime.now()
            return True
        
        # Sell limit: execute when price rises to/above limit
        elif self.side == 'SELL' and current_price >= self.limit_price:
            self.status = OrderStatus.TRIGGERED
            self.triggered_at = datetime.now()
            return True
        
        return False
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'type': self.order_type.value,
            'limit_price': self.limit_price,
            'side': self.side,
            'time_constraint': self.time_constraint.value
        })
        return data


class OCOOrder:
    """One-Cancels-Other: Links two orders (e.g., stop-loss + take-profit)"""
    
    def __init__(self, order_id: str, primary_order: AdvancedOrder, secondary_order: AdvancedOrder):
        self.order_id = order_id
        self.primary = primary_order
        self.secondary = secondary_order
        self.status = OrderStatus.ACTIVE
        self.created_at = datetime.now()
        self.triggered_order = None
    
    def check_trigger(self, current_price: float) -> Optional[str]:
        """
        Check both orders, cancel one if other triggers.
        Returns 'PRIMARY' or 'SECONDARY' if triggered, None otherwise.
        """
        if self.status != OrderStatus.ACTIVE:
            return None
        
        # Check primary
        if self.primary.check_trigger(current_price):
            self.secondary.status = OrderStatus.CANCELED
            self.status = OrderStatus.TRIGGERED
            self.triggered_order = 'PRIMARY'
            return 'PRIMARY'
        
        # Check secondary
        if self.secondary.check_trigger(current_price):
            self.primary.status = OrderStatus.CANCELED
            self.status = OrderStatus.TRIGGERED
            self.triggered_order = 'SECONDARY'
            return 'SECONDARY'
        
        return None
    
    def cancel(self):
        """Cancel both orders"""
        self.primary.status = OrderStatus.CANCELED
        self.secondary.status = OrderStatus.CANCELED
        self.status = OrderStatus.CANCELED
    
    def to_dict(self) -> Dict:
        return {
            'order_id': self.order_id,
            'type': OrderType.OCO.value,
            'status': self.status.value,
            'primary': self.primary.to_dict(),
            'secondary': self.secondary.to_dict(),
            'created_at': self.created_at.isoformat(),
            'triggered_order': self.triggered_order
        }
