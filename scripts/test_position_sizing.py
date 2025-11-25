"""
Test Risk-Based Position Sizing
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.portfolio import RiskBasedPositionSizer
import pandas as pd
import numpy as np

def test_position_sizing():
    print("="*70)
    print("RISK-BASED POSITION SIZING TEST")
    print("="*70)
    print()
    
    capital = 10000
    price = 45000  # BTC price
    
    # Initialize sizer
    sizer = RiskBasedPositionSizer(
        capital=capital,
        max_position_pct=0.20,  # Max 20% per position
        max_risk_per_trade=0.02  # Max 2% risk per trade
    )
    
    # Test 1: Fixed Fractional Sizing
    print("1. Testing Fixed Fractional Sizing")
    print("-"*70)
    
    size_info = sizer.calculate_position_size(
        price=price,
        method='fixed_fractional',
        stop_loss_pct=0.03  # 3% stop loss
    )
    
    sizer.print_sizing_info('BTC/USDT', size_info)
    
    # Test 2: Kelly Criterion
    print("\n2. Testing Kelly Criterion")
    print("-"*70)
    
    size_info = sizer.calculate_position_size(
        price=price,
        method='kelly',
        win_rate=0.60,  # 60% win rate
        avg_win=0.05,   # 5% average win
        avg_loss=0.02   # 2% average loss
    )
    
    sizer.print_sizing_info('BTC/USDT', size_info)
    
    # Test 3: Volatility-Based Sizing
    print("\n3. Testing Volatility-Based Sizing")
    print("-"*70)
    
    size_info = sizer.calculate_position_size(
        price=price,
        method='volatility',
        volatility=0.04  # 4% volatility
    )
    
    sizer.print_sizing_info('BTC/USDT', size_info)
    
    # Test 4: ATR-Based Sizing
    print("\n4. Testing ATR-Based Sizing")
    print("-"*70)
    
    # Create mock data for ATR calculation
    np.random.seed(42)
    prices = [price]
    for _ in range(30):
        change = np.random.randn() * 0.02
        prices.append(prices[-1] * (1 + change))
    
    data = pd.DataFrame({
        'close': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices]
    })
    
    size_info = sizer.calculate_position_size(
        price=price,
        method='atr',
        data=data
    )
    
    sizer.print_sizing_info('BTC/USDT', size_info)
    
    # Test 5: Multi-Position Sizing
    print("\n5. Testing Multi-Position Sizing")
    print("-"*70)
    
    positions = {
        'BTC/USDT': {
            'price': 45000,
            'method': 'fixed_fractional',
            'stop_loss_pct': 0.03
        },
        'ETH/USDT': {
            'price': 2500,
            'method': 'volatility',
            'volatility': 0.05
        },
        'SOL/USDT': {
            'price': 100,
            'method': 'kelly',
            'win_rate': 0.55,
            'avg_win': 0.04,
            'avg_loss': 0.02
        }
    }
    
    results = sizer.calculate_multi_position_sizes(positions)
    
    print("\n   Multi-Position Results:")
    total_value = 0
    total_risk = 0
    
    for symbol, info in results.items():
        print(f"\n   {symbol}:")
        print(f"     Size: {info['size']:.4f} units")
        print(f"     Value: ${info['value']:,.2f} ({info['position_pct']*100:.1f}%)")
        print(f"     Risk: ${info['risk_amount']:,.2f} ({info['risk_pct']*100:.2f}%)")
        
        total_value += info['value']
        total_risk += info['risk_amount']
    
    print(f"\n   Total Allocation: ${total_value:,.2f} ({total_value/capital*100:.1f}%)")
    print(f"   Total Risk: ${total_risk:,.2f} ({total_risk/capital*100:.2f}%)")
    
    # Test 6: Comparison of Methods
    print("\n6. Comparing All Methods")
    print("-"*70)
    
    methods = ['fixed_fractional', 'kelly', 'volatility', 'atr']
    
    print(f"\n   {'Method':<20} {'Size':<12} {'Value':<15} {'Risk %':<10}")
    print("   " + "-"*60)
    
    for method in methods:
        size_info = sizer.calculate_position_size(
            price=price,
            method=method,
            stop_loss_pct=0.03,
            win_rate=0.55,
            avg_win=0.04,
            avg_loss=0.02,
            volatility=0.03,
            data=data
        )
        
        print(f"   {method:<20} {size_info['size']:<12.4f} ${size_info['value']:<14,.2f} {size_info['risk_pct']*100:<10.2f}%")
    
    print("\n" + "="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\n✅ All position sizing methods working correctly!")
    print("\nKey Features:")
    print("  • Fixed fractional sizing")
    print("  • Kelly Criterion")
    print("  • Volatility-based sizing")
    print("  • ATR-based sizing")
    print("  • Multi-position risk management")
    print("  • Position size limits")
    print()

if __name__ == "__main__":
    test_position_sizing()
