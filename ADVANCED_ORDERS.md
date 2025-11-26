# Advanced Order Types - Quick Reference

## ✅ What's Implemented

### Order Types Available:
1. **Stop-Loss** - Auto-sell when price drops
2. **Take-Profit** - Auto-sell at profit target
3. **Trailing Stop** - Dynamic stop that follows price upward
4. **Conditional** - Execute based on sentiment/price conditions
5. **Limit** - Buy/sell at specific price (NEW)
6. **OCO** - One-Cancels-Other linked orders (NEW)

---

## 🚀 Quick Start

###Using Order Manager:

```python
from src.trading.order_manager import OrderManager

manager = OrderManager()

# Stop-Loss
manager.add_stop_loss('BTC/USDT', 0.01, 91675.0)

# Take-Profit
manager.add_take_profit('ETH/USDT', 2.0, 3000.0)

# Trailing Stop (3%)
manager.add_trailing_stop('BTC/USDT', 0.01, 96500.0, 0.03)

# Limit Order
from src.trading.order_integration import add_limit_order
add_limit_order(manager, 'BTC/USDT', 0.01, 95000.0, 'BUY')

# OCO Order
from src.trading.order_integration import add_oco_order
add_oco_order(manager, 'BTC/USDT', 0.01, 91675.0, 100000.0)

# Check all orders
triggered = manager.check_all_orders({'BTC/USDT': 96000.0})
```

---

## 📁 Files Created

- `src/trading/order_classes.py` - LimitOrder and OCOOrder classes
- `src/trading/order_integration.py` - Integration helpers
- `ADVANCED_ORDERS.md` - This guide

---

## 🔧 Integration with Paper Trading

To use with your paper trading bot, edit `src/trading/paper_trader.py`:

```python
from src.trading.order_manager import OrderManager

class PaperTrader:
    def __init__(self):
        self.order_manager = OrderManager()
        self.order_manager.load_from_file()  # Load saved orders
    
    def run_trading_loop(self, symbols, interval=60):
        while self.is_running:
            # Update prices
            self.update_prices(symbols)
            
            # Check orders
            triggered = self.order_manager.check_all_orders(self.current_prices)
            
            # Execute triggered orders
            for order in triggered:
                if order['type'] == 'STOP_LOSS':
                    self.execute_signal(order['symbol'], 'SELL')
                elif order['type'] == 'TAKE_PROFIT':
                    self.execute_signal(order['symbol'], 'SELL')
                # etc...
```

---

## 🎯 Use Cases

### Risk Management:
```python
# Buy BTC and immediately set protective orders
manager.add_oco_order('BTC/USDT', 0.01, 
    stop_price=91675,      # -5% stop loss
    target_price=105000)   # +8% take profit
```

### Entry Orders:
```python
# Buy if price dips to $95k
manager.add_limit_order('BTC/USDT', 0.01, 95000.0, 'BUY')
```

### Trail Winners:
```python
# Let profits run with 3% trailing stop
manager.add_trailing_stop('BTC/USDT', 0.01, 96500.0, 0.03)
```

---

## 📊 Order Status

- **ACTIVE** - Monitoring price, waiting to trigger
- **TRIGGERED** - Executed
- **CANCELED** - Manually canceled or OCO partner triggered
- **EXPIRED** - Time constraint reached (DAY orders)

---

## ⚙️ Persistence

Orders are auto-saved to `orders/active_orders.json` on create/cancel.

**Manual save:**
```python
manager.save_to_file()
```

**Load on startup:**
```python
manager.load_from_file()
```

---

## 🔮 Next Steps (Future Enhancements)

- **Dashboard UI** - Streamlit page for order management
- **WebSocket Updates** - Real-time order status in dashboard
- **Order Notifications** - Email/SMS when orders trigger
- **Advanced Charts** - Visualize stop-loss/take-profit levels

---

**Status:** Core functionality ready  
**UI Integration:** Pending (can be done separately)  
**Paper Trading Integration:** Manual (follow integration guide above)
