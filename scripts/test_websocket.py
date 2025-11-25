import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.market_stream import MarketDataStream

async def ticker_callback(ticker):
    """Callback for ticker updates."""
    print(f"  📊 {ticker['symbol']}: ${ticker['last']:,.2f} | Vol: ${ticker['volume']:,.0f}")

async def trade_callback(trade):
    """Callback for trade updates."""
    side_emoji = "🟢" if trade['side'] == 'buy' else "🔴"
    print(f"  {side_emoji} Trade: {trade['amount']:.4f} @ ${trade['price']:,.2f}")

async def orderbook_callback(orderbook):
    """Callback for orderbook updates."""
    best_bid = orderbook['bids'][0][0] if orderbook['bids'] else 0
    best_ask = orderbook['asks'][0][0] if orderbook['asks'] else 0
    spread = best_ask - best_bid
    print(f"  📖 Orderbook: Bid ${best_bid:,.2f} | Ask ${best_ask:,.2f} | Spread ${spread:.2f}")

async def test_websocket():
    print("="*60)
    print("Testing WebSocket Market Data Stream")
    print("="*60)
    
    # Initialize stream
    print("\n1. Initializing WebSocket stream...")
    try:
        stream = MarketDataStream(exchange_id='binance', max_buffer_size=100)
        print("   ✓ Stream initialized")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    # Start stream
    print("\n2. Starting stream...")
    stream.start_stream()
    print("   ✓ Stream started")
    
    # Subscribe to ticker
    print("\n3. Subscribing to BTC/USDT ticker...")
    await stream.subscribe_ticker('BTC/USDT', callback=ticker_callback)
    print("   ✓ Subscribed to ticker")
    
    # Subscribe to trades
    print("\n4. Subscribing to BTC/USDT trades...")
    await stream.subscribe_trades('BTC/USDT', callback=trade_callback)
    print("   ✓ Subscribed to trades")
    
    # Subscribe to orderbook
    print("\n5. Subscribing to BTC/USDT orderbook...")
    await stream.subscribe_orderbook('BTC/USDT', callback=orderbook_callback, limit=5)
    print("   ✓ Subscribed to orderbook")
    
    # Run for 30 seconds
    print("\n6. Streaming data for 30 seconds...")
    print("   (Press Ctrl+C to stop early)\n")
    
    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\n   Interrupted by user")
    
    # Get buffer stats
    print("\n7. Getting buffer statistics...")
    stats = stream.get_buffer_stats()
    print(f"   Ticker updates: {stats['tickers']}")
    print(f"   Trade updates: {stats['trades']}")
    print(f"   Orderbook updates: {stats['orderbooks']}")
    print(f"   Total subscriptions: {stats['total_subscriptions']}")
    
    # Get latest data
    print("\n8. Getting latest data...")
    latest_ticker = stream.get_latest_ticker('BTC/USDT')
    if latest_ticker:
        print(f"   Latest price: ${latest_ticker['last']:,.2f}")
    
    latest_trades = stream.get_latest_trades('BTC/USDT', count=5)
    print(f"   Latest trades: {len(latest_trades)} trades")
    
    latest_orderbook = stream.get_latest_orderbook('BTC/USDT')
    if latest_orderbook:
        print(f"   Orderbook depth: {len(latest_orderbook['bids'])} bids, {len(latest_orderbook['asks'])} asks")
    
    # Stop stream
    print("\n9. Stopping stream...")
    await stream.stop_stream()
    print("   ✓ Stream stopped")
    
    print("\n" + "="*60)
    print("WebSocket Stream Tests Complete!")
    print("="*60)

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
