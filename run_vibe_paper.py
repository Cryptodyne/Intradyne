import sys
import os
import time
import logging
import pandas as pd

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

        # Sort candidates by quote volume first (Stage 0: Liquidity Filter)
        candidates.sort(key=lambda x: x['volume'], reverse=True)
        top_50_candidates = candidates[:50]

        # Stage 1: 4H Macro Bias Filter (Top 50 -> Top 25)
        logger.info(f"🏆 Stage 1: Evaluating 4H Macro Bias across Top {len(top_50_candidates)} Halal candidates...")
        stage1_passed = []
        for c in top_50_candidates:
            symbol = c['symbol']
            try:
                ohlcv_4h = trader.market_data_fetcher.fetch_ohlcv(symbol, timeframe='4h', limit=30)
                if ohlcv_4h and len(ohlcv_4h) >= 20:
                    df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    is_bullish, score = strategy.evaluate_4h_bias(df_4h)
                    if is_bullish:
                        stage1_passed.append({'symbol': symbol, 'score_4h': score, 'volume': c['volume']})
            except Exception:
                pass

        # Fallback if less than 10 pass Stage 1
        if len(stage1_passed) < 10:
            for c in top_50_candidates[:25]:
                if not any(x['symbol'] == c['symbol'] for x in stage1_passed):
                    stage1_passed.append({'symbol': c['symbol'], 'score_4h': c['perc_24h'], 'volume': c['volume']})

        stage1_passed.sort(key=lambda x: x['score_4h'], reverse=True)
        top_25 = stage1_passed[:25]
        logger.info(f"✅ Stage 1 Complete: Filtered to Top {len(top_25)} 4H Bullish Bias coins.")

        # Stage 2: 1H Trend Structure Filter (Top 25 -> Top 10)
        logger.info(f"🏆 Stage 2: Confirming 1H Trend Structure across Top {len(top_25)} candidates...")
        stage2_passed = []
        for c in top_25:
            symbol = c['symbol']
            try:
                ohlcv_1h = trader.market_data_fetcher.fetch_ohlcv(symbol, timeframe='1h', limit=30)
                if ohlcv_1h and len(ohlcv_1h) >= 20:
                    df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    is_valid, score = strategy.evaluate_1h_structure(df_1h)
                    if is_valid:
                        stage2_passed.append({'symbol': symbol, 'score_1h': score + c['score_4h']})
            except Exception:
                pass

        # Fallback if less than 5 pass Stage 2
        if len(stage2_passed) < 5:
            for c in top_25[:10]:
                if not any(x['symbol'] == c['symbol'] for x in stage2_passed):
                    stage2_passed.append({'symbol': c['symbol'], 'score_1h': c['score_4h']})

        stage2_passed.sort(key=lambda x: x['score_1h'], reverse=True)
        symbols_to_trade = [p['symbol'] for p in stage2_passed[:10]]
        
        logger.info(f"🎯 Stage 3 & 4 Active! Top 10 MTF Funnel Setups selected for 15m/5m execution: {symbols_to_trade}")
        
    except Exception as e:
        logger.error(f"Error during market scan: {e}. Falling back to default symbols.")
        symbols_to_trade = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'ADA/USD']

    logger.info("Starting Live 4-Stage MTF Funnel Paper Trading (15m/5m Execution)...")
    trader.run_trading_loop(symbols_to_trade, 30)

if __name__ == "__main__":
    run_paper_trading()
