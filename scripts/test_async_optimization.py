import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.optimization.async_optimizer import AsyncOptimizer, PerformanceComparison

async def test_async_optimizer():
    print("="*60)
    print("Testing Async Performance Optimizations")
    print("="*60)
    
    # Initialize optimizer
    print("\n1. Initializing AsyncOptimizer...")
    optimizer = AsyncOptimizer(max_concurrent=10)
    print("   ✓ Optimizer initialized")
    
    # Test 1: Multiple symbols from one exchange
    print("\n2. Testing parallel symbol fetching...")
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    try:
        results = await optimizer.fetch_multiple_symbols('bitget', symbols, '5m', 10)
        
        successful = sum(1 for r in results.values() if r['success'])
        print(f"   ✓ Fetched {successful}/{len(symbols)} symbols")
        
        for symbol, data in results.items():
            if data['success']:
                print(f"     {symbol}: {len(data['data'])} candles ({data['latency']*1000:.0f}ms)")
            else:
                print(f"     {symbol}: Failed - {data['error']}")
    
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test 2: One symbol from multiple exchanges
    print("\n3. Testing multi-exchange fetching...")
    exchanges = ['bitget', 'binance']
    
    try:
        results = await optimizer.fetch_from_multiple_exchanges(
            exchanges, 'BTC/USDT', '5m', 10
        )
        
        successful = sum(1 for r in results.values() if r['success'])
        print(f"   ✓ Fetched from {successful}/{len(exchanges)} exchanges")
        
        for exchange, data in results.items():
            if data['success']:
                last_close = data['data'][-1][4] if data['data'] else 0
                print(f"     {exchange}: ${last_close:,.2f} ({data['latency']*1000:.0f}ms)")
            else:
                print(f"     {exchange}: Failed - {data['error']}")
    
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test 3: Batch ticker fetching
    print("\n4. Testing batch ticker fetching...")
    
    try:
        tickers = await optimizer.batch_fetch_tickers('bitget', symbols)
        
        successful = sum(1 for t in tickers.values() if t['success'])
        print(f"   ✓ Fetched {successful}/{len(symbols)} tickers")
        
        for symbol, data in tickers.items():
            if data['success']:
                ticker = data['data']
                print(f"     {symbol}: ${ticker['last']:,.2f} | Vol: ${ticker['quoteVolume']:,.0f}")
    
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test 4: Fully parallel multi-exchange multi-symbol
    print("\n5. Testing fully parallel fetch (2 exchanges × 3 symbols)...")
    
    try:
        results = await optimizer.optimized_multi_exchange_fetch(
            exchanges, symbols, '5m', 10
        )
        
        total = 0
        successful = 0
        
        for exchange, symbol_data in results.items():
            for symbol, data in symbol_data.items():
                total += 1
                if data['success']:
                    successful += 1
        
        print(f"   ✓ Fetched {successful}/{total} combinations")
        
        for exchange, symbol_data in results.items():
            print(f"   {exchange}:")
            for symbol, data in symbol_data.items():
                if data['success']:
                    print(f"     {symbol}: {len(data['data'])} candles")
                else:
                    print(f"     {symbol}: Failed")
    
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Get stats
    print("\n6. Performance statistics:")
    stats = optimizer.get_performance_stats()
    print(f"   Max concurrent: {stats['max_concurrent']}")
    print(f"   Active exchanges: {stats['active_exchanges']}")
    print(f"   Exchanges: {', '.join(stats['exchanges'])}")
    
    # Cleanup
    print("\n7. Closing connections...")
    await optimizer.close()
    print("   ✓ All connections closed")
    
    print("\n" + "="*60)
    print("Async Optimizer Tests Complete!")
    print("="*60)

def test_performance_comparison():
    print("\n" + "="*60)
    print("Performance Comparison: Sync vs Async")
    print("="*60)
    
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT']
    
    print(f"\nTesting with {len(symbols)} symbols...")
    
    try:
        comparison = PerformanceComparison.compare('bitget', symbols)
        
        print(f"\n📊 Results:")
        print(f"   Sync duration: {comparison['sync']['duration']:.2f}s")
        print(f"   Async duration: {comparison['async']['duration']:.2f}s")
        print(f"   Speedup: {comparison['speedup']:.2f}x")
        print(f"   Improvement: {comparison['improvement_pct']:.1f}%")
        
        print(f"\n   Sync avg per symbol: {comparison['sync']['avg_per_symbol']*1000:.0f}ms")
        print(f"   Async avg per symbol: {comparison['async']['avg_per_symbol']*1000:.0f}ms")
    
    except Exception as e:
        print(f"   ✗ Comparison failed: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    print("Running async optimizer tests...\n")
    asyncio.run(test_async_optimizer())
    
    print("\n\nRunning performance comparison...")
    test_performance_comparison()
