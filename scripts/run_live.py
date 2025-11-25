import sys
import os
import time
import argparse
import yaml
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.market_data import MarketDataFetcher
from src.core.coordinator import Coordinator

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data/logs/live_trading.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('LiveTrading')

def load_config():
    """Load exchange configuration."""
    config_path = 'config/exchanges.yaml'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return None

def main():
    parser = argparse.ArgumentParser(description='Intradyne Live Trading System')
    parser.add_argument('--symbols', type=str, default='BTC/USDT',
                       help='Comma-separated list of symbols (e.g., BTC/USDT,ETH/USDT)')
    parser.add_argument('--exchange', type=str, default='binance',
                       help='Exchange to use (binance, bybit, okx)')
    parser.add_argument('--timeframe', type=str, default='5m',
                       help='Timeframe for candles (1m, 5m, 15m, 1h, 4h)')
    parser.add_argument('--interval', type=int, default=300,
                       help='Update interval in seconds (default: 300 = 5 minutes)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (no actual trades)')
    
    args = parser.parse_args()
    
    # Setup
    logger = setup_logging()
    config = load_config()
    
    logger.info("="*60)
    logger.info("INTRADYNE LIVE TRADING SYSTEM")
    logger.info("="*60)
    logger.info(f"Exchange: {args.exchange}")
    logger.info(f"Symbols: {args.symbols}")
    logger.info(f"Timeframe: {args.timeframe}")
    logger.info(f"Update Interval: {args.interval}s")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info("="*60)
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    # Initialize components
    try:
        logger.info("Initializing Market Data Fetcher...")
        fetcher = MarketDataFetcher(exchange_id=args.exchange)
        
        logger.info("Initializing Coordinator...")
        coordinator = Coordinator()
        
        # Get exchange status
        status = fetcher.get_exchange_status()
        logger.info(f"Connected to {status['name']} ({status['markets_count']} markets)")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return
    
    # Main loop
    logger.info("\nStarting live monitoring...")
    logger.info("Press Ctrl+C to stop\n")
    
    iteration = 0
    try:
        while True:
            iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*60}")
            
            for symbol in symbols:
                try:
                    # Fetch market data
                    logger.info(f"\nFetching data for {symbol}...")
                    market_data = fetcher.format_for_engines(symbol, args.timeframe)
                    
                    # Validate data quality
                    ohlcv = fetcher.fetch_ohlcv(symbol, args.timeframe, 50)
                    is_valid, checks = fetcher.validate_data_quality(ohlcv)
                    
                    if not is_valid:
                        logger.warning(f"Data quality issues for {symbol}: {checks}")
                        continue
                    
                    logger.info(f"  Last Price: ${market_data['last_price']:.2f}")
                    logger.info(f"  Volume: ${market_data['volume']:,.0f}")
                    logger.info(f"  Data Quality: {'✓ PASS' if is_valid else '✗ FAIL'}")
                    
                    # Run pipeline
                    logger.info(f"  Running analysis pipeline...")
                    result = coordinator.run_pipeline(market_data)
                    
                    logger.info(f"  Decision: {result['decision']}")
                    logger.info(f"  Score: {result['ensemble']['score']}")
                    logger.info(f"  Compliance: {result['ensemble']['compliance']}")
                    
                    if args.dry_run:
                        logger.info(f"  [DRY RUN] No actual trade executed")
                    
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    continue
            
            # Wait for next iteration
            logger.info(f"\nWaiting {args.interval}s until next update...")
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("\n\nShutdown requested by user")
        logger.info("Stopping live trading system...")
        logger.info("Goodbye!")

if __name__ == "__main__":
    main()
