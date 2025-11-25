import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.exchange_aggregator import ExchangeAggregator

def test_aggregator():
    print("="*60)
    print("Testing Exchange Aggregator")
    print("="*60)
    
    # Initialize
    print("\n1. Initializing aggregator (Binance + Bybit)...")
    try:
        aggregator = ExchangeAggregator(['binance', 'bybit'])
        print(f"   ✓ Connected to {len(aggregator.exchanges)} exchanges")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    # Get exchange status
    print("\n2. Checking exchange status...")
    statuses = aggregator.get_exchange_status()
    for exchange_id, status in statuses.items():
        if status['connected']:
            print(f"   ✓ {exchange_id}: {status['markets']} markets")
        else:
            print(f"   ✗ {exchange_id}: {status.get('error', 'Unknown error')}")
    
    # Fetch from all exchanges
    print("\n3. Fetching BTC/USDT from all exchanges...")
    try:
        results = aggregator.fetch_from_all_exchanges('BTC/USDT', '5m', 10)
        for exchange_id, result in results.items():
            if result['success']:
                candles = result['data']
                last_close = candles[-1][4] if candles else 0
                print(f"   ✓ {exchange_id}: ${last_close:,.2f} ({len(candles)} candles)")
            else:
                print(f"   ✗ {exchange_id}: {result['error']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Get best prices
    print("\n4. Finding best prices...")
    try:
        best = aggregator.get_best_price('BTC/USDT')
        if 'error' not in best:
            print(f"   Best Bid: ${best['best_bid']['price']:,.2f} on {best['best_bid']['exchange']}")
            print(f"   Best Ask: ${best['best_ask']['price']:,.2f} on {best['best_ask']['exchange']}")
        else:
            print(f"   ✗ {best['error']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Detect arbitrage
    print("\n5. Detecting arbitrage opportunities...")
    try:
        arb = aggregator.detect_arbitrage('BTC/USDT', threshold=0.1)
        if arb['opportunity']:
            print(f"   🎯 ARBITRAGE FOUND!")
            print(f"      Buy from: {arb['buy_from']} @ ${arb['buy_price']:,.2f}")
            print(f"      Sell to: {arb['sell_to']} @ ${arb['sell_price']:,.2f}")
            print(f"      Spread: {arb['spread']}%")
            print(f"      Profit: ${arb['profit_per_unit']:,.2f} per unit")
        else:
            print(f"   No arbitrage opportunity (spread: {arb.get('spread', 0)}%)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Find most liquid exchange
    print("\n6. Finding most liquid exchange...")
    try:
        liquid = aggregator.get_most_liquid_exchange('BTC/USDT')
        if 'error' not in liquid:
            print(f"   Most liquid: {liquid['exchange']}")
            print(f"   Volume: ${liquid['volume']:,.0f}")
        else:
            print(f"   ✗ {liquid['error']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test failover
    print("\n7. Testing failover mechanism...")
    try:
        result = aggregator.fetch_with_failover('BTC/USDT', '5m', 10)
        if result['success']:
            print(f"   ✓ Fetched from {result['exchange']}")
            print(f"   Data points: {len(result['data'])}")
        else:
            print(f"   ✗ All exchanges failed: {result['error']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    print("\n" + "="*60)
    print("Exchange Aggregator Tests Complete!")
    print("="*60)

if __name__ == "__main__":
    test_aggregator()
