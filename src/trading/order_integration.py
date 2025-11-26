"""
Advanced Orders Integration Module
Adds limit orders and OCO orders to the existing order manager.
Run this to add new methods to OrderManager.
"""

# Add these methods to OrderManager class in order_manager.py:

def add_limit_order(self, symbol: str, quantity: float, limit_price: float, side: str,
                   position_id: Optional[str] = None, time_constraint=None) -> str:
    """
    Add a limit order.
    
    Args:
        symbol: Trading pair
        quantity: Amount to trade
        limit_price: Price to execute at
        side: 'BUY' or 'SELL'
        time_constraint: TimeConstraint.GTC or TimeConstraint.DAY
    """
    from src.trading.order_classes import LimitOrder, TimeConstraint
    
    order_id = f"LMT_{self.order_counter:04d}"
    self.order_counter += 1
    
    tc = time_constraint or TimeConstraint.GTC
    order = LimitOrder(order_id, symbol, quantity, limit_price, side, position_id, tc)
    self.orders.append(order)
    self.save_to_file()  # Auto-save
    return order_id


def add_oco_order(self, symbol: str, quantity: float, stop_price: float, 
                 target_price: float, position_id: Optional[str] = None) -> str:
    """
    Add OCO (One-Cancels-Other) order - links stop-loss and take-profit.
    
    Args:
        symbol: Trading pair
        quantity: Amount to trade
        stop_price: Stop-loss price
        target_price: Take-profit price
    """
    from src.trading.order_classes import OCOOrder
    
    order_id = f"OCO_{self.order_counter:04d}"
    self.order_counter += 2  # Reserves IDs for both orders
    
    # Create both orders
    sl = StopLossOrder(f"{order_id}_SL", symbol, quantity, stop_price, position_id)
    tp = TakeProfitOrder(f"{order_id}_TP", symbol, quantity, target_price, position_id)
    
    # Link them
    oco = OCOOrder(order_id, sl, tp)
    self.oco_orders = getattr(self, 'oco_orders', [])
    self.oco_orders.append(oco)
    self.save_to_file()
    return order_id


def save_to_file(self, filepath: str = "orders/active_orders.json"):
    """Save active orders to JSON file."""
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
    if not os.path.exists(filepath):
        return
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    self.order_counter = data.get('counter', 0)
    # Note: Reconstruction from JSON would need order type detection
    # For now, orders are recreated fresh on each session
