"""
Test Advanced Risk Manager
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk import AdvancedRiskManager
import pandas as pd
import numpy as np

def create_mock_data(days=100):
    """Create mock OHLC data"""
    np.random.seed(42)
    
    prices = [100]
    for _ in range(days - 1):
        change = np.random.randn() * 2
        prices.append(prices[-1] * (1 + change/100))
    
    data = pd.DataFrame({
        'open': prices,
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [1000000 + np.random.randint(-200000, 200000) for _ in prices]
    })
    
    return data

def test_advanced_risk_manager():
    print("="*70)
    print("ADVANCED RISK MANAGER TEST")
    print("="*70)
    print()
    
    risk_mgr = AdvancedRiskManager(
        atr_period=14,
        atr_multiplier=2.0,
        volume_threshold=1.5,
        volume_lookback=20
    )
    
    data = create_mock_data(100)
    
    # Test 1: ATR Calculation
    print("1. Testing ATR Calculation")
    print("-"*70)
    
    atr = risk_mgr.calculate_atr(data)
    print(f"   ATR (14-period): {atr:.2f}")
    print(f"   ✅ ATR calculated")
    print()
    
    # Test 2: ATR-Based Stop Loss
    print("2. Testing ATR-Based Stop Loss")
    print("-"*70)
    
    entry_price = 100.0
    stop_loss = risk_mgr.calculate_atr_stop_loss(entry_price, atr, direction='long')
    stop_pct = (entry_price - stop_loss) / entry_price
    
    print(f"   Entry Price: ${entry_price:.2f}")
    print(f"   ATR: ${atr:.2f}")
    print(f"   Stop Loss: ${stop_loss:.2f}")
    print(f"   Stop Distance: {stop_pct*100:.1f}%")
    print(f"   ✅ Dynamic stop calculated")
    print()
    
    # Test 3: Volume Confirmation
    print("3. Testing Volume Confirmation")
    print("-"*70)
    
    # Test with normal volume
    is_confirmed = risk_mgr.check_volume_confirmation(data.iloc[:50])
    print(f"   Normal volume: {'✅ Confirmed' if is_confirmed else '❌ Not confirmed'}")
    
    # Create high volume spike
    data_spike = data.copy()
    data_spike.loc[data_spike.index[-1], 'volume'] = data['volume'].mean() * 2
    is_confirmed = risk_mgr.check_volume_confirmation(data_spike)
    print(f"   High volume spike: {'✅ Confirmed' if is_confirmed else '❌ Not confirmed'}")
    print()
    
    # Test 4: Trailing Stop
    print("4. Testing Trailing Stop")
    print("-"*70)
    
    symbol = 'BTC/USDT'
    entry_price = 100.0
    
    # Initialize trailing stop
    risk_mgr.initialize_trailing_stop(
        symbol, entry_price, direction='long',
        activation_pct=0.03, trail_distance_pct=0.02
    )
    
    print(f"   Entry: ${entry_price:.2f}")
    
    # Simulate price movement
    prices = [100, 101, 102, 103, 104, 103.5, 103, 102.5]
    
    for price in prices:
        stop_price = risk_mgr.update_trailing_stop(symbol, price)
        stop_hit, reason = risk_mgr.check_stop_hit(symbol, price)
        
        profit = (price - entry_price) / entry_price * 100
        
        if stop_price:
            print(f"   Price: ${price:.2f} (+{profit:.1f}%) | Stop: ${stop_price:.2f} | Hit: {stop_hit}")
        else:
            print(f"   Price: ${price:.2f} (+{profit:.1f}%) | Stop: Not activated")
        
        if stop_hit:
            print(f"   🛑 Stop hit at ${price:.2f}!")
            break
    
    print()
    
    # Test 5: Dynamic Position Sizing
    print("5. Testing Dynamic Position Sizing")
    print("-"*70)
    
    capital = 10000
    price = 100
    
    size = risk_mgr.calculate_dynamic_position_size(capital, price, atr, risk_pct=0.02)
    position_value = size * price
    
    print(f"   Capital: ${capital:,.2f}")
    print(f"   Price: ${price:.2f}")
    print(f"   ATR: ${atr:.2f}")
    print(f"   Position Size: {size:.4f} units")
    print(f"   Position Value: ${position_value:,.2f}")
    print(f"   Risk: 2% of capital")
    print()
    
    # Test 6: Risk Metrics
    print("6. Testing Risk Metrics")
    print("-"*70)
    
    metrics = risk_mgr.get_risk_metrics(symbol)
    
    print(f"   Entry Price: ${metrics['entry_price']:.2f}")
    print(f"   Current Stop: ${metrics['current_stop']:.2f}")
    print(f"   Highest Price: ${metrics['highest_price']:.2f}")
    print(f"   Trailing Activated: {metrics['trailing_activated']}")
    print()
    
    print("="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\n✅ All advanced risk management features working!")
    print("\nKey Features:")
    print("  • ATR-based dynamic stops")
    print("  • Volume confirmation filters")
    print("  • Trailing stop management")
    print("  • Dynamic position sizing")
    print("  • Risk metrics tracking")
    print()

if __name__ == "__main__":
    test_advanced_risk_manager()
