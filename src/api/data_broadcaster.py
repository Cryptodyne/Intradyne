"""
Data Broadcaster Service
Monitors trading activity and broadcasts updates to WebSocket clients.
"""

import asyncio
import os
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging

# File watcher
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logging.warning("watchdog not installed - file watching disabled")

logger = logging.getLogger(__name__)


class TradingDataHandler(FileSystemEventHandler):
    """File system event handler for trading data files."""
    
    def __init__(self, broadcaster):
        self.broadcaster = broadcaster
        self.last_modified = {}
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        # Only process CSV and log files
        if not (event.src_path.endswith('.csv') or event.src_path.endswith('.log')):
            return
        
        # Debounce: avoid processing same file multiple times rapidly
        now = time.time()
        if event.src_path in self.last_modified:
            if now - self.last_modified[event.src_path] < 1.0:  # 1 second debounce
                return
        
        self.last_modified[event.src_path] = now
        
        logger.info(f"File modified: {event.src_path}")
        asyncio.create_task(self.broadcaster.on_file_change(event.src_path))


class DataBroadcaster:
    """
    Monitors trading data sources and broadcasts updates to WebSocket clients.
    Supports file watching, database listeners, and manual triggers.
    """
    
    def __init__(self, manager, enable_file_watcher: bool = True):
        """
        Initialize broadcaster.
        
        Args:
            manager: WebSocket connection manager instance
            enable_file_watcher: Enable filesystem monitoring
        """
        self.manager = manager
        self.enable_file_watcher = enable_file_watcher
        self.observer = None
        self.redis_client = None
        self._running = False
        
        # Paths to monitor
        self.watch_paths = [
            'reports',
            'logs'
        ]
    
    async def start(self):
        """Start the broadcaster service."""
        logger.info("Starting Data Broadcaster...")
        self._running = True
        
        # Start file watcher
        if self.enable_file_watcher and WATCHDOG_AVAILABLE:
            self._start_file_watcher()
        
        # Start Redis subscriber (if available)
        # await self._start_redis_subscriber()
        
        logger.info("Data Broadcaster started successfully")
    
    def stop(self):
        """Stop the broadcaster service."""
        logger.info("Stopping Data Broadcaster...")
        self._running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        logger.info("Data Broadcaster stopped")
    
    def _start_file_watcher(self):
        """Start watching filesystem for changes."""
        try:
            self.observer = Observer()
            handler = TradingDataHandler(self)
            
            for path in self.watch_paths:
                if os.path.exists(path):
                    self.observer.schedule(handler, path, recursive=False)
                    logger.info(f"Watching directory: {path}")
            
            self.observer.start()
            logger.info("File watcher started")
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
    
    async def on_file_change(self, file_path: str):
        """
        Handle file change event.
        
        Args:
            file_path: Path to modified file
        """
        try:
            # Parse file and extract latest data
            if 'rag_paper_trades.csv' in file_path:
                data = await self._read_latest_trades(file_path)
                if data:
                    await self.broadcast_trade_update(data)
            
            elif 'paper_trading.log' in file_path:
                data = await self._read_latest_log(file_path)
                if data:
                    await self.broadcast_price_update(data)
        
        except Exception as e:
            logger.error(f"Error processing file change: {e}")
    
    async def _read_latest_trades(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Read latest trade from CSV file."""
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            
            if df.empty:
                return None
            
            # Get last trade
            latest = df.iloc[-1].to_dict()
            
            return {
                "type": "trade",
                "data": {
                    "symbol": latest.get('symbol'),
                    "side": latest.get('side'),
                    "price": float(latest.get('price', 0)),
                    "quantity": float(latest.get('quantity', 0)),
                    "timestamp": latest.get('timestamp'),
                },
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Error reading trades CSV: {e}")
            return None
    
    async def _read_latest_log(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse latest price from log file."""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()[-10:]  # Last 10 lines
            
            prices = {}
            for line in reversed(lines):
                if 'BTC/USDT:' in line and '$' in line:
                    try:
                        price_str = line.split('$')[1].split()[0].replace(',', '')
                        prices['BTC/USDT'] = float(price_str)
                    except: pass
                
                if 'ETH/USDT:' in line and '$' in line:
                    try:
                        price_str = line.split('$')[1].split()[0].replace(',', '')
                        prices['ETH/USDT'] = float(price_str)
                    except: pass
                
                if len(prices) >= 2:
                    break
            
            if prices:
                return {
                    "type": "price_update",
                    "data": prices,
                    "timestamp": time.time()
                }
        
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
        
        return None
    
    async def broadcast_trade_update(self, data: Dict[str, Any]):
        """
        Broadcast trade update to relevant channels.
        
        Args:
            data: Trade data dict
        """
        symbol = data.get('data', {}).get('symbol')
        
        # Broadcast to all clients
        await self.manager.broadcast_all(data)
        
        # Broadcast to symbol-specific channel
        if symbol:
            await self.manager.broadcast_channel(f"trades:{symbol}", data)
        
        logger.debug(f"Broadcast trade update: {symbol}")
    
    async def broadcast_price_update(self, data: Dict[str, Any]):
        """
        Broadcast price update to clients.
        
        Args:
            data: Price data dict
        """
        # Broadcast to all clients
        await self.manager.broadcast_all(data)
        
        # Broadcast to symbol-specific channels
        prices = data.get('data', {})
        for symbol, price in prices.items():
            await self.manager.broadcast_channel(
                f"prices:{symbol}",
                {
                    "type": "price_update",
                    "data": {"symbol": symbol, "price": price},
                    "timestamp": data.get('timestamp')
                }
            )
        
        logger.debug(f"Broadcast price update: {list(prices.keys())}")
    
    async def broadcast_ai_signal(self, symbol: str, signal: Dict[str, Any]):
        """
        Broadcast AI signal to clients.
        
        Args:
            symbol: Trading symbol
            signal: AI signal data
        """
        data = {
            "type": "ai_signal",
            "data": {
                "symbol": symbol,
                "signal": signal
            },
            "timestamp": time.time()
        }
        
        # Broadcast to all
        await self.manager.broadcast_all(data)
        
        # Broadcast to symbol channel
        await self.manager.broadcast_channel(f"signals:{symbol}", data)
        
        logger.info(f"Broadcast AI signal: {symbol} -> {signal.get('action')}")
    
    async def broadcast_status(self, status: Dict[str, Any]):
        """
        Broadcast system status update.
        
        Args:
            status: Status data dict
        """
        data = {
            "type": "status",
            "data": status,
            "timestamp": time.time()
        }
        
        await self.manager.broadcast_all(data)
        logger.debug("Broadcast status update")


# Global broadcaster instance
broadcaster = None


def get_broadcaster(manager):
    """Get or create broadcaster instance."""
    global broadcaster
    if broadcaster is None:
        broadcaster = DataBroadcaster(manager, enable_file_watcher=True)
    return broadcaster
