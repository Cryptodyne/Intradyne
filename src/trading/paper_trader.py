"""
Paper Trader - Main trading engine with live market data
Integrates portfolio management, risk management, and live data
"""

import time
from typing import Dict, List, Callable, Optional
from datetime import datetime
import logging

from .portfolio_manager import PortfolioManager
from .risk_manager import RiskManager

class PaperTrader:
    """
    Live paper trading engine with real market data.
    Executes strategies in real-time without risking capital.
    """
    
    def __init__(self, initial_capital: float = 10000, 
                 strategy_func: Optional[Callable] = None,
                 risk_config: Optional[Dict] = None):
        """
        Initialize paper trader.
        
        Args:
            initial_capital: Starting virtual capital
            strategy_func: Trading strategy function
            risk_config: Risk management configuration
        """
        self.portfolio = PortfolioManager(initial_capital)
        
        # Default risk config
        if risk_config is None:
            risk_config = {
                'max_positions': 5,
                'max_position_size': 0.2,
                'daily_loss_limit': 0.05,
                'max_drawdown': 0.15,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.10
            }
        
        self.risk_manager = RiskManager(risk_config)
        self.strategy_func = strategy_func
        
        self.logger = logging.getLogger("PaperTrader")
        self.is_running = False
        self.market_data_fetcher = None
        
        # Trading state
        self.current_prices = {}
        self.price_history = {}
        self.signals_history = []
    
    def connect_exchange(self, exchange_name: str = 'binance'):
        """Connect to exchange for live data"""
        try:
            from src.data.market_data import MarketDataFetcher
            self.market_data_fetcher = MarketDataFetcher(exchange_name)
            self.logger.info(f"Connected to {exchange_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to exchange: {e}")
            return False
    
    def fetch_latest_price(self, symbol: str) -> Optional[float]:
        """Fetch latest price for symbol"""
        if not self.market_data_fetcher:
            self.logger.warning("No market data fetcher connected")
            return None
        
        try:
            ticker = self.market_data_fetcher.fetch_ticker(symbol)
            return ticker.get('last')
        except Exception as e:
            self.logger.error(f"Failed to fetch price for {symbol}: {e}")
            return None
    
    def update_prices(self, symbols: List[str]):
        """Update current prices for all symbols"""
        for symbol in symbols:
            price = self.fetch_latest_price(symbol)
            if price:
                self.current_prices[symbol] = price
                
                # Update price history
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                
                self.price_history[symbol].append({
                    'timestamp': datetime.now(),
                    'price': price
                })
                
                # Keep last 1000 prices
                if len(self.price_history[symbol]) > 1000:
                    self.price_history[symbol] = self.price_history[symbol][-1000:]
        
        # Update portfolio positions
        self.portfolio.update_positions(self.current_prices)
    
    def generate_signal(self, symbol: str) -> str:
        """
        Generate trading signal for symbol.
        
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        if not self.strategy_func:
            return 'HOLD'
        
        # Get price history for this symbol
        if symbol not in self.price_history or len(self.price_history[symbol]) < 50:
            return 'HOLD'
        
        # Convert to simple format for strategy
        import pandas as pd
        prices = [p['price'] for p in self.price_history[symbol]]
        
        # Create simple DataFrame
        data = pd.DataFrame({
            'close': prices,
            'high': prices,  # Simplified
            'low': prices,
            'volume': [1000000] * len(prices)  # Mock volume
        })
        
        # Generate signal
        try:
            signal = self.strategy_func(data, len(data) - 1)
            return signal
        except Exception as e:
            self.logger.error(f"Strategy error for {symbol}: {e}")
            return 'HOLD'
    
    def execute_signal(self, symbol: str, signal: str):
        """Execute trading signal"""
        if signal == 'HOLD':
            return
        
        current_price = self.current_prices.get(symbol)
        if not current_price:
            self.logger.warning(f"No price data for {symbol}")
            return
        
        # Handle BUY signal
        if signal == 'BUY':
            # Check if already have position
            if self.portfolio.has_position(symbol):
                self.logger.info(f"Already have position in {symbol}, skipping BUY")
                return
            
            # Calculate position size (10% of equity)
            equity = self.portfolio.get_total_equity()
            position_value = equity * 0.1
            quantity = position_value / current_price
            
            # Check risk limits
            can_open, reason = self.risk_manager.check_can_open_position(
                self.portfolio, symbol, quantity, current_price
            )
            
            if not can_open:
                self.logger.warning(f"Cannot open {symbol}: {reason}")
                return
            
            # Open position
            success = self.portfolio.open_position(symbol, quantity, current_price)
            
            if success:
                self.logger.info(f"✅ BUY {symbol}: {quantity:.6f} @ ${current_price:.2f}")
                self.signals_history.append({
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'signal': 'BUY',
                    'price': current_price,
                    'quantity': quantity
                })
        
        # Handle SELL signal
        elif signal == 'SELL':
            # Check if have position
            if not self.portfolio.has_position(symbol):
                self.logger.info(f"No position in {symbol}, skipping SELL")
                return
            
            # Close position
            trade = self.portfolio.close_position(symbol, current_price)
            
            if trade:
                self.logger.info(f"✅ SELL {symbol}: P&L ${trade['pnl']:.2f} ({trade['pnl_pct']*100:.2f}%)")
                self.signals_history.append({
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'signal': 'SELL',
                    'price': current_price,
                    'pnl': trade['pnl']
                })
    
    def check_risk_exits(self):
        """Check all positions for stop-loss/take-profit"""
        positions_to_close = []
        
        for symbol, position in self.portfolio.positions.items():
            current_price = self.current_prices.get(symbol)
            if not current_price:
                continue
            
            # Check stop-loss
            if self.risk_manager.check_stop_loss(position, current_price):
                positions_to_close.append((symbol, 'STOP_LOSS'))
            
            # Check take-profit
            elif self.risk_manager.check_take_profit(position, current_price):
                positions_to_close.append((symbol, 'TAKE_PROFIT'))
        
        # Close positions
        for symbol, reason in positions_to_close:
            current_price = self.current_prices[symbol]
            trade = self.portfolio.close_position(symbol, current_price)
            
            if trade:
                self.logger.info(f"🛑 {reason} {symbol}: P&L ${trade['pnl']:.2f}")
    
    def run_trading_loop(self, symbols: List[str], interval: int = 60):
        """
        Run live trading loop.
        
        Args:
            symbols: List of symbols to trade
            interval: Update interval in seconds
        """
        self.logger.info(f"Starting paper trading for {symbols}")
        self.logger.info(f"Update interval: {interval}s")
        self.is_running = True
        
        iteration = 0
        
        try:
            while self.is_running:
                iteration += 1
                self.logger.info(f"\n--- Iteration {iteration} ---")
                
                # Update prices
                self.update_prices(symbols)
                
                # Check risk exits first
                self.check_risk_exits()
                
                # Generate and execute signals
                for symbol in symbols:
                    signal = self.generate_signal(symbol)
                    
                    if signal != 'HOLD':
                        self.logger.info(f"Signal: {symbol} -> {signal}")
                        self.execute_signal(symbol, signal)
                
                # Log status
                summary = self.portfolio.get_performance_summary()
                self.logger.info(f"Equity: ${summary['current_equity']:.2f} | "
                               f"P&L: ${summary['total_pnl']:.2f} ({summary['total_return']*100:+.2f}%) | "
                               f"Positions: {summary['active_positions']}")
                
                # Wait for next iteration
                time.sleep(interval)
        
        except KeyboardInterrupt:
            self.logger.info("Trading stopped by user")
        except Exception as e:
            self.logger.error(f"Trading error: {e}")
        finally:
            self.is_running = False
            self.print_final_summary()
    
    def stop(self):
        """Stop trading loop"""
        self.is_running = False
    
    def print_final_summary(self):
        """Print final trading summary"""
        print("\n" + "="*70)
        print("PAPER TRADING SESSION SUMMARY")
        print("="*70)
        
        summary = self.portfolio.get_performance_summary()
        
        print(f"\n💰 Performance:")
        print(f"   Initial Capital: ${summary['initial_capital']:,.2f}")
        print(f"   Final Equity: ${summary['current_equity']:,.2f}")
        print(f"   Total Return: {summary['total_return']*100:+.2f}%")
        print(f"   Total P&L: ${summary['total_pnl']:,.2f}")
        
        print(f"\n📊 Trading Stats:")
        print(f"   Total Trades: {summary['total_trades']}")
        print(f"   Win Rate: {summary['win_rate']*100:.1f}%")
        print(f"   Max Drawdown: {summary['max_drawdown']*100:.2f}%")
        
        print(f"\n📈 Current Status:")
        print(f"   Active Positions: {summary['active_positions']}")
        print(f"   Cash: ${summary['cash']:,.2f}")
        
        print("\n" + "="*70)
    
    def get_status(self) -> Dict:
        """Get current trading status"""
        return {
            'is_running': self.is_running,
            'portfolio': self.portfolio.get_performance_summary(),
            'positions': self.portfolio.get_positions_summary(),
            'risk_status': self.risk_manager.get_risk_status(self.portfolio),
            'current_prices': self.current_prices,
            'signals_count': len(self.signals_history)
        }
