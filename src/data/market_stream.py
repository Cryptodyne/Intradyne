import asyncio
import ccxt.pro as ccxtpro
import logging
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
import json

class MarketDataStream:
    """
    Real-time market data streaming using WebSocket.
    Provides low-latency price updates with automatic reconnection.
    """
    
    def __init__(self, exchange_id: str = 'binance', max_buffer_size: int = 1000):
        """
        Initialize the WebSocket stream.
        
        Args:
            exchange_id: Exchange to connect to
            max_buffer_size: Maximum number of updates to buffer
        """
        self.exchange_id = exchange_id
        self.max_buffer_size = max_buffer_size
        self.logger = logging.getLogger(f"WebSocketStream_{exchange_id}")
        
        # Initialize exchange
        exchange_class = getattr(ccxtpro, exchange_id)
        self.exchange = exchange_class({
            'enableRateLimit': True,
        })
        
        # Subscriptions and callbacks
        self.subscriptions = {}
        self.running = False
        self.tasks = []
        
        # Data buffers
        self.ticker_buffer = {}
        self.trades_buffer = {}
        self.orderbook_buffer = {}
    
    async def subscribe_ticker(self, symbol: str, callback: Optional[Callable] = None):
        """
        Subscribe to ticker updates for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            callback: Optional callback function(ticker_data)
        """
        self.logger.info(f"Subscribing to ticker: {symbol}")
        
        if symbol not in self.ticker_buffer:
            self.ticker_buffer[symbol] = []
        
        async def watch_ticker():
            while self.running:
                try:
                    ticker = await self.exchange.watch_ticker(symbol)
                    
                    # Add to buffer
                    self.ticker_buffer[symbol].append({
                        'symbol': ticker['symbol'],
                        'last': ticker['last'],
                        'bid': ticker['bid'],
                        'ask': ticker['ask'],
                        'volume': ticker['quoteVolume'],
                        'timestamp': ticker['timestamp'],
                        'datetime': ticker['datetime']
                    })
                    
                    # Trim buffer if too large
                    if len(self.ticker_buffer[symbol]) > self.max_buffer_size:
                        self.ticker_buffer[symbol] = self.ticker_buffer[symbol][-self.max_buffer_size:]
                    
                    # Call callback if provided
                    if callback:
                        await callback(self.ticker_buffer[symbol][-1])
                    
                except Exception as e:
                    self.logger.error(f"Error watching ticker {symbol}: {e}")
                    await asyncio.sleep(5)  # Wait before retry
        
        task = asyncio.create_task(watch_ticker())
        self.tasks.append(task)
        self.subscriptions[f"ticker_{symbol}"] = task
    
    async def subscribe_trades(self, symbol: str, callback: Optional[Callable] = None):
        """
        Subscribe to trade updates for a symbol.
        
        Args:
            symbol: Trading pair
            callback: Optional callback function(trades_data)
        """
        self.logger.info(f"Subscribing to trades: {symbol}")
        
        if symbol not in self.trades_buffer:
            self.trades_buffer[symbol] = []
        
        async def watch_trades():
            while self.running:
                try:
                    trades = await self.exchange.watch_trades(symbol)
                    
                    for trade in trades:
                        trade_data = {
                            'symbol': trade['symbol'],
                            'price': trade['price'],
                            'amount': trade['amount'],
                            'side': trade['side'],
                            'timestamp': trade['timestamp'],
                            'datetime': trade['datetime']
                        }
                        
                        self.trades_buffer[symbol].append(trade_data)
                        
                        # Call callback if provided
                        if callback:
                            await callback(trade_data)
                    
                    # Trim buffer
                    if len(self.trades_buffer[symbol]) > self.max_buffer_size:
                        self.trades_buffer[symbol] = self.trades_buffer[symbol][-self.max_buffer_size:]
                    
                except Exception as e:
                    self.logger.error(f"Error watching trades {symbol}: {e}")
                    await asyncio.sleep(5)
        
        task = asyncio.create_task(watch_trades())
        self.tasks.append(task)
        self.subscriptions[f"trades_{symbol}"] = task
    
    async def subscribe_orderbook(self, symbol: str, callback: Optional[Callable] = None, limit: int = 20):
        """
        Subscribe to orderbook updates for a symbol.
        
        Args:
            symbol: Trading pair
            callback: Optional callback function(orderbook_data)
            limit: Depth of orderbook
        """
        self.logger.info(f"Subscribing to orderbook: {symbol}")
        
        if symbol not in self.orderbook_buffer:
            self.orderbook_buffer[symbol] = []
        
        async def watch_orderbook():
            while self.running:
                try:
                    orderbook = await self.exchange.watch_order_book(symbol, limit)
                    
                    orderbook_data = {
                        'symbol': orderbook['symbol'],
                        'bids': orderbook['bids'][:limit],
                        'asks': orderbook['asks'][:limit],
                        'timestamp': orderbook['timestamp'],
                        'datetime': orderbook['datetime']
                    }
                    
                    self.orderbook_buffer[symbol].append(orderbook_data)
                    
                    # Trim buffer
                    if len(self.orderbook_buffer[symbol]) > self.max_buffer_size:
                        self.orderbook_buffer[symbol] = self.orderbook_buffer[symbol][-self.max_buffer_size:]
                    
                    # Call callback if provided
                    if callback:
                        await callback(orderbook_data)
                    
                except Exception as e:
                    self.logger.error(f"Error watching orderbook {symbol}: {e}")
                    await asyncio.sleep(5)
        
        task = asyncio.create_task(watch_orderbook())
        self.tasks.append(task)
        self.subscriptions[f"orderbook_{symbol}"] = task
    
    def start_stream(self):
        """Start the WebSocket stream."""
        self.running = True
        self.logger.info("WebSocket stream started")
    
    async def stop_stream(self):
        """Stop the WebSocket stream and cleanup."""
        self.logger.info("Stopping WebSocket stream...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Close exchange connection
        await self.exchange.close()
        
        self.logger.info("WebSocket stream stopped")
    
    def get_latest_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the latest ticker data for a symbol."""
        if symbol in self.ticker_buffer and self.ticker_buffer[symbol]:
            return self.ticker_buffer[symbol][-1]
        return None
    
    def get_latest_trades(self, symbol: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get the latest trades for a symbol."""
        if symbol in self.trades_buffer:
            return self.trades_buffer[symbol][-count:]
        return []
    
    def get_latest_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the latest orderbook for a symbol."""
        if symbol in self.orderbook_buffer and self.orderbook_buffer[symbol]:
            return self.orderbook_buffer[symbol][-1]
        return None
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get statistics about buffered data."""
        return {
            'tickers': {symbol: len(buffer) for symbol, buffer in self.ticker_buffer.items()},
            'trades': {symbol: len(buffer) for symbol, buffer in self.trades_buffer.items()},
            'orderbooks': {symbol: len(buffer) for symbol, buffer in self.orderbook_buffer.items()},
            'total_subscriptions': len(self.subscriptions),
            'running': self.running
        }


# Helper function to run async stream in sync context
def run_stream_sync(stream: MarketDataStream, symbols: List[str], duration: int = 60):
    """
    Run WebSocket stream synchronously for a specified duration.
    
    Args:
        stream: MarketDataStream instance
        symbols: List of symbols to subscribe to
        duration: Duration to run in seconds
    """
    async def run():
        stream.start_stream()
        
        # Subscribe to all symbols
        for symbol in symbols:
            await stream.subscribe_ticker(symbol)
        
        # Run for specified duration
        await asyncio.sleep(duration)
        
        # Stop stream
        await stream.stop_stream()
    
    asyncio.run(run())
