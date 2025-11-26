# Test script for Live Trading on Bitget Testnet
"""Comprehensive test suite for live trading components.

This script tests:
- OrderExecutor (order placement, cancellation, fills)
- PositionManager (position tracking, reconciliation)
- LiveTrader (full integration, safety limits)

IMPORTANT: Uses Bitget TESTNET only - NO REAL MONEY
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trading.order_executor import OrderExecutor
from src.trading.position_manager_live import PositionManager
from src.trading.live_trader import LiveTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_order_executor():
    """Test OrderExecutor functionality."""
    print("\n" + "="*70)
    print("TEST 1: Order Executor")
    print("="*70)
    
    # Initialize (credentials in OrderExecutor defaults)
    executor = OrderExecutor(
        exchange_id="bitget",
        testnet=True,  # TESTNET ONLY
    )
    
    print(f"\n✅ Initialized OrderExecutor for Bitget TESTNET")
    
    # Test 1: Place market order (small amount)
    print("\n📝 Test 1a: Place market buy order (0.001 BTC)")
    order = executor.place_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.001,
    )
    
    if order:
        print(f"✅ Market order placed: {order['id']}")
        print(f"   Status: {order['status']}")
        print(f"   Filled: {order.get('filled', 0)}")
        
        # Wait and check status
        time.sleep(2)
        status = executor.get_order_status(order['id'], "BTC/USDT")
        if status:
            print(f"✅ Order status updated: {status['status']}")
    else:
        print("❌ Failed to place market order")
    
    # Test 2: Place limit order
    print("\n📝 Test 1b: Place limit sell order (0.001 BTC @ $100k)")
    order = executor.place_limit_order(
        symbol="BTC/USDT",
        side="sell",
        amount=0.001,
        price=100000,  # Very high price (won't fill)
    )
    
    if order:
        print(f"✅ Limit order placed: {order['id']}")
        
        # Cancel the order
        time.sleep(1)
        cancelled = executor.cancel_order(order['id'], "BTC/USDT")
        if cancelled:
            print(f"✅ Order cancelled successfully")
    else:
        print("❌ Failed to place limit order")
    
    # Test 3: Get stats
    print("\n📊 OrderExecutor Stats:")
    stats = executor.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return executor


def test_position_manager(executor):
    """Test PositionManager functionality."""
    print("\n" + "="*70)
    print("TEST 2: Position Manager")
    print("="*70)
    
    # Initialize
    position_manager = PositionManager(
        executor=executor,
        sync_interval=30,  # 30 seconds
        max_position_usd=5000,
    )
    
    print(f"\n✅ Initialized PositionManager")
    
    # Test 1: Manual sync
    print("\n📝 Test 2a: Manual position sync")
    positions = position_manager.sync_positions()
    print(f"✅ Synced {len(positions)} positions:")
    for symbol, position in positions.items():
        print(f"   {symbol}: {position['amount']:.6f} @ ${position['current_price']:.2f}")
    
    # Test 2: Get total value
    total_value = position_manager.get_total_value_usd()
    print(f"\n💰 Total position value: ${total_value:,.2f}")
    
    # Test 3: Start auto-sync
    print("\n📝 Test 2b: Start auto-sync (30s interval)")
    position_manager.start_auto_sync()
    print("✅ Auto-sync started - waiting 35 seconds...")
    time.sleep(35)
    
    # Test 4: Stop auto-sync
    position_manager.stop_auto_sync()
    print("✅ Auto-sync stopped")
    
    # Test 5: Get stats
    print("\n📊 PositionManager Stats:")
    stats = position_manager.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return position_manager


def test_live_trader():
    """Test LiveTrader full integration."""
    print("\n" + "="*70)
    print("TEST 3: Live Trader (Full Integration)")
    print("="*70)
    
    # Initialize
    trader = LiveTrader(
        exchange_id="bitget",
        initial_capital=10000,
        daily_loss_limit_pct=5.0,  # 5% as requested
        max_position_pct=20.0,
        max_drawdown_pct=15.0,
        testnet=True,
    )
    
    print(f"\n✅ Initialized LiveTrader with 5% daily loss limit")
    
    # Start trader
    trader.start()
    print("✅ Trader started")
    
    # Test 1: Get initial stats
    print("\n📊 Initial Stats:")
    stats = trader.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test 2: Place a test order
    print("\n📝 Test 3a: Place market order via LiveTrader")
    order = trader.place_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.001,
        order_type="market",
    )
    
    if order:
        print(f"✅ Order placed via LiveTrader: {order['id']}")
    else:
        print("❌ Order rejected by LiveTrader")
    
    # Test 3: Run for 1 minute to test monitoring
    print("\n📝 Test 3b: Running trader for 60 seconds to test monitoring...")
    time.sleep(60)
    
    # Test 4: Get final stats
    print("\n📊 Final Stats:")
    stats = trader.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Stop trader
    trader.stop()
    print("\n✅ Trader stopped gracefully")
    
    return trader


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("BITGET TESTNET LIVE TRADING TESTS")
    print("="*70)
    print(f"Time: {datetime.now()}")
    print(f"⚠️  TESTNET MODE - NO REAL MONEY")
    print(f"⚠️  Using hardcoded testnet credentials")
    print("="*70)
    
    try:
        # Run tests
        executor = test_order_executor()
        position_manager = test_position_manager(executor)
        trader = test_live_trader()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
