# Continuous Paper Trading Demo with Real Bitget Data
"""Run paper trading continuously with real market data from Bitget.

This script:
- Connects to Bitget production API for REAL market data
- Runs trading strategies continuously (24/7 capable)
- Simulates order execution (NO REAL MONEY)
- Logs all trades and performance metrics
- Generates real-time reports
- Can be stopped gracefully with Ctrl+C

SAFETY: Zero financial risk - all orders are simulated
"""

import ccxt
import time
import signal
import sys
import logging
from datetime import datetime
from threading import Event
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs/paper_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ContinuousPaperTrader:
    """Continuous paper trading with real market data."""
    
    def __init__(
        self,
        initial_capital: float = 10000,
        symbols: list = None,
        check_interval: int = 60,
    ):
        """Initialize continuous paper trader.
        
        Args:
            initial_capital: Starting virtual capital
            symbols: List of symbols to trade (default: ['BTC/USDT', 'ETH/USDT'])
            check_interval: Seconds between strategy checks
        """
        self.initial_capital = initial_capital
        self.symbols = symbols or ['BTC/USDT', 'ETH/USDT']
        self.check_interval = check_interval
        
        # Initialize Bitget exchange
        self.exchange = ccxt.bitget({
            'apiKey': 'bg_9c5dcee3c08ae511344269760009c409',
            'secret': '6561347d257a454cbe50167dc7e305b683e74d2b85fb172a2d21fdbc263a9b5b',
            'password': 'Intradyne',
            'enableRateLimit': True,
        })
        
        # Virtual portfolio
        self.cash = initial_capital
        self.holdings = {}  # symbol -> amount
        self.trades = []
        self.price_history = {symbol: [] for symbol in self.symbols}
        
        # Stop event for graceful shutdown
        self._stop_event = Event()
        
        logger.info(f"✅ Continuous Paper Trader initialized")
        logger.info(f"   Capital: ${initial_capital:,.2f}")
        logger.info(f"   Symbols: {', '.join(self.symbols)}")
        logger.info(f"   Check interval: {check_interval}s")
    
    def start(self):
        """Start continuous paper trading."""
        logger.info("🚀 Starting continuous paper trading...")
        logger.info("   Press Ctrl+C to stop gracefully")
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        iteration = 0
        
        while not self._stop_event.is_set():
            try:
                iteration += 1
                logger.info(f"\n{'='*70}")
                logger.info(f"Iteration #{iteration} - {datetime.now()}")
                logger.info(f"{'='*70}")
                
                # Fetch market data
                self._fetch_market_data()
                
                # Run strategy
                self._run_strategy()
                
                # Update portfolio valuation
                self._update_portfolio()
                
                # Log performance
                self._log_performance()
                
                # Export to CSV
                if iteration % 10 == 0:  # Every 10 iterations
                    self._export_trades()
                
                # Wait for next iteration
                logger.info(f"\n⏳ Waiting {self.check_interval}s until next check...")
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)  # Brief pause before retry
        
        logger.info("\n🛑 Paper trading stopped")
        self._final_report()
    
    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C for graceful shutdown."""
        logger.warning("\n\n🛑 Shutdown signal received...")
        self._stop_event.set()
    
    def _fetch_market_data(self):
        """Fetch real market data from Bitget."""
        logger.info("\n📊 Fetching market data...")
        
        for symbol in self.symbols:
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                price = ticker['last']
                
                # Store price history
                self.price_history[symbol].append({
                    'timestamp': datetime.now(),
                    'price': price,
                    'volume': ticker.get('baseVolume', 0),
                })
                
                # Keep only last 100 data points
                if len(self.price_history[symbol]) > 100:
                    self.price_history[symbol].pop(0)
                
                logger.info(f"   {symbol}: ${price:,.2f} (Vol: {ticker.get('baseVolume', 0):,.2f})")
                
            except Exception as e:
                logger.error(f"   ❌ Failed to fetch {symbol}: {e}")
    
    def _run_strategy(self):
        """Run simple momentum strategy."""
        logger.info("\n🎯 Running trading strategy...")
        
        for symbol in self.symbols:
            if len(self.price_history[symbol]) < 5:
                logger.info(f"   {symbol}: Not enough data yet")
                continue
            
            # Simple momentum strategy: buy if price increased over last 5 periods
            prices = [p['price'] for p in self.price_history[symbol][-5:]]
            current_price = prices[-1]
            avg_price = sum(prices[:-1]) / len(prices[:-1])
            
            momentum = (current_price - avg_price) / avg_price * 100
            
            # Get current position
            current_position = self.holdings.get(symbol.split('/')[0], 0)
            position_value = current_position * current_price
            
            logger.info(f"   {symbol}: Momentum {momentum:+.2f}% | Position: {current_position:.6f}")
            
            # Trading logic - LOWERED THRESHOLDS FOR FASTER TRADING
            if momentum > 0.3 and current_position == 0 and self.cash > 100:
                # Buy signal (was 1.0%, now 0.3%)
                order_value = min(self.cash * 0.2, 1000)  # 20% of cash or $1000 max
                amount = order_value / current_price
                self._execute_buy(symbol, amount, current_price)
                
            elif momentum < -0.3 and current_position > 0:
                # Sell signal (was -1.0%, now -0.3%)
                self._execute_sell(symbol, current_position, current_price)
    
    def _execute_buy(self, symbol, amount, price):
        """Execute simulated buy order."""
        fee = amount * price * 0.001  # 0.1% fee
        total_cost = (amount * price) + fee
        
        if total_cost > self.cash:
            logger.warning(f"   ⚠️ Insufficient cash for buy order: ${total_cost:.2f}")
            return
        
        # Update portfolio
        base_currency = symbol.split('/')[0]
        self.cash -= total_cost
        self.holdings[base_currency] = self.holdings.get(base_currency, 0) + amount
        
        # Record trade
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': 'BUY',
            'amount': amount,
            'price': price,
            'value': amount * price,
            'fee': fee,
            'total_cost': total_cost,
        }
        self.trades.append(trade)
        
        logger.info(f"   ✅ SIMULATED BUY: {amount:.6f} {base_currency} @ ${price:,.2f} (Cost: ${total_cost:.2f})")
    
    def _execute_sell(self, symbol, amount, price):
        """Execute simulated sell order."""
        fee = amount * price * 0.001  # 0.1% fee
        total_proceeds = (amount * price) - fee
        
        # Update portfolio
        base_currency = symbol.split('/')[0]
        self.cash += total_proceeds
        self.holdings[base_currency] = self.holdings.get(base_currency, 0) - amount
        
        # Remove if near zero
        if abs(self.holdings[base_currency]) < 0.000001:
            del self.holdings[base_currency]
        
        # Record trade
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': 'SELL',
            'amount': amount,
            'price': price,
            'value': amount * price,
            'fee': fee,
            'total_proceeds': total_proceeds,
        }
        self.trades.append(trade)
        
        logger.info(f"   ✅ SIMULATED SELL: {amount:.6f} {base_currency} @ ${price:,.2f} (Proceeds: ${total_proceeds:.2f})")
    
    def _update_portfolio(self):
        """Update portfolio valuation."""
        holdings_value = 0
        
        for symbol in self.symbols:
            base_currency = symbol.split('/')[0]
            amount = self.holdings.get(base_currency, 0)
            
            if amount > 0 and self.price_history[symbol]:
                current_price = self.price_history[symbol][-1]['price']
                holdings_value += amount * current_price
        
        self.equity = self.cash + holdings_value
        self.pnl = self.equity - self.initial_capital
        self.pnl_pct = (self.pnl / self.initial_capital) * 100
    
    def _log_performance(self):
        """Log current performance."""
        logger.info(f"\n💰 Portfolio Summary:")
        logger.info(f"   Cash: ${self.cash:,.2f}")
        logger.info(f"   Holdings Value: ${self.equity - self.cash:,.2f}")
        logger.info(f"   Total Equity: ${self.equity:,.2f}")
        logger.info(f"   P&L: ${self.pnl:+,.2f} ({self.pnl_pct:+.2f}%)")
        logger.info(f"   Total Trades: {len(self.trades)}")
    
    def _export_trades(self):
        """Export trades to CSV."""
        if not self.trades:
            return
        
        try:
            df = pd.DataFrame(self.trades)
            df.to_csv('reports/paper_trades.csv', index=False)
            logger.info(f"\n📄 Exported {len(self.trades)} trades to reports/paper_trades.csv")
        except Exception as e:
            logger.error(f"❌ Failed to export trades: {e}")
    
    def _final_report(self):
        """Generate final performance report."""
        logger.info(f"\n{'='*70}")
        logger.info("📊 FINAL PERFORMANCE REPORT")
        logger.info(f"{'='*70}")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Final Equity: ${self.equity:,.2f}")
        logger.info(f"Total P&L: ${self.pnl:+,.2f} ({self.pnl_pct:+.2f}%)")
        logger.info(f"Total Trades: {len(self.trades)}")
        
        if self.trades:
            buy_trades = [t for t in self.trades if t['side'] == 'BUY']
            sell_trades = [t for t in self.trades if t['side'] == 'SELL']
            logger.info(f"Buy Orders: {len(buy_trades)}")
            logger.info(f"Sell Orders: {len(sell_trades)}")
        
        # Export final trades
        self._export_trades()
        
        logger.info(f"{'='*70}\n")


def main():
    """Run continuous paper trading demo."""
    print("\n" + "="*70)
    print("CONTINUOUS PAPER TRADING DEMO")
    print("="*70)
    print("✅ Using Bitget production API for REAL market data")
    print("✅ Simulating all orders (NO REAL MONEY)")
    print("✅ Running simple momentum strategy")
    print("✅ Press Ctrl+C to stop gracefully")
    print("="*70)
    
    # Create and start trader
    trader = ContinuousPaperTrader(
        initial_capital=10000,
        symbols=['BTC/USDT', 'ETH/USDT'],
        check_interval=60,  # Check every 60 seconds
    )
    
    trader.start()


if __name__ == "__main__":
    main()
