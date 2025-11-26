"""
Order Manager for Advanced Trading
Handles stop-loss, take-profit, trailing stops, and conditional orders.
Monitors prices and triggers orders automatically.
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path


class OrderType(Enum):
    """Supported order types"""
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"
    CONDITIONAL = "CONDITIONAL"
    LIMIT = "LIMIT"
    OCO = "OCO"


class OrderStatus(Enum):
    """Order lifecycle states"""
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class TimeConstraint(Enum):
    """Time constraints for orders"""
    GTC = "GTC"  # Good-Til-Cancelled
    DAY = "DAY"  # Cancel at end of day


class AdvancedOrder:
    """Base class for advanced orders"""
    
    def __init__(self, order_id: str, symbol: str, quantity: float, 
                 position_id: Optional[str] = None):
        self.order_id = order_id
        self.symbol = symbol
        self.quantity = quantity
        self.position_id = position_id
        self.status = OrderStatus.ACTIVE
        self.created_at = datetime.now()
        self.triggered_at = None
        
    def to_dict(self) -> Dict:
        """Serialize to dict"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'position_id': self.position_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None
        }


class StopLossOrder(AdvancedOrder):
    """Automatically sell when price drops below threshold"""
    
    def __init__(self, order_id: str, symbol: str, quantity: float,
                 stop_price: float, position_id: Optional[str] = None):
        super().__init__(order_id, symbol, quantity, position_id)
        self.stop_price = stop_price
        self.order_type = OrderType.STOP_LOSS
        
    def check_trigger(self, current_price: float) -> bool:
        """Check if stop-loss should trigger"""
        if self.status != OrderStatus.ACTIVE:
            return False
            
        if current_price <= self.stop_price:
            self.status = OrderStatus.TRIGGERED
            self.triggered_at = datetime.now()
            return True
        return False
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'type': self.order_type.value,
            'stop_price': self.stop_price
        })
        return data


class TakeProfitOrder(AdvancedOrder):
    """Automatically sell when profit target is reached"""
    
    def __init__(self, order_id: str, symbol: str, quantity: float,
                 target_price: float, position_id: Optional[str] = None):
        super().__init__(order_id, symbol, quantity, position_id)
        self.target_price = target_price
        self.order_type = OrderType.TAKE_PROFIT
        
    def check_trigger(self, current_price: float) -> bool:
        """Check if take-profit should trigger"""
        if self.status != OrderStatus.ACTIVE:
            return False
            
        if current_price >= self.target_price:
            self.status = OrderStatus.TRIGGERED
            self.triggered_at = datetime.now()
            return True
        return False
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'type': self.order_type.value,
            'target_price': self.target_price
        })
        return data


class TrailingStopOrder(AdvancedOrder):
    """Dynamic stop that follows price upward"""
    
    def __init__(self, order_id: str, symbol: str, quantity: float,
                 initial_price: float, trail_percent: float, 
                 position_id: Optional[str] = None):
        super().__init__(order_id, symbol, quantity, position_id)
        self.trail_percent = trail_percent  # e.g., 0.03 = 3%
        self.highest_price = initial_price
        self.current_stop = initial_price * (1 - trail_percent)
        self.order_type = OrderType.TRAILING_STOP
        
    def update(self, current_price: float):
        """Update trailing stop based on new price"""
        if self.status != OrderStatus.ACTIVE:
            return
            
        # Update highest price
        if current_price > self.highest_price:
            self.highest_price = current_price
            self.current_stop = current_price * (1 - self.trail_percent)
    
    def check_trigger(self, current_price: float) -> bool:
        """Check if trailing stop should trigger"""
        if self.status != OrderStatus.ACTIVE:
            return False
        
        # Update first
        self.update(current_price)
        
        # Check trigger
        if current_price <= self.current_stop:
            self.status = OrderStatus.TRIGGERED
            self.triggered_at = datetime.now()
            return True
        return False
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'type': self.order_type.value,
            'trail_percent': self.trail_percent,
            'highest_price': self.highest_price,
            'current_stop': self.current_stop
        })
        return data


class ConditionalOrder(AdvancedOrder):
    """Execute based on conditions (sentiment, price, etc.)"""
    
    def __init__(self, order_id: str, symbol: str, quantity: float,
                 condition_type: str, threshold: float, action: str):
        super().__init__(order_id, symbol, quantity)
        self.condition_type = condition_type  # 'SENTIMENT_BULLISH', 'PRICE_ABOVE', etc.
        self.threshold = threshold
        self.action = action  # 'BUY' or 'SELL'
        self.order_type = OrderType.CONDITIONAL
        
    def check_trigger(self, **kwargs) -> bool:
        """Check if condition is met"""
        if self.status != OrderStatus.ACTIVE:
            return False
        
        if self.condition_type == 'PRICE_ABOVE':
            current_price = kwargs.get('current_price', 0)
            if current_price >= self.threshold:
                self.status = OrderStatus.TRIGGERED
                self.triggered_at = datetime.now()
                return True
                
        elif self.condition_type == 'PRICE_BELOW':
            current_price = kwargs.get('current_price', 0)
            if current_price <= self.threshold:
                self.status = OrderStatus.TRIGGERED
                self.triggered_at = datetime.now()
                return True
        
        elif self.condition_type == 'SENTIMENT_BULLISH':
            sentiment = kwargs.get('sentiment', 0)
            if sentiment >= self.threshold:
                self.status = OrderStatus.TRIGGERED
                self.triggered_at = datetime.now()
                return True
        
        elif self.condition_type == 'SENTIMENT_BEARISH':
            sentiment = kwargs.get('sentiment', 0)
            if sentiment <= -self.threshold:
                self.status = OrderStatus.TRIGGERED
                self.triggered_at = datetime.now()
                return True
        
        return False
    
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'type': self.order_type.value,
            'condition_type': self.condition_type,
            'threshold': self.threshold,
            'action': self.action
        })
        return data


class OrderManager:
    """Manages all advanced orders and monitors triggers"""
    
    def __init__(self):
        self.orders: List[AdvancedOrder] = []
        self.order_counter = 0
        
    def add_stop_loss(self, symbol: str, quantity: float, stop_price: float,
                     position_id: Optional[str] = None) -> str:
        """Add a stop-loss order"""
        order_id = f"SL_{self.order_counter:04d}"
        self.order_counter += 1
        
        order = StopLossOrder(order_id, symbol, quantity, stop_price, position_id)
        self.orders.append(order)
        return order_id
    
    def add_take_profit(self, symbol: str, quantity: float, target_price: float,
                       position_id: Optional[str] = None) -> str:
        """Add a take-profit order"""
        order_id = f"TP_{self.order_counter:04d}"
        self.order_counter += 1
        
        order = TakeProfitOrder(order_id, symbol, quantity, target_price, position_id)
        self.orders.append(order)
        return order_id
    
    def add_trailing_stop(self, symbol: str, quantity: float, 
                         initial_price: float, trail_percent: float,
                         position_id: Optional[str] = None) -> str:
        """Add a trailing stop order"""
        order_id = f"TS_{self.order_counter:04d}"
        self.order_counter += 1
        
        order = TrailingStopOrder(order_id, symbol, quantity, initial_price, 
                                 trail_percent, position_id)
        self.orders.append(order)
        return order_id
    
    def add_conditional(self, symbol: str, quantity: float,
                       condition_type: str, threshold: float, action: str) -> str:
        """Add a conditional order"""
        order_id = f"COND_{self.order_counter:04d}"
        self.order_counter += 1
        
        order = ConditionalOrder(order_id, symbol, quantity, 
                                condition_type, threshold, action)
        self.orders.append(order)
        return order_id
    
    def check_all_orders(self, prices: Dict[str, float], **kwargs) -> List[Dict]:
        """
        Check all orders for triggers.
        
        Args:
            prices: {'BTC/USDT': 96500.0, 'ETH/USDT': 2890.0, ...}
            **kwargs: Additional context (sentiment, etc.)
            
        Returns:
            List of triggered orders
        """
        triggered = []
        
        for order in self.orders:
            if order.status != OrderStatus.ACTIVE:
                continue
            
            symbol = order.symbol
            current_price = prices.get(symbol)
            
            if current_price is None:
                continue
            
            # Check trigger based on order type
            if isinstance(order, (StopLossOrder, TakeProfitOrder)):
                if order.check_trigger(current_price):
                    triggered.append(order.to_dict())
                    
            elif isinstance(order, TrailingStopOrder):
                if order.check_trigger(current_price):
                    triggered.append(order.to_dict())
                    
            elif isinstance(order, ConditionalOrder):
                if order.check_trigger(current_price=current_price, **kwargs):
                    triggered.append(order.to_dict())
        
        return triggered
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        for order in self.orders:
            if order.order_id == order_id and order.status == OrderStatus.ACTIVE:
                order.status = OrderStatus.CANCELED
                return True
        return False
    
    def get_active_orders(self) -> List[Dict]:
        """Get all active orders"""
        return [order.to_dict() for order in self.orders 
                if order.status == OrderStatus.ACTIVE]
    
    def get_triggered_orders(self) -> List[Dict]:
        """Get all triggered orders"""
        return [order.to_dict() for order in self.orders 
                if order.status == OrderStatus.TRIGGERED]
    
    def clear_triggered(self):
        """Remove triggered orders from active list"""
        self.orders = [order for order in self.orders 
                      if order.status != OrderStatus.TRIGGERED]

    def save_to_file(self, filepath: str = "orders/active_orders.json"):
        """Save active orders to JSON file."""
        import json
        import os
        from pathlib import Path
        
        Path("orders").mkdir(exist_ok=True)
        
        data = {
            'counter': self.order_counter,
            'orders': [o.to_dict() for o in self.orders if o.status == OrderStatus.ACTIVE],
            'oco_orders': [o.to_dict() for o in getattr(self, 'oco_orders', []) if o.status == OrderStatus.ACTIVE]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filepath: str = "orders/active_orders.json"):
        """Load active orders from JSON file."""
        import json
        import os
        
        if not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.order_counter = data.get('counter', 0)
            # Note: Full reconstruction requires parsing types. 
            # For now we just load counter to avoid ID collisions.
            # In a full implementation, we would recreate objects here.
        except Exception as e:
            print(f"Error loading orders: {e}")

    def add_limit_order(self, symbol: str, quantity: float, limit_price: float, side: str,
                       position_id: Optional[str] = None, time_constraint=None) -> str:
        """Add a limit order."""
        from src.trading.order_classes import LimitOrder, TimeConstraint
        
        order_id = f"LMT_{self.order_counter:04d}"
        self.order_counter += 1
        
        tc = time_constraint or TimeConstraint.GTC
        order = LimitOrder(order_id, symbol, quantity, limit_price, side, position_id, tc)
        self.orders.append(order)
        self.save_to_file()
        return order_id

    def add_oco_order(self, symbol: str, quantity: float, stop_price: float, 
                     target_price: float, position_id: Optional[str] = None) -> str:
        """Add OCO (One-Cancels-Other) order."""
        from src.trading.order_classes import OCOOrder, StopLossOrder, TakeProfitOrder
        
        order_id = f"OCO_{self.order_counter:04d}"
        self.order_counter += 2
        
        sl = StopLossOrder(f"{order_id}_SL", symbol, quantity, stop_price, position_id)
        tp = TakeProfitOrder(f"{order_id}_TP", symbol, quantity, target_price, position_id)
        
        oco = OCOOrder(order_id, sl, tp)
        if not hasattr(self, 'oco_orders'):
            self.oco_orders = []
        self.oco_orders.append(oco)
        self.save_to_file()
        return order_id


if __name__ == "__main__":
    # Test the order manager
    print("📋 Testing Order Manager...")
    
    manager = OrderManager()
    
    # Test stop-loss
    print("\n--- Test 1: Stop Loss ---")
    sl_id = manager.add_stop_loss('BTC/USDT', 0.01, 91675.0, 'pos_001')
    print(f"Created stop-loss: {sl_id} at $91,675")
    
    # Check without trigger
    triggered = manager.check_all_orders({'BTC/USDT': 96500.0})
    print(f"Price $96,500: Triggered = {len(triggered)}")
    
    # Check with trigger
    triggered = manager.check_all_orders({'BTC/USDT': 91000.0})
    print(f"Price $91,000: Triggered = {len(triggered)}")
    if triggered:
        print(f"  → {triggered[0]}")
    
    # Test take-profit
    print("\n--- Test 2: Take Profit ---")
    tp_id = manager.add_take_profit('ETH/USDT', 2.0, 3000.0)
    print(f"Created take-profit: {tp_id} at $3,000")
    
    triggered = manager.check_all_orders({'ETH/USDT': 3100.0})
    print(f"Price $3,100: Triggered = {len(triggered)}")
    
    # Test trailing stop
    print("\n--- Test 3: Trailing Stop ---")
    ts_id = manager.add_trailing_stop('BTC/USDT', 0.01, 96500.0, 0.03)
    print(f"Created trailing stop: {ts_id} at 3% trail")
    
    # Price goes up
    triggered = manager.check_all_orders({'BTC/USDT': 97000.0})
    print(f"Price $97,000: Stop moved to ${manager.orders[-1].current_stop:.2f}")
    
    # Price drops
    triggered = manager.check_all_orders({'BTC/USDT': 93800.0})
    print(f"Price $93,800: Triggered = {len(triggered)}")
    
    # Show active orders
    print("\n--- Active Orders ---")
    active = manager.get_active_orders()
    print(f"Total active: {len(active)}")
    for order in active:
        print(f"  • {order['order_id']} ({order['type']})")
    
    print("\n✅ Order Manager test complete!")
