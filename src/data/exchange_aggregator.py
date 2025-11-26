import ccxt
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

class ExchangeAggregator:
    """
    Aggregates data from multiple exchanges for redundancy and arbitrage detection.
    """
    
    def __init__(self, exchanges: List[str] = None, max_workers: int = 3):
        """
        Initialize the aggregator.
        
        Args:
            exchanges: List of exchange IDs (default: ['binance', 'bybit'])
            max_workers: Maximum concurrent exchange connections
        """
        self.exchange_ids = exchanges or ['binance', 'bybit']
        self.max_workers = max_workers
        self.exchanges = {}
        self.logger = logging.getLogger("ExchangeAggregator")
        
        # Initialize exchanges
        for exchange_id in self.exchange_ids:
            try:
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class({
                    'enableRateLimit': True,
                    'timeout': 30000,
                })
                self.exchanges[exchange_id].load_markets()
                self.logger.info(f"Connected to {exchange_id}")
            except Exception as e:
                self.logger.error(f"Failed to initialize {exchange_id}: {e}")
    
    def fetch_from_all_exchanges(self, symbol: str, timeframe: str = '5m', 
                                 limit: int = 50) -> Dict[str, Any]:
        """
        Fetch OHLCV data from all exchanges in parallel.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            Dictionary with data from each exchange
        """
        results = {}
        
        def fetch_from_exchange(exchange_id):
            try:
                exchange = self.exchanges[exchange_id]
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                return exchange_id, {
                    'success': True,
                    'data': ohlcv,
                    'timestamp': time.time()
                }
            except Exception as e:
                self.logger.error(f"Error fetching from {exchange_id}: {e}")
                return exchange_id, {
                    'success': False,
                    'error': str(e),
                    'timestamp': time.time()
                }
        
        # Fetch in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(fetch_from_exchange, ex_id): ex_id 
                for ex_id in self.exchanges.keys()
            }
            
            for future in as_completed(futures):
                exchange_id, result = future.result()
                results[exchange_id] = result
        
        return results
    
    def get_best_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get best bid/ask prices across all exchanges.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary with best prices and exchange info
        """
        prices = {}
        
        def fetch_ticker(exchange_id):
            try:
                exchange = self.exchanges[exchange_id]
                ticker = exchange.fetch_ticker(symbol)
                return exchange_id, {
                    'success': True,
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'last': ticker['last'],
                    'volume': ticker['quoteVolume']
                }
            except Exception as e:
                return exchange_id, {'success': False, 'error': str(e)}
        
        # Fetch in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(fetch_ticker, ex_id): ex_id 
                for ex_id in self.exchanges.keys()
            }
            
            for future in as_completed(futures):
                exchange_id, result = future.result()
                if result['success']:
                    prices[exchange_id] = result
        
        if not prices:
            return {'error': 'No exchanges available'}
        
        # Find best prices
        best_bid = max(prices.items(), key=lambda x: x[1]['bid'])
        best_ask = min(prices.items(), key=lambda x: x[1]['ask'])
        
        return {
            'best_bid': {
                'exchange': best_bid[0],
                'price': best_bid[1]['bid']
            },
            'best_ask': {
                'exchange': best_ask[0],
                'price': best_ask[1]['ask']
            },
            'all_prices': prices
        }
    
    def detect_arbitrage(self, symbol: str, threshold: float = 0.5) -> Dict[str, Any]:
        """
        Detect arbitrage opportunities across exchanges.
        
        Args:
            symbol: Trading pair
            threshold: Minimum spread percentage to report (default: 0.5%)
            
        Returns:
            Dictionary with arbitrage opportunity details
        """
        best_prices = self.get_best_price(symbol)
        
        if 'error' in best_prices:
            return {'opportunity': False, 'error': best_prices['error']}
        
        best_bid = best_prices['best_bid']['price']
        best_ask = best_prices['best_ask']['price']
        
        # Calculate spread
        spread_pct = ((best_bid - best_ask) / best_ask) * 100
        
        opportunity = spread_pct > threshold
        
        return {
            'opportunity': opportunity,
            'spread': round(spread_pct, 3),
            'buy_from': best_prices['best_ask']['exchange'],
            'buy_price': best_ask,
            'sell_to': best_prices['best_bid']['exchange'],
            'sell_price': best_bid,
            'profit_per_unit': best_bid - best_ask,
            'timestamp': time.time()
        }
    
    def get_most_liquid_exchange(self, symbol: str) -> Dict[str, Any]:
        """
        Find exchange with highest volume for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary with most liquid exchange info
        """
        volumes = {}
        
        def fetch_volume(exchange_id):
            try:
                exchange = self.exchanges[exchange_id]
                ticker = exchange.fetch_ticker(symbol)
                return exchange_id, ticker['quoteVolume']
            except Exception as e:
                return exchange_id, 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(fetch_volume, ex_id): ex_id 
                for ex_id in self.exchanges.keys()
            }
            
            for future in as_completed(futures):
                exchange_id, volume = future.result()
                volumes[exchange_id] = volume
        
        if not volumes:
            return {'error': 'No data available'}
        
        most_liquid = max(volumes.items(), key=lambda x: x[1])
        
        return {
            'exchange': most_liquid[0],
            'volume': most_liquid[1],
            'all_volumes': volumes
        }
    
    def fetch_with_failover(self, symbol: str, timeframe: str = '5m', 
                           limit: int = 50, priority_order: List[str] = None) -> Dict[str, Any]:
        """
        Fetch data with automatic failover to backup exchanges.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles
            priority_order: Custom priority order (default: config order)
            
        Returns:
            Data from first successful exchange
        """
        exchange_order = priority_order or list(self.exchanges.keys())
        
        for exchange_id in exchange_order:
            try:
                exchange = self.exchanges[exchange_id]
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                
                self.logger.info(f"Successfully fetched from {exchange_id}")
                return {
                    'success': True,
                    'exchange': exchange_id,
                    'data': ohlcv,
                    'timestamp': time.time()
                }
            except Exception as e:
                self.logger.warning(f"Failed to fetch from {exchange_id}: {e}")
                continue
        
        return {
            'success': False,
            'error': 'All exchanges failed',
            'timestamp': time.time()
        }
    
    def get_exchange_status(self) -> Dict[str, Any]:
        """
        Get status of all connected exchanges.
        
        Returns:
            Dictionary with exchange statuses
        """
        statuses = {}
        
        for exchange_id, exchange in self.exchanges.items():
            try:
                # Try a simple API call to check connectivity
                exchange.fetch_status()
                statuses[exchange_id] = {
                    'connected': True,
                    'markets': len(exchange.markets),
                    'name': exchange.name
                }
            except Exception as e:
                statuses[exchange_id] = {
                    'connected': False,
                    'error': str(e)
                }
        
        return statuses
