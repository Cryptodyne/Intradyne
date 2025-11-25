"""
Enhanced Paper Trading with Quick Wins
Real-time trading with ATR stops, volume filters, trailing stops, and regime detection
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk import AdvancedRiskManager
from src.strategy import RegimeDetector
from src.trading.paper_trader import PaperTrader
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class EnhancedPaperTrader(PaperTrader):
    """Enhanced paper trader with Quick Wins improvements"""
    
    def __init__(self, initial_capital=10000, exchange_id='bitget'):
        super().__init__(initial_capital, exchange_id)
        
        # Initialize Quick Wins components
        self.risk_manager = AdvancedRiskManager(
            atr_period=14,
            atr_multiplier=2.0,
            volume_threshold=1.5,
            volume_lookback=20
        )
        self.regime_detector = RegimeDetector(lookback=20)
        
        # Enhanced settings
        self.use_atr_stops = True
        self.use_volume_confirmation = True
        self.use_trailing_stops = True
        self.use_regime_detection = True
        
        self.logger.info("Enhanced Paper Trader initialized with Quick Wins")
    
    def should_enter_trade(self, symbol, signal, data):
        """Enhanced entry logic with filters"""
        
        # Regime detection
        if self.use_regime_detection:
            regime = self.regime_detector.detect_regime(data)
            
            if not self.regime_detector.should_trade(regime):
                self.logger.info(f"Skipping {symbol}: Unfavorable regime {regime}")
                return False, 0
            
            # Get position size multiplier
            multiplier = self.regime_detector.get_position_size_multiplier(regime)
        else:
            multiplier = 1.0
        
        # Volume confirmation
        if self.use_volume_confirmation:
            if not self.risk_manager.check_volume_confirmation(data):
                self.logger.info(f"Skipping {symbol}: Volume not confirmed")
                return False, 0
        
        return True, multiplier
    
    def calculate_position_size(self, symbol, price, data, multiplier=1.0):
        """Calculate position size with dynamic adjustments"""
        
        # Base position size (95% of capital)
        base_size = (self.capital * 0.95) / price
        
        # Apply regime multiplier
        size = base_size * multiplier
        
        return size
    
    def calculate_stop_loss(self, symbol, entry_price, data):
        """Calculate ATR-based stop loss"""
        
        if self.use_atr_stops:
            atr = self.risk_manager.calculate_atr(data)
            stop_loss = self.risk_manager.calculate_atr_stop_loss(
                entry_price, atr, 'long'
            )
            self.logger.info(f"ATR-based stop: ${stop_loss:.2f} (ATR: ${atr:.2f})")
        else:
            # Fixed 3% stop
            stop_loss = entry_price * 0.97
        
        return stop_loss
    
    def manage_position(self, symbol, position, current_price, data):
        """Enhanced position management with trailing stops"""
        
        # Update trailing stop
        if self.use_trailing_stops:
            trailing_stop = self.risk_manager.update_trailing_stop(symbol, current_price)
            
            # Check if trailing stop hit
            if trailing_stop:
                stop_hit, reason = self.risk_manager.check_stop_hit(symbol, current_price)
                
                if stop_hit:
                    self.logger.info(f"Trailing stop hit for {symbol} at ${current_price:.2f}")
                    return 'exit', 'trailing_stop'
        
        # Check regular stop loss
        if current_price <= position['stop_loss']:
            return 'exit', 'stop_loss'
        
        # Check signal exit
        # (Add your signal logic here)
        
        return 'hold', None
    
    def run_enhanced_trading(self, symbols=['BTC/USDT'], interval=60, duration_hours=24):
        """
        Run enhanced paper trading.
        
        Args:
            symbols: List of symbols to trade
            interval: Check interval in seconds
            duration_hours: How long to run (hours)
        """
        
        print("="*70)
        print("ENHANCED PAPER TRADING WITH QUICK WINS")
        print("="*70)
        print(f"\nSymbols: {', '.join(symbols)}")
        print(f"Initial Capital: ${self.capital:,.2f}")
        print(f"Check Interval: {interval}s")
        print(f"Duration: {duration_hours}h")
        print("\nQuick Wins Features:")
        print(f"  • ATR-based stops: {'✅' if self.use_atr_stops else '❌'}")
        print(f"  • Volume confirmation: {'✅' if self.use_volume_confirmation else '❌'}")
        print(f"  • Trailing stops: {'✅' if self.use_trailing_stops else '❌'}")
        print(f"  • Regime detection: {'✅' if self.use_regime_detection else '❌'}")
        print("\n" + "="*70)
        print("\nStarting trading... (Press Ctrl+C to stop)")
        print()
        
        start_time = time.time()
        end_time = start_time + (duration_hours * 3600)
        iteration = 0
        
        try:
            while time.time() < end_time:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")
                
                for symbol in symbols:
                    try:
                        # Fetch data
                        data = self.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                        
                        if data is None or len(data) < 30:
                            continue
                        
                        current_price = data['close'].iloc[-1]
                        
                        # Check if in position
                        if symbol in self.positions:
                            position = self.positions[symbol]
                            action, reason = self.manage_position(symbol, position, current_price, data)
                            
                            if action == 'exit':
                                self.close_position(symbol, current_price, reason)
                        else:
                            # Generate signal (simple SMA crossover for demo)
                            sma_20 = data['close'].tail(20).mean()
                            sma_50 = data['close'].tail(50).mean()
                            
                            signal = 1 if sma_20 > sma_50 else 0
                            
                            if signal > 0:
                                # Check entry filters
                                should_enter, multiplier = self.should_enter_trade(symbol, signal, data)
                                
                                if should_enter:
                                    # Calculate position size
                                    size = self.calculate_position_size(symbol, current_price, data, multiplier)
                                    
                                    # Calculate stop loss
                                    stop_loss = self.calculate_stop_loss(symbol, current_price, data)
                                    
                                    # Enter position
                                    self.enter_position(symbol, current_price, size, stop_loss)
                                    
                                    # Initialize trailing stop
                                    if self.use_trailing_stops:
                                        self.risk_manager.initialize_trailing_stop(
                                            symbol, current_price, 'long'
                                        )
                        
                        # Print status
                        regime = self.regime_detector.detect_regime(data) if self.use_regime_detection else 'N/A'
                        print(f"{symbol}: ${current_price:,.2f} | Regime: {regime} | Capital: ${self.capital:,.2f}")
                    
                    except Exception as e:
                        self.logger.error(f"Error processing {symbol}: {e}")
                
                # Print summary
                self.print_summary()
                
                # Wait
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\nTrading stopped by user")
        
        # Final summary
        print("\n" + "="*70)
        print("FINAL RESULTS")
        print("="*70)
        self.print_summary()
        
        return self.get_performance_metrics()

if __name__ == "__main__":
    trader = EnhancedPaperTrader(initial_capital=10000, exchange_id='bitget')
    
    # Run for 24 hours, checking every 60 seconds
    results = trader.run_enhanced_trading(
        symbols=['BTC/USDT', 'ETH/USDT'],
        interval=60,
        duration_hours=24
    )
    
    print("\n✅ Enhanced paper trading complete!")
    print(f"Final Capital: ${results['final_capital']:,.2f}")
    print(f"Total Return: {results['total_return']*100:+.1f}%")
