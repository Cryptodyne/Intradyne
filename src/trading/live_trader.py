# Live Trader - Main Orchestrator for Real Money Trading
"""Live trading orchestrator with safety features and kill switches.

This module provides the LiveTrader class which:
- Orchestrates real-time trading with actual exchange APIs
- Integrates OrderExecutor and PositionManager
- Implements circuit breakers and safety limits
- Enforces daily loss limits and drawdown controls
- Provides emergency shutdown functionality

SAFETY FEATURES:
- 5% daily loss limit (auto-shutdown)
- Max position size per trade
- Drawdown-based circuit breaker
- Manual kill switch (emergency stop)
- Testnet-only mode enforced
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from threading import Thread, Event

from src.trading.order_executor import OrderExecutor
from src.trading.position_manager_live import PositionManager

logger = logging.getLogger(__name__)


class LiveTrader:
    """Main live trading orchestrator with advanced safety controls."""
    
    def __init__(
        self,
        exchange_id: str = "bitget",
        api_key: str = "bg_9c5dcee3c08ae511344269760009c409",
        api_secret: str = "6561347d257a454cbe50167dc7e305b683e74d2b85fb172a2d21fdbc263a9b5b",
        api_password: str = "Intradyne",
        initial_capital: float = 10000,
        daily_loss_limit_pct: float = 5.0,
        max_position_pct: float = 20.0,
        max_drawdown_pct: float = 15.0,
        testnet: bool = True,
    ):
        """Initialize LiveTrader.
        
        Args:
            exchange_id: Exchange name (e.g., 'bitget')
            api_key: API key
            api_secret: API secret
            api_password: API password
            initial_capital: Starting capital in USD
            daily_loss_limit_pct: Max daily loss % before auto-shutdown
            max_position_pct: Max position size per trade as % of capital
            max_drawdown_pct: Max drawdown % before circuit breaker
            testnet: If True, use testnet (ALWAYS True for safety)
        """
        # Force testnet mode
        if not testnet:
            logger.warning("❌ TESTNET DISABLED - FORCING TESTNET FOR SAFETY")
            testnet = True
        
        self.exchange_id = exchange_id
        self.initial_capital = initial_capital
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.testnet = testnet
        
        # Initialize components
        self.executor = OrderExecutor(
            exchange_id=exchange_id,
            api_key=api_key,
            api_secret=api_secret,
            api_password=api_password,
            testnet=testnet,
        )
        
        max_position_usd = initial_capital * (max_position_pct / 100)
        self.position_manager = PositionManager(
            executor=self.executor,
            max_position_usd=max_position_usd,
        )
        
        # State tracking
        self.equity = initial_capital
        self.peak_equity = initial_capital
        self.daily_start_equity = initial_capital
        self.pnl = 0.0
        self.daily_pnl = 0.0
        self.trades = []
        
        # Safety controls
        self.trading_enabled = True
        self.circuit_breaker_triggered = False
        self.daily_loss_limit_hit = False
        
        # Monitoring thread
        self._monitor_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        logger.info(
            f"✅ LiveTrader initialized | "
            f"Exchange: {exchange_id.upper()} | "
            f"Capital: ${initial_capital:,.2f} | "
            f"Daily Loss Limit: {daily_loss_limit_pct}% | "
            f"Max Position: {max_position_pct}% | "
            f"⚠️ TESTNET MODE"
        )
    
    def start(self):
        """Start live trading system."""
        # Start position auto-sync
        self.position_manager.start_auto_sync()
        
        # Start monitoring thread
        self._stop_event.clear()
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("✅ Live trading started")
    
    def stop(self):
        """Stop live trading system (EMERGENCY SHUTDOWN)."""
        logger.warning("🛑 EMERGENCY SHUTDOWN INITIATED")
        
        # Disable trading
        self.trading_enabled = False
        
        # Cancel all open orders
        cancelled = self.executor.cancel_all_orders()
        logger.warning(f"🛑 Cancelled {cancelled} open orders")
        
        # Stop monitoring
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        # Stop position sync
        self.position_manager.stop_auto_sync()
        
        # Export audit trail
        self.position_manager.export_to_csv()
        
        logger.warning("🛑 SHUTDOWN COMPLETE")
    
    def _monitor_loop(self):
        """Background monitoring loop for safety checks."""
        while not self._stop_event.is_set():
            try:
                self._check_safety_limits()
                self._reset_daily_pnl_if_needed()
            except Exception as e:
                logger.error(f"❌ Monitor error: {e}")
            
            self._stop_event.wait(10)  # Check every 10 seconds
    
    def _check_safety_limits(self):
        """Check safety limits and trigger circuit breakers if needed."""
        # Update equity
        self._update_equity()
        
        # Check daily loss limit
        daily_loss_pct = abs(self.daily_pnl / self.daily_start_equity * 100) if self.daily_start_equity > 0 else 0
        
        if self.daily_pnl < 0 and daily_loss_pct >= self.daily_loss_limit_pct:
            if not self.daily_loss_limit_hit:
                logger.critical(
                    f"🛑 DAILY LOSS LIMIT HIT: {daily_loss_pct:.2f}% | "
                    f"P&L: ${self.daily_pnl:,.2f} | SHUTTING DOWN"
                )
                self.daily_loss_limit_hit = True
                self.stop()
        
        # Check max drawdown
        drawdown_pct = (self.peak_equity - self.equity) / self.peak_equity * 100 if self.peak_equity > 0 else 0
        
        if drawdown_pct >= self.max_drawdown_pct:
            if not self.circuit_breaker_triggered:
                logger.critical(
                    f"🛑 CIRCUIT BREAKER TRIGGERED: Drawdown {drawdown_pct:.2f}% | "
                    f"Peak: ${self.peak_equity:,.2f} | Current: ${self.equity:,.2f}"
                )
                self.circuit_breaker_triggered = True
                self.stop()
        
        # Update peak equity
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
    
    def _reset_daily_pnl_if_needed(self):
        """Reset daily P&L at midnight UTC."""
        now = datetime.utcnow()
        if now.hour == 0 and now.minute == 0:
            logger.info(f"📊 Daily reset | P&L: ${self.daily_pnl:,.2f}")
            self.daily_start_equity = self.equity
            self.daily_pnl = 0.0
            self.daily_loss_limit_hit = False
    
    def _update_equity(self):
        """Update current equity from positions and cash."""
        # Get position value
        position_value = self.position_manager.get_total_value_usd()
        
        # Get cash balance
        try:
            balance = self.executor.exchange.fetch_balance()
            cash = balance['total'].get('USDT', 0)
        except Exception as e:
            logger.error(f"❌ Failed to fetch balance: {e}")
            cash = 0
        
        # Update equity
        self.equity = cash + position_value
        self.pnl = self.equity - self.initial_capital
        self.daily_pnl = self.equity - self.daily_start_equity
    
    def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = 'market',
        price: Optional[float] = None,
    ) -> Optional[Dict]:
        """Place an order with safety checks.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Order quantity
            order_type: 'market', 'limit', or 'stop'
            price: Price for limit/stop orders
        
        Returns:
            Order dict or None if rejected
        """
        # Check if trading enabled
        if not self.trading_enabled:
            logger.warning("⚠️ Trading disabled - order rejected")
            return None
        
        # Check circuit breakers
        if self.circuit_breaker_triggered or self.daily_loss_limit_hit:
            logger.warning("⚠️ Circuit breaker active - order rejected")
            return None
        
        # Check position limits
        if side == 'buy':
            order_value_usd = amount * (price if price else 0)  # Approximate
            if not self.position_manager.check_position_limit(symbol, order_value_usd):
                logger.warning(f"⚠️ Position limit exceeded - order rejected: {symbol}")
                return None
        
        # Place order via executor
        if order_type == 'market':
            order = self.executor.place_market_order(symbol, side, amount)
        elif order_type == 'limit':
            order = self.executor.place_limit_order(symbol, side, amount, price)
        elif order_type == 'stop':
            order = self.executor.place_stop_loss_order(symbol, side, amount, price)
        else:
            logger.error(f"❌ Unknown order type: {order_type}")
            return None
        
        # Track trade
        if order:
            self.trades.append(order)
            logger.info(f"✅ Order placed: {order['id']}")
        
        return order
    
    def get_stats(self) -> Dict:
        """Get live trader statistics.
        
        Returns:
            Dict with comprehensive stats
        """
        self._update_equity()
        
        return {
            'equity': f"${self.equity:,.2f}",
            'pnl': f"${self.pnl:,.2f}",
            'daily_pnl': f"${self.daily_pnl:,.2f}",
            'peak_equity': f"${self.peak_equity:,.2f}",
            'drawdown_pct': f"{(self.peak_equity - self.equity) / self.peak_equity * 100:.2f}%",
            'total_trades': len(self.trades),
            'trading_enabled': self.trading_enabled,
            'circuit_breaker': self.circuit_breaker_triggered,
            'daily_loss_limit_hit': self.daily_loss_limit_hit,
            'testnet_mode': self.testnet,
            **self.executor.get_stats(),
            **self.position_manager.get_stats(),
        }
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()
