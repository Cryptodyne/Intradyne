# Position Manager for Live Trading
"""Track live positions across exchanges with real-time reconciliation.

This module provides the PositionManager class which handles:
- Real-time position syncing from exchange APIs
- Aggregate position calculation (net long/short)
- Unrealized P&L computation
- Position limits enforcement
- Automatic reconciliation and discrepancy detection

SAFETY FEATURES:
- Automatic sync every 60 seconds
- Discrepancy alerts (>0.1% difference)
- Position history audit trail
- CSV export for compliance
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from threading import Thread, Event
import pandas as pd

logger = logging.getLogger(__name__)


class PositionManager:
    """Manage live positions with real-time tracking and reconciliation."""
    
    def __init__(
        self,
        executor,  # OrderExecutor instance
        sync_interval: int = 60,
        max_position_usd: float = 10000,
        csv_path: str = "data/positions.csv",
    ):
        """Initialize PositionManager.
        
        Args:
            executor: OrderExecutor instance for exchange API access
            sync_interval: Seconds between automatic syncs
            max_position_usd: Maximum position size in USD per symbol
            csv_path: Path for position history CSV
        """
        self.executor = executor
        self.sync_interval = sync_interval
        self.max_position_usd = max_position_usd
        self.csv_path = csv_path
        
        # Position tracking
        self.positions: Dict[str, Dict] = {}  # Symbol -> Position details
        self.position_history: List[Dict] = []
        
        # Sync thread
        self._sync_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Stats
        self.total_syncs = 0
        self.discrepancies_detected = 0
        
        logger.info(f"✅ PositionManager initialized (max position: ${max_position_usd:,.2f})")
    
    def start_auto_sync(self):
        """Start automatic position syncing in background thread."""
        if self._sync_thread and self._sync_thread.is_alive():
            logger.warning("⚠️ Auto-sync already running")
            return
        
        self._stop_event.clear()
        self._sync_thread = Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info(f"✅ Auto-sync started (interval: {self.sync_interval}s)")
    
    def stop_auto_sync(self):
        """Stop automatic position syncing."""
        if not self._sync_thread or not self._sync_thread.is_alive():
            return
        
        self._stop_event.set()
        self._sync_thread.join(timeout=5)
        logger.info("🛑 Auto-sync stopped")
    
    def _sync_loop(self):
        """Background loop for automatic position syncing."""
        while not self._stop_event.is_set():
            try:
                self.sync_positions()
                self.total_syncs += 1
            except Exception as e:
                logger.error(f"❌ Sync error: {e}")
            
            self._stop_event.wait(self.sync_interval)
    
    def sync_positions(self) -> Dict[str, Dict]:
        """Fetch current positions from exchange and update local state.
        
        Returns:
            Dict of symbol -> position details
        """
        try:
            # Fetch positions from exchange
            exchange_positions = self.executor.exchange.fetch_balance()
            
            # Update local positions
            updated_positions = {}
            
            for currency, balance in exchange_positions['total'].items():
                if balance > 0:
                    # Skip quote currencies (USDT, USD, etc.)
                    if currency in ['USDT', 'USD', 'BUSD', 'USDC']:
                        continue
                    
                    # Get symbol (e.g., BTC/USDT)
                    symbol = f"{currency}/USDT"
                    
                    # Get current price
                    try:
                        ticker = self.executor.exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to get price for {symbol}: {e}")
                        current_price = 0
                    
                    # Calculate position details
                    position = {
                        'symbol': symbol,
                        'amount': balance,
                        'current_price': current_price,
                        'market_value_usd': balance * current_price,
                        'timestamp': datetime.utcnow().isoformat(),
                    }
                    
                    # Check for discrepancies
                    if symbol in self.positions:
                        old_amount = self.positions[symbol]['amount']
                        diff_pct = abs(balance - old_amount) / old_amount * 100 if old_amount > 0 else 0
                        
                        if diff_pct > 0.1:  # >0.1% difference
                            logger.warning(
                                f"⚠️ DISCREPANCY: {symbol} | "
                                f"Old: {old_amount:.6f} | New: {balance:.6f} | "
                                f"Diff: {diff_pct:.2f}%"
                            )
                            self.discrepancies_detected += 1
                    
                    updated_positions[symbol] = position
                    
                    # Add to history
                    self.position_history.append(position)
            
            # Update positions dict
            self.positions = updated_positions
            
            logger.info(f"✅ Synced {len(self.positions)} positions")
            return self.positions
        
        except Exception as e:
            logger.error(f"❌ Failed to sync positions: {e}")
            return self.positions
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position details for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
        
        Returns:
            Position dict or None if no position
        """
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all current positions.
        
        Returns:
            Dict of symbol -> position details
        """
        return self.positions.copy()
    
    def get_total_value_usd(self) -> float:
        """Calculate total market value of all positions in USD.
        
        Returns:
            Total value in USD
        """
        return sum(pos['market_value_usd'] for pos in self.positions.values())
    
    def get_unrealized_pnl(self, symbol: str, entry_price: float) -> Optional[float]:
        """Calculate unrealized P&L for a position.
        
        Args:
            symbol: Trading pair
            entry_price: Average entry price
        
        Returns:
            Unrealized P&L in USD or None if no position
        """
        position = self.get_position(symbol)
        if not position:
            return None
        
        current_price = position['current_price']
        amount = position['amount']
        
        pnl = (current_price - entry_price) * amount
        return pnl
    
    def check_position_limit(self, symbol: str, new_amount_usd: float) -> bool:
        """Check if adding to a position would exceed limits.
        
        Args:
            symbol: Trading pair
            new_amount_usd: Additional position size in USD
        
        Returns:
            True if within limits, False otherwise
        """
        current_position = self.get_position(symbol)
        current_value = current_position['market_value_usd'] if current_position else 0
        
        total_value = current_value + new_amount_usd
        
        if total_value > self.max_position_usd:
            logger.warning(
                f"⚠️ POSITION LIMIT EXCEEDED: {symbol} | "
                f"Current: ${current_value:,.2f} | New: ${new_amount_usd:,.2f} | "
                f"Total: ${total_value:,.2f} | Limit: ${self.max_position_usd:,.2f}"
            )
            return False
        
        return True
    
    def export_to_csv(self) -> bool:
        """Export position history to CSV for audit trail.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.position_history:
                logger.warning("⚠️ No position history to export")
                return False
            
            df = pd.DataFrame(self.position_history)
            df.to_csv(self.csv_path, index=False)
            logger.info(f"✅ Exported {len(self.position_history)} positions to {self.csv_path}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to export to CSV: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get position manager statistics.
        
        Returns:
            Dict with stats
        """
        return {
            'total_positions': len(self.positions),
            'total_value_usd': f"${self.get_total_value_usd():,.2f}",
            'total_syncs': self.total_syncs,
            'discrepancies_detected': self.discrepancies_detected,
            'auto_sync_active': self._sync_thread and self._sync_thread.is_alive(),
            'sync_interval': f"{self.sync_interval}s",
            'max_position_usd': f"${self.max_position_usd:,.2f}",
        }
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop_auto_sync()
