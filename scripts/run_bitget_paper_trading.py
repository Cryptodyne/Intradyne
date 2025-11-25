"""
Bitget Paper Trading - Quick Start
Connects to Bitget exchange for live paper trading
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trading.paper_trader import PaperTrader
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def simple_sma_strategy(data, index, fast=9, slow=20):
    """Simple SMA crossover strategy"""
    if index < slow:
        return 'HOLD'
    
    closes = data['close'].values[:index+1]
    
    sma_fast = sum(closes[-fast:]) / fast
    sma_slow = sum(closes[-slow:]) / slow
    
    # Previous SMAs
    if index > 0:
        prev_closes = data['close'].values[:index]
        prev_sma_fast = sum(prev_closes[-fast:]) / fast
        prev_sma_slow = sum(prev_closes[-slow:]) / slow
        
        # Crossover
        if sma_fast > sma_slow and prev_sma_fast <= prev_sma_slow:
            return 'BUY'
        elif sma_fast < sma_slow and prev_sma_fast >= prev_sma_slow:
            return 'SELL'
    
    return 'HOLD'

def main():
    print("="*70)
    print("🚀 BITGET PAPER TRADING")
    print("="*70)
    print()
    
    # Initialize
    print("📊 Initializing paper trader...")
    print("   Initial Capital: $10,000")
    print("   Strategy: SMA Crossover (9/20)")
    print()
    
    trader = PaperTrader(
        initial_capital=10000,
        strategy_func=simple_sma_strategy
    )
    
    # Connect to Bitget
    print("🔌 Connecting to Bitget exchange...")
    connected = trader.connect_exchange('bitget')
    
    if not connected:
        print("❌ Failed to connect to Bitget")
        print("\n💡 Troubleshooting:")
        print("   1. Check internet connection")
        print("   2. Install CCXT: pip install ccxt")
        print("   3. Bitget may require API keys for some features")
        print("\n🔄 Trying Binance as fallback...")
        
        connected = trader.connect_exchange('binance')
        if not connected:
            print("❌ Failed to connect to any exchange")
            return
        else:
            print("✅ Connected to Binance (fallback)")
    else:
        print("✅ Connected to Bitget successfully!")
    
    print()
    
    # Trading configuration
    symbols = ['BTC/USDT', 'ETH/USDT']
    update_interval = 60  # seconds
    
    print("⚙️  Trading Configuration:")
    print(f"   Symbols: {', '.join(symbols)}")
    print(f"   Update Interval: {update_interval}s")
    print(f"   Position Size: 10% of capital")
    print()
    
    print("🛡️  Risk Management:")
    print("   Max Positions: 5")
    print("   Stop-Loss: 3%")
    print("   Take-Profit: 10%")
    print("   Daily Loss Limit: 5%")
    print()
    
    print("🎯 Starting live paper trading...")
    print("   Press Ctrl+C to stop")
    print()
    print("-"*70)
    
    # Start trading
    try:
        trader.run_trading_loop(symbols, interval=update_interval)
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("Trading stopped by user")
        print("="*70)

if __name__ == "__main__":
    main()
