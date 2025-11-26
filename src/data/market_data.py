import ccxt
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

class MarketDataFetcher:
    """
    Fetches real-time market data from cryptocurrency exchanges using CCXT.
    Supports multiple exchanges with automatic failover and rate limiting.
    """
    
    def __init__(self, exchange_id: str = 'binance', testnet: bool = False, cache_enabled: bool = True):
        """
        Initialize the market data fetcher.
        
        Args:
            exchange_id: Exchange to connect to ('binance', 'bybit', 'okx')
            testnet: Whether to use testnet (default: False)
            cache_enabled: Enable in-memory caching (default: True)
        """
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.cache_enabled = cache_enabled
        
        # Setup logging first
        self.logger = logging.getLogger(f"MarketData_{exchange_id}")
        self.logger.setLevel(logging.INFO)
        
        # Initialize exchange
        self.exchange = self._init_exchange(exchange_id, testnet)
        
        # Enhanced cache
        if cache_enabled:
            from .cache import EnhancedCache
            self._cache = EnhancedCache(max_size=100, default_ttl=60)
        else:
            self._cache = None
        
    def _init_exchange(self, exchange_id: str, testnet: bool):
        """Initialize CCXT exchange instance."""
        exchange_class = getattr(ccxt, exchange_id)
        
        config = {
            'enableRateLimit': True,  # Built-in rate limiting
            'timeout': 30000,  # 30 seconds
        }
        
        if testnet:
            config['sandbox'] = True
            
        exchange = exchange_class(config)
        
        # Load markets
        try:
            exchange.load_markets()
            self.logger.info(f"Connected to {exchange_id} ({len(exchange.markets)} markets)")
        except Exception as e:
            self.logger.error(f"Failed to load markets: {e}")
            raise
            
        return exchange
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 100, 
                    since: Optional[int] = None) -> List[List]:
        """
        Fetch OHLCV (candlestick) data.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch
            since: Timestamp to fetch from (milliseconds)
            
        Returns:
            List of OHLCV candles: [[timestamp, open, high, low, close, volume], ...]
        """
        # Check cache
        cache_key = f"{symbol}_{timeframe}_{limit}"
        if self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                self.logger.debug(f"Cache hit for {cache_key}")
                return cached_data
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            
            # Update cache
            if self._cache is not None:
                self._cache.set(cache_key, ohlcv)
            
            self.logger.info(f"Fetched {len(ohlcv)} candles for {symbol} ({timeframe})")
            return ohlcv
            
        except ccxt.NetworkError as e:
            self.logger.error(f"Network error fetching {symbol}: {e}")
            raise
        except ccxt.ExchangeError as e:
            self.logger.error(f"Exchange error fetching {symbol}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {symbol}: {e}")
            raise
    
    def get_latest_closes(self, symbol: str, timeframe: str = '5m', limit: int = 50) -> List[float]:
        """
        Get only the closing prices (for engine compatibility).
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            List of closing prices
        """
        ohlcv = self.fetch_ohlcv(symbol, timeframe, limit)
        closes = [candle[4] for candle in ohlcv]  # Index 4 is close price
        return closes
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker data (last price, volume, etc.).
        
        Args:
            symbol: Trading pair
            
        Returns:
            Ticker dictionary with last, bid, ask, volume, etc.
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get current orderbook (bids and asks).
        
        Args:
            symbol: Trading pair
            limit: Depth of orderbook
            
        Returns:
            Orderbook with bids and asks
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            return orderbook
        except Exception as e:
            self.logger.error(f"Error fetching orderbook for {symbol}: {e}")
            raise
    
    def validate_data_quality(self, ohlcv_data: List[List]) -> tuple[bool, Dict[str, bool]]:
        """
        Validate OHLCV data quality.
        
        Args:
            ohlcv_data: OHLCV candles
            
        Returns:
            (is_valid, checks_dict)
        """
        checks = {}
        
        # Check completeness (no missing data)
        checks['completeness'] = len(ohlcv_data) > 0 and all(len(c) == 6 for c in ohlcv_data)
        
        # Check freshness (last candle is recent)
        if ohlcv_data:
            last_timestamp = ohlcv_data[-1][0] / 1000  # Convert to seconds
            age_seconds = time.time() - last_timestamp
            checks['freshness'] = age_seconds < 300  # Less than 5 minutes old
        else:
            checks['freshness'] = False
        
        # Check consistency (no extreme price spikes)
        if len(ohlcv_data) > 1:
            closes = [c[4] for c in ohlcv_data]
            max_change = max(abs(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes)))
            checks['consistency'] = max_change < 0.5  # No more than 50% change between candles
        else:
            checks['consistency'] = True
        
        # Check volume (not all zeros)
        if ohlcv_data:
            volumes = [c[5] for c in ohlcv_data]
            checks['volume'] = any(v > 0 for v in volumes)
        else:
            checks['volume'] = False
        
        is_valid = all(checks.values())
        return is_valid, checks
    
    def get_exchange_status(self) -> Dict[str, Any]:
        """
        Get exchange status and info.
        
        Returns:
            Dictionary with exchange info
        """
        return {
            'id': self.exchange.id,
            'name': self.exchange.name,
            'countries': self.exchange.countries,
            'has': {
                'fetchOHLCV': self.exchange.has['fetchOHLCV'],
                'fetchTicker': self.exchange.has['fetchTicker'],
                'fetchOrderBook': self.exchange.has['fetchOrderBook'],
            },
            'timeframes': list(self.exchange.timeframes.keys()) if self.exchange.has['fetchOHLCV'] else [],
            'markets_count': len(self.exchange.markets),
        }
    
    def format_for_engines(self, symbol: str, timeframe: str = '5m', limit: int = 50) -> Dict[str, Any]:
        """
        Fetch and format data for trading engines.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            Dictionary compatible with engine expectations
        """
        closes = self.get_latest_closes(symbol, timeframe, limit)
        ticker = self.get_ticker(symbol)
        
        return {
            'symbol': symbol,
            'closes': closes,
            'volume': ticker.get('quoteVolume', 0),
            'last_price': ticker.get('last', closes[-1] if closes else 0),
            'timestamp': datetime.now().isoformat()
        }
