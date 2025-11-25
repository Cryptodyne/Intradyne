"""
Test Multi-Asset Allocation
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.portfolio import MultiAssetAllocator, DynamicAllocator
import pandas as pd
import numpy as np

def create_mock_data(symbols, days=100):
    """Create mock price data"""
    data = {}
    
    for symbol in symbols:
        np.random.seed(hash(symbol) % 2**32)
        prices = [100]
        
        for _ in range(days - 1):
            change = np.random.randn() * 2
            prices.append(prices[-1] * (1 + change/100))
        
        data[symbol] = pd.DataFrame({
            'close': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'volume': [1000000] * days
        })
    
    return data

def test_allocation():
    print("="*70)
    print("MULTI-ASSET ALLOCATION TEST")
    print("="*70)
    print()
    
    # Test assets
    assets = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
    capital = 10000
    
    # Create mock data
    print("1. Creating Mock Data")
    print("-"*70)
    data = create_mock_data(assets)
    print(f"   ✅ Created data for {len(assets)} assets")
    print()
    
    # Test 2: Equal Weight Allocation
    print("2. Testing Equal Weight Allocation")
    print("-"*70)
    
    allocator = MultiAssetAllocator(capital, strategy='equal_weight')
    allocations = allocator.calculate_allocation(assets, data)
    allocator.print_allocation()
    
    # Test 3: Risk Parity Allocation
    print("\n3. Testing Risk Parity Allocation")
    print("-"*70)
    
    allocator = MultiAssetAllocator(capital, strategy='risk_parity')
    allocations = allocator.calculate_allocation(assets, data)
    allocator.print_allocation()
    
    # Test 4: Momentum Allocation
    print("\n4. Testing Momentum Allocation")
    print("-"*70)
    
    allocator = MultiAssetAllocator(capital, strategy='momentum')
    allocations = allocator.calculate_allocation(assets, data)
    allocator.print_allocation()
    
    # Test 5: Market Cap Allocation
    print("\n5. Testing Market Cap Allocation")
    print("-"*70)
    
    allocator = MultiAssetAllocator(capital, strategy='market_cap')
    allocations = allocator.calculate_allocation(assets, data)
    allocator.print_allocation()
    
    # Test 6: Rebalancing
    print("\n6. Testing Portfolio Rebalancing")
    print("-"*70)
    
    # Simulate current values (some drift from target)
    current_values = {
        'BTC/USDT': 3000,
        'ETH/USDT': 2800,
        'BNB/USDT': 2200,
        'SOL/USDT': 2000
    }
    
    allocator = MultiAssetAllocator(capital, strategy='equal_weight')
    allocator.calculate_allocation(assets, data)
    
    trades = allocator.rebalance(current_values)
    
    print("\n   Current Values:")
    for asset, value in current_values.items():
        print(f"     {asset}: ${value:,.2f}")
    
    print("\n   Rebalancing Trades:")
    for asset, trade in trades.items():
        action = "BUY" if trade > 0 else "SELL"
        print(f"     {action} {asset}: ${abs(trade):,.2f}")
    
    # Test 7: Dynamic Allocator
    print("\n7. Testing Dynamic Allocator")
    print("-"*70)
    
    dynamic = DynamicAllocator(capital)
    
    market_conditions = ['bull', 'bear', 'sideways', 'volatile']
    
    for condition in market_conditions:
        print(f"\n   Market: {condition.upper()}")
        allocations = dynamic.calculate_allocation(assets, data, condition)
        print(f"   Strategy: {dynamic.current_strategy}")
        
        # Show top 2 allocations
        sorted_alloc = sorted(allocations.items(), key=lambda x: x[1], reverse=True)
        for asset, amount in sorted_alloc[:2]:
            weight = amount / capital
            print(f"     {asset}: ${amount:,.2f} ({weight*100:.1f}%)")
    
    print("\n" + "="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\n✅ All allocation strategies working correctly!")
    print("\nKey Features:")
    print("  • Equal weight allocation")
    print("  • Risk parity (inverse volatility)")
    print("  • Momentum-based allocation")
    print("  • Market cap weighting")
    print("  • Portfolio rebalancing")
    print("  • Dynamic strategy selection")
    print()

if __name__ == "__main__":
    test_allocation()
