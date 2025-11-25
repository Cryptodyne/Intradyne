"""
Run live paper trading with real market data
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

def run_paper_trading():
    print("="*70)
    print("LIVE PAPER TRADING - BITGET")
    print("="*70)
    print()
    
    # Initialize paper trader
    print("Initializing paper trader...")
    trader = PaperTrader(
        initial_capital=10000,
        strategy_func=simple_sma_strategy
    )
    
    # Connect to Bitget exchange
    print("Connecting to Bitget...")
    connected = trader.connect_exchange('bitget')
    
    if not connected:
        print("❌ Failed to connect to Bitget")
        print("\nNote: This requires internet connection and CCXT library")
        print("Install with: pip install ccxt")
        print("\nTrying Binance as fallback...")
        connected = trader.connect_exchange('binance')
        if not connected:
            print("❌ Failed to connect to any exchange")
            return
    
    print("✅ Connected to exchange")
    print()
    
    # Configure trading
    symbols = ['BTC/USDT', 'ETH/USDT']
    update_interval = 60  # 60 seconds
    
    print(f"Trading symbols: {', '.join(symbols)}")
    print(f"Update interval: {update_interval} seconds")
    print(f"Strategy: SMA Crossover (9/20)")
    print()
    print("Press Ctrl+C to stop trading")
    print()
    
    # Start trading
    trader.run_trading_loop(symbols, interval=update_interval)

if __name__ == "__main__":
    run_paper_trading()
