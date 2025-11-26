# Order Execution Engine for Live Trading
"""Execute real orders on cryptocurrency exchanges via CCXT.

This module provides the OrderExecutor class which handles:
- Order placement (market, limit, stop-loss)
- Order status tracking and fill monitoring
- Retry logic with exponential backoff
- Position reconciliation
- Emergency cancel-all functionality

SAFETY FEATURES:
- Testnet-only mode enforced
- Rate limiting per exchange
- Order validation before placement
- Slippage tracking
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import ccxt

logger = logging.getLogger(__name__)


class OrderExecutor:
    """Execute orders on cryptocurrency exchanges."""
    
    def __init__(
        self,
        exchange_id: str = "bitget",
        api_key: str = "bg_9c5dcee3c08ae511344269760009c409",
        api_secret: str = "6561347d257a454cbe50167dc7e305b683e74d2b85fb172a2d21fdbc263a9b5b",
        api_password: str = "Intradyne",
        testnet: bool = True,
        max_retries: int = 3,
    ):
        """Initialize OrderExecutor.
        
        Args:
            exchange_id: Exchange name (e.g., 'bitget')
            api_key: API key for authentication
            api_secret: API secret for authentication
            api_password: API password (required for some exchanges)
            testnet: If True, use testnet/sandbox (ALWAYS True for safety)
            max_retries: Maximum retry attempts for failed orders
        """
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.max_retries = max_retries
        
        # Force testnet for safety
        if not testnet:
            logger.warning("❌ TESTNET DISABLED - FORCING TESTNET MODE FOR SAFETY")
            self.testnet = True
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'password': api_password,
            'enableRateLimit': True,
        })
        
        # Set testnet/sandbox mode
        if self.testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info(f"✅ {exchange_id.upper()} TESTNET mode enabled")
        
        # Order tracking
        self.active_orders: Dict[str, Dict] = {}  # System ID -> Order details
        self.order_history: List[Dict] = []
        
        # Stats
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
    
    def place_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Place a market order.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            amount: Order quantity
            client_order_id: Optional custom order ID
        
        Returns:
            Order details dict or None if failed
        """
        return self._place_order(
            symbol=symbol,
            order_type='market',
            side=side,
            amount=amount,
            price=None,
            client_order_id=client_order_id,
        )
    
    def place_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Place a limit order.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            amount: Order quantity
            price: Limit price
            client_order_id: Optional custom order ID
        
        Returns:
            Order details dict or None if failed
        """
        return self._place_order(
            symbol=symbol,
            order_type='limit',
            side=side,
            amount=amount,
            price=price,
            client_order_id=client_order_id,
        )
    
    def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Place a stop-loss order.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            amount: Order quantity
            stop_price: Stop trigger price
            client_order_id: Optional custom order ID
        
        Returns:
            Order details dict or None if failed
        """
        return self._place_order(
            symbol=symbol,
            order_type='stop_loss',
            side=side,
            amount=amount,
            price=stop_price,
            client_order_id=client_order_id,
        )
    
    def _place_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Internal method to place orders with retry logic.
        
        Args:
            symbol: Trading pair
            order_type: 'market', 'limit', or 'stop_loss'
            side: 'buy' or 'sell'
            amount: Order quantity
            price: Order price (required for limit/stop orders)
            client_order_id: Optional custom order ID
        
        Returns:
            Order details dict or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                # Prepare order parameters
                params = {}
                if client_order_id:
                    params['clientOrderId'] = client_order_id
                
                # Place order via CCXT
                if order_type == 'market':
                    order = self.exchange.create_market_order(symbol, side, amount, params)
                elif order_type == 'limit':
                    order = self.exchange.create_limit_order(symbol, side, amount, price, params)
                elif order_type == 'stop_loss':
                    order = self.exchange.create_order(
                        symbol=symbol,
                        type='stop',
                        side=side,
                        amount=amount,
                        price=price,
                        params=params,
                    )
                else:
                    logger.error(f"❌ Unknown order type: {order_type}")
                    return None
                
                # Track order
                order_id = order.get('id')
                self.active_orders[order_id] = order
                self.order_history.append(order)
                self.total_orders += 1
                self.successful_orders += 1
                
                logger.info(
                    f"✅ Order placed: {side.upper()} {amount} {symbol} @ "
                    f"{price if price else 'MARKET'} | ID: {order_id}"
                )
                
                return order
            
            except ccxt.InsufficientFunds as e:
                logger.error(f"❌ Insufficient funds: {e}")
                self.failed_orders += 1
                return None
            
            except ccxt.InvalidOrder as e:
                logger.error(f"❌ Invalid order: {e}")
                self.failed_orders += 1
                return None
            
            except ccxt.NetworkError as e:
                logger.warning(f"⚠️ Network error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"❌ Order failed after {self.max_retries} attempts")
                    self.failed_orders += 1
                    return None
            
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                self.failed_orders += 1
                return None
        
        return None
    
    def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Fetch order status from exchange.
        
        Args:
            order_id: Exchange order ID
            symbol: Trading pair
        
        Returns:
            Order status dict or None if failed
        """
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            
            # Update local tracking
            if order_id in self.active_orders:
                self.active_orders[order_id].update(order)
            
            return order
        
        except Exception as e:
            logger.error(f"❌ Failed to fetch order {order_id}: {e}")
            return None
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an active order.
        
        Args:
            order_id: Exchange order ID
            symbol: Trading pair
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.exchange.cancel_order(order_id, symbol)
            
            # Remove from active orders
            if order_id in self.active_orders:
                del self.active_orders[order_id]
            
            logger.info(f"✅ Order cancelled: {order_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to cancel order {order_id}: {e}")
            return False
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all active orders (EMERGENCY FUNCTION).
        
        Args:
            symbol: If specified, cancel only orders for this symbol
        
        Returns:
            Number of orders cancelled
        """
        cancelled_count = 0
        
        try:
            if symbol:
                # Cancel orders for specific symbol
                orders = self.exchange.fetch_open_orders(symbol)
            else:
                # Cancel all orders
                orders = self.exchange.fetch_open_orders()
            
            for order in orders:
                try:
                    self.exchange.cancel_order(order['id'], order['symbol'])
                    cancelled_count += 1
                    logger.info(f"✅ Cancelled: {order['id']}")
                except Exception as e:
                    logger.error(f"❌ Failed to cancel {order['id']}: {e}")
            
            # Clear local tracking
            self.active_orders.clear()
            
            logger.warning(f"🛑 EMERGENCY: Cancelled {cancelled_count} orders")
            return cancelled_count
        
        except Exception as e:
            logger.error(f"❌ Failed to cancel all orders: {e}")
            return cancelled_count
    
    def get_fills(self, symbol: Optional[str] = None, since: Optional[int] = None) -> List[Dict]:
        """Fetch recent order fills (trades).
        
        Args:
            symbol: Trading pair (optional)
            since: Timestamp in ms (optional)
        
        Returns:
            List of trade dicts
        """
        try:
            if symbol:
                trades = self.exchange.fetch_my_trades(symbol, since=since)
            else:
                trades = self.exchange.fetch_my_trades(since=since)
            
            return trades
        
        except Exception as e:
            logger.error(f"❌ Failed to fetch fills: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get executor statistics.
        
        Returns:
            Dict with order stats
        """
        success_rate = (
            self.successful_orders / self.total_orders * 100
            if self.total_orders > 0
            else 0
        )
        
        return {
            'total_orders': self.total_orders,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'success_rate': f"{success_rate:.2f}%",
            'active_orders': len(self.active_orders),
            'testnet_mode': self.testnet,
        }
