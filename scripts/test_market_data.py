import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.market_data import MarketDataFetcher

def test_market_data():
    print("="*60)
    print("Testing Market Data Fetcher")
    print("="*60)
    
    # Initialize
    print("\n1. Initializing Binance connection...")
    try:
        fetcher = MarketDataFetcher(exchange_id='binance')
        print("   ✓ Connected successfully")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return
    
    # Get exchange status
    print("\n2. Getting exchange status...")
    status = fetcher.get_exchange_status()
    print(f"   Exchange: {status['name']}")
    print(f"   Markets: {status['markets_count']}")
    print(f"   Timeframes: {', '.join(status['timeframes'][:5])}...")
    
    # Fetch OHLCV
    print("\n3. Fetching OHLCV for BTC/USDT (5m, 50 candles)...")
    try:
        ohlcv = fetcher.fetch_ohlcv('BTC/USDT', '5m', 50)
        print(f"   ✓ Fetched {len(ohlcv)} candles")
        print(f"   Latest candle: {ohlcv[-1]}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    # Get closes
    print("\n4. Getting closing prices...")
    closes = fetcher.get_latest_closes('BTC/USDT', '5m', 50)
    print(f"   ✓ Got {len(closes)} closing prices")
    print(f"   Latest close: ${closes[-1]:,.2f}")
    print(f"   Price range: ${min(closes):,.2f} - ${max(closes):,.2f}")
    
    # Get ticker
    print("\n5. Getting ticker data...")
    ticker = fetcher.get_ticker('BTC/USDT')
    print(f"   Last: ${ticker['last']:,.2f}")
    print(f"   Bid: ${ticker['bid']:,.2f}")
    print(f"   Ask: ${ticker['ask']:,.2f}")
    print(f"   Volume: ${ticker['quoteVolume']:,.0f}")
    
    # Validate data quality
    print("\n6. Validating data quality...")
    is_valid, checks = fetcher.validate_data_quality(ohlcv)
    print(f"   Overall: {'✓ VALID' if is_valid else '✗ INVALID'}")
    for check, result in checks.items():
        status = '✓' if result else '✗'
        print(f"   {status} {check}: {result}")
    
    # Format for engines
    print("\n7. Formatting data for engines...")
    engine_data = fetcher.format_for_engines('BTC/USDT', '5m', 50)
    print(f"   Symbol: {engine_data['symbol']}")
    print(f"   Closes: {len(engine_data['closes'])} values")
    print(f"   Volume: ${engine_data['volume']:,.0f}")
    print(f"   Last Price: ${engine_data['last_price']:,.2f}")
    print(f"   Timestamp: {engine_data['timestamp']}")
    
    print("\n" + "="*60)
    print("Market Data Fetcher Tests Complete!")
    print("="*60)

if __name__ == "__main__":
    test_market_data()
