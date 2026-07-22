import sys
import os
import time
import logging

# Ensure root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.trading.paper_trader import PaperTrader
from src.strategy.vibe_alpha import VibeAlphaStrategy

# Setup Async / Machine readable logging (Protocol 20)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RunVibePaper")

def enforce_single_instance(port: int = 49998):
    """Ensure only one instance of the Paper Trader runs at any time by binding a local socket lock."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
    except socket.error:
        logger.warning(f"⚠️ Paper Trader engine is already running (Port {port} locked). Exiting duplicate instance.")
        sys.exit(0)
    return s

def run_paper_trading():
    _instance_lock = enforce_single_instance(49998)
    # Surface Pro Defense: Process Isolation & Affinity (Protocol 2)
    try:
        import psutil
        p = psutil.Process()
        if hasattr(p, 'cpu_affinity'):
            p.cpu_affinity([0, 1]) # Pin scanner & feed to Cores 0 & 1
            logger.info("Surface Pro Defense: Intraday Engine pinned to CPU Cores [0, 1]")
    except Exception as e:
        logger.warning(f"Could not set CPU affinity: {e}")

    logger.info("Initializing Intraday VibeAlphaStrategy (15m Primary Timeframe)...")
    strategy = VibeAlphaStrategy({
        "lookback": 20,
        "adx_period": 14,
        "atr_period": 14,
        "rsi_period": 14,
        "adx_threshold": 18,
        "volume_factor": 1.2
    })

    def paper_adapter_func(df, idx):
        res = strategy.analyze("PAPER_SYMBOL", df)
        if res and 'action' in res:
            return res['action']
        return 'HOLD'

    logger.info("Initializing PaperTrader Engine...")
    trader = PaperTrader(initial_capital=10000, strategy_func=paper_adapter_func)
    
    connected = trader.connect_exchange('kraken')
    if not connected:
        logger.error("Failed to connect to Kraken. Exiting.")
        return

    top_n = int(os.environ.get("SCAN_UNIVERSE_LIMIT", "50"))
    logger.info(f"Performing Intraday Market Scan to find top {top_n} Halal momentum pairs...")
    try:
        exchange = trader.market_data_fetcher.exchange
        tickers = exchange.fetch_tickers()
        
        # Load Halal Whitelist for compliance filtering (Rule 7)
        import yaml
        allowed_base_assets = set()
        meme_blacklist = {'DOGE', 'SHIB', 'PEPE', 'WIF', 'BONK', 'POPCAT', 'PUMP', 'SPX', 'FLOKI', 'MEME', 'MOG'}
        if os.path.exists("config/halal_whitelist.yaml"):
            with open("config/halal_whitelist.yaml", "r", encoding="utf-8") as f:
                hw = yaml.safe_load(f) or {}
                for category, syms in hw.items():
                    if isinstance(syms, list):
                        for s in syms:
                            if not isinstance(s, str) or s.strip().startswith('#'):
                                continue
                            raw_pair = s.split('#')[0].strip()
                            if '/' in raw_pair:
                                base = raw_pair.split('/')[0].upper()
                                if base not in meme_blacklist:
                                    allowed_base_assets.add(base)

        valid_pairs = []
        excluded = ['USDC/USDT', 'DAI/USDT', 'WBTC/USDT', 'USDT/USD', 'USDC/USD', 'USDC/EUR', 'USDT/EUR']
        candidates = []
        for symbol, ticker in tickers.items():
            if (symbol.endswith('/USDT') or symbol.endswith('/USD')) and symbol not in excluded and ':' not in symbol:
                base_coin = symbol.split('/')[0].upper()
                if base_coin in meme_blacklist:
                    continue # Rule 7: Hard block Meme coins
                if allowed_base_assets and base_coin not in allowed_base_assets:
                    continue # Enforce Halal whitelist

                vol = ticker.get('quoteVolume', 0) or 0
                perc_24h = ticker.get('percentage', 0) or 0
                if vol > 50000: # Liquidity filter
                    candidates.append({
                        'symbol': symbol,
                        'perc_24h': perc_24h,
                        'volume': vol
                    })

        # Pre-filter top 70 by liquidity/24h volume for fast 4h momentum calculation
        candidates.sort(key=lambda x: x['volume'], reverse=True)
        top_candidates = candidates[:70]

        valid_pairs = []
        logger.info(f"Computing 4h Session Momentum across top {len(top_candidates)} liquidity candidates...")
        for c in top_candidates:
            symbol = c['symbol']
            try:
                ohlcv = trader.market_data_fetcher.fetch_ohlcv(symbol, timeframe='15m', limit=17)
                if ohlcv and len(ohlcv) >= 16:
                    open_4h = ohlcv[-16][1] # Open price 16 candles ago (4 hours)
                    close_now = ohlcv[-1][4]
                    if open_4h > 0:
                        perc_4h = ((close_now - open_4h) / open_4h) * 100
                        valid_pairs.append({
                            'symbol': symbol,
                            'momentum_4h': perc_4h,
                            'volume': c['volume']
                        })
                        continue
            except Exception:
                pass
            # Fallback to 24h momentum if 4h candles unavailable
            valid_pairs.append({
                'symbol': symbol,
                'momentum_4h': c['perc_24h'],
                'volume': c['volume']
            })

        valid_pairs.sort(key=lambda x: x['momentum_4h'], reverse=True)
        selected = valid_pairs[:top_n]
        symbols_to_trade = [p['symbol'] for p in selected]
        
        logger.info(f"Intraday 4h Momentum Scan complete! Selected {len(symbols_to_trade)} Halal pairs for 15m trading: {symbols_to_trade[:10]}...")
        
    except Exception as e:
        logger.error(f"Error during market scan: {e}. Falling back to default symbols.")
        symbols_to_trade = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'ADA/USD']

    logger.info("Starting Live Intraday Paper Trading (15m Candle Closes)...")
    # Rule 10: 15m candle closes with 30s update poll interval
    trader.run_trading_loop(symbols_to_trade, 30)

if __name__ == "__main__":
    run_paper_trading()
