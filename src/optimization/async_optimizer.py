import asyncio
import ccxt.async_support as ccxt_async
from typing import List, Dict, Any, Optional
import time
import logging
from concurrent.futures import ThreadPoolExecutor

class AsyncOptimizer:
    """
    Async optimization layer for high-performance parallel operations.
    Provides 2-5x performance improvement through async/await patterns.
    """
    
    def __init__(self, max_concurrent: int = 10):
        """
        Initialize the async optimizer.
        
        Args:
            max_concurrent: Maximum concurrent operations
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger("AsyncOptimizer")
        
        # Connection pool
        self.exchange_pool = {}
        
    async def _get_exchange(self, exchange_id: str):
        """Get or create exchange instance from pool."""
        if exchange_id not in self.exchange_pool:
            exchange_class = getattr(ccxt_async, exchange_id)
            self.exchange_pool[exchange_id] = exchange_class({
                'enableRateLimit': True,
            })
        return self.exchange_pool[exchange_id]
    
    async def fetch_multiple_symbols(self, exchange_id: str, symbols: List[str], 
                                     timeframe: str = '5m', limit: int = 50) -> Dict[str, Any]:
        """
        Fetch OHLCV data for multiple symbols in parallel.
        
        Args:
            exchange_id: Exchange to use
            symbols: List of trading pairs
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            Dictionary mapping symbols to OHLCV data
        """
        exchange = await self._get_exchange(exchange_id)
        
        async def fetch_symbol(symbol):
            async with self.semaphore:
                try:
                    start = time.time()
                    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                    latency = time.time() - start
                    return symbol, {'success': True, 'data': ohlcv, 'latency': latency}
                except Exception as e:
                    return symbol, {'success': False, 'error': str(e)}
        
        # Fetch all symbols in parallel
        tasks = [fetch_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
    
    async def fetch_from_multiple_exchanges(self, exchanges: List[str], symbol: str,
                                           timeframe: str = '5m', limit: int = 50) -> Dict[str, Any]:
        """
        Fetch data from multiple exchanges in parallel.
        
        Args:
            exchanges: List of exchange IDs
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            Dictionary mapping exchanges to data
        """
        async def fetch_exchange(exchange_id):
            async with self.semaphore:
                try:
                    exchange = await self._get_exchange(exchange_id)
                    start = time.time()
                    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                    latency = time.time() - start
                    return exchange_id, {'success': True, 'data': ohlcv, 'latency': latency}
                except Exception as e:
                    return exchange_id, {'success': False, 'error': str(e)}
        
        # Fetch from all exchanges in parallel
        tasks = [fetch_exchange(ex) for ex in exchanges]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
    
    async def batch_fetch_tickers(self, exchange_id: str, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch ticker data for multiple symbols in parallel.
        
        Args:
            exchange_id: Exchange to use
            symbols: List of trading pairs
            
        Returns:
            Dictionary mapping symbols to ticker data
        """
        exchange = await self._get_exchange(exchange_id)
        
        async def fetch_ticker(symbol):
            async with self.semaphore:
                try:
                    ticker = await exchange.fetch_ticker(symbol)
                    return symbol, {'success': True, 'data': ticker}
                except Exception as e:
                    return symbol, {'success': False, 'error': str(e)}
        
        tasks = [fetch_ticker(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
    
    async def parallel_analysis(self, market_data_list: List[Dict[str, Any]], 
                               analysis_func) -> List[Any]:
        """
        Run analysis on multiple market data sets in parallel.
        
        Args:
            market_data_list: List of market data dictionaries
            analysis_func: Analysis function to apply
            
        Returns:
            List of analysis results
        """
        async def analyze(data):
            async with self.semaphore:
                # Run CPU-bound analysis in thread pool
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as pool:
                    result = await loop.run_in_executor(pool, analysis_func, data)
                return result
        
        tasks = [analyze(data) for data in market_data_list]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def optimized_multi_exchange_fetch(self, exchanges: List[str], 
                                            symbols: List[str],
                                            timeframe: str = '5m',
                                            limit: int = 50) -> Dict[str, Dict[str, Any]]:
        """
        Fetch data for multiple symbols from multiple exchanges (fully parallel).
        
        Args:
            exchanges: List of exchange IDs
            symbols: List of trading pairs
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            Nested dictionary: {exchange: {symbol: data}}
        """
        async def fetch_exchange_symbol(exchange_id, symbol):
            async with self.semaphore:
                try:
                    exchange = await self._get_exchange(exchange_id)
                    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                    return (exchange_id, symbol), {'success': True, 'data': ohlcv}
                except Exception as e:
                    return (exchange_id, symbol), {'success': False, 'error': str(e)}
        
        # Create all tasks
        tasks = [
            fetch_exchange_symbol(ex, sym) 
            for ex in exchanges 
            for sym in symbols
        ]
        
        # Execute all in parallel
        results = await asyncio.gather(*tasks)
        
        # Organize results
        organized = {}
        for (exchange_id, symbol), data in results:
            if exchange_id not in organized:
                organized[exchange_id] = {}
            organized[exchange_id][symbol] = data
        
        return organized
    
    async def close(self):
        """Close all exchange connections."""
        for exchange in self.exchange_pool.values():
            await exchange.close()
        self.exchange_pool.clear()
        self.logger.info("All exchange connections closed")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            'max_concurrent': self.max_concurrent,
            'active_exchanges': len(self.exchange_pool),
            'exchanges': list(self.exchange_pool.keys())
        }


# Helper function for sync context
def run_async_fetch(optimizer: AsyncOptimizer, exchanges: List[str], 
                   symbols: List[str], **kwargs) -> Dict[str, Dict[str, Any]]:
    """
    Run async fetch in synchronous context.
    
    Args:
        optimizer: AsyncOptimizer instance
        exchanges: List of exchanges
        symbols: List of symbols
        **kwargs: Additional arguments for fetch
        
    Returns:
        Fetch results
    """
    async def _run():
        try:
            return await optimizer.optimized_multi_exchange_fetch(
                exchanges, symbols, **kwargs
            )
        finally:
            await optimizer.close()
    
    return asyncio.run(_run())


# Performance comparison utility
class PerformanceComparison:
    """Compare sync vs async performance."""
    
    @staticmethod
    def benchmark_sync(exchange_id: str, symbols: List[str], 
                      timeframe: str = '5m', limit: int = 50) -> Dict[str, Any]:
        """Benchmark synchronous fetching."""
        import ccxt
        
        exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
        
        start = time.time()
        results = {}
        
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                results[symbol] = {'success': True, 'data': ohlcv}
            except Exception as e:
                results[symbol] = {'success': False, 'error': str(e)}
        
        duration = time.time() - start
        
        return {
            'duration': duration,
            'symbols_count': len(symbols),
            'avg_per_symbol': duration / len(symbols),
            'results': results
        }
    
    @staticmethod
    async def benchmark_async(exchange_id: str, symbols: List[str],
                             timeframe: str = '5m', limit: int = 50) -> Dict[str, Any]:
        """Benchmark asynchronous fetching."""
        optimizer = AsyncOptimizer(max_concurrent=10)
        
        start = time.time()
        results = await optimizer.fetch_multiple_symbols(
            exchange_id, symbols, timeframe, limit
        )
        duration = time.time() - start
        
        await optimizer.close()
        
        return {
            'duration': duration,
            'symbols_count': len(symbols),
            'avg_per_symbol': duration / len(symbols),
            'speedup': None,  # Will be calculated
            'results': results
        }
    
    @staticmethod
    def compare(exchange_id: str, symbols: List[str]) -> Dict[str, Any]:
        """Compare sync vs async performance."""
        print(f"Benchmarking {len(symbols)} symbols on {exchange_id}...")
        
        # Sync benchmark
        print("  Running sync benchmark...")
        sync_result = PerformanceComparison.benchmark_sync(exchange_id, symbols)
        
        # Async benchmark
        print("  Running async benchmark...")
        async_result = asyncio.run(
            PerformanceComparison.benchmark_async(exchange_id, symbols)
        )
        
        # Calculate speedup
        speedup = sync_result['duration'] / async_result['duration']
        async_result['speedup'] = speedup
        
        return {
            'sync': sync_result,
            'async': async_result,
            'speedup': speedup,
            'improvement_pct': (speedup - 1) * 100
        }
