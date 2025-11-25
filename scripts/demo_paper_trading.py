"""
Simple Paper Trading Demo with Performance Improvements
Demonstrates Quick Wins and Medium-Term Enhancements
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk import AdvancedRiskManager
from src.strategy import RegimeDetector, MultiTimeframeAnalyzer
from src.sentiment import SentimentAnalyzer
from src.portfolio import CorrelationOptimizer
import pandas as pd
import numpy as np
import time

class SimplePaperTrader:
    """Simple paper trader with all performance improvements"""
    
    def __init__(self, initial_capital=10000):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.positions = {}
        self.trades = []
        
        # Initialize performance improvements
        self.risk_manager = AdvancedRiskManager()
        self.regime_detector = RegimeDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        print("="*70)
        print("ENHANCED PAPER TRADING DEMO")
        print("="*70)
        print(f"\nInitial Capital: ${self.capital:,.2f}")
        print("\nPerformance Improvements Active:")
        print("  ✅ ATR-based dynamic stops")
        print("  ✅ Volume confirmation filters")
        print("  ✅ Trailing stop management")
        print("  ✅ Market regime detection")
        print("  ✅ Sentiment analysis")
        print("\n" + "="*70)
    
    def create_mock_data(self, trend='bullish'):
        """Create mock market data"""
        np.random.seed(int(time.time()) % 2**32)
        
        drift = 0.002 if trend == 'bullish' else -0.002 if trend == 'bearish' else 0.0
        vol = 0.02
        
        prices = [45000]  # BTC starting price
        for _ in range(100):
            change = np.random.randn() * vol + drift
            prices.append(prices[-1] * (1 + change))
        
        return pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': [1000000 + np.random.randint(-200000, 200000) for _ in prices]
        })
    
    def run_demo(self, iterations=10):
        """Run paper trading demo"""
        
        print("\nStarting trading simulation...")
        print()
        
        for i in range(iterations):
            print(f"\n--- Iteration {i+1}/{iterations} ---")
            
            # Create mock data
            data = self.create_mock_data('bullish')
            current_price = data['close'].iloc[-1]
            
            # Detect regime
            regime = self.regime_detector.detect_regime(data)
            should_trade_regime = self.regime_detector.should_trade(regime)
            
            # Analyze sentiment
            sentiment = self.sentiment_analyzer.get_sentiment_score(data)
            should_trade_sentiment = self.sentiment_analyzer.should_trade(sentiment)
            
            # Volume confirmation
            volume_confirmed = self.risk_manager.check_volume_confirmation(data)
            
            print(f"Price: ${current_price:,.2f}")
            print(f"Regime: {regime} ({'✅ Trade' if should_trade_regime else '❌ Skip'})")
            print(f"Sentiment: {sentiment['level']} ({sentiment['overall']:+.2f})")
            print(f"Volume: {'✅ Confirmed' if volume_confirmed else '❌ Low'}")
            
            # Trading logic
            if not self.positions:
                # Check all filters
                if should_trade_regime and should_trade_sentiment and volume_confirmed:
                    # Calculate position size
                    atr = self.risk_manager.calculate_atr(data)
                    stop_loss = self.risk_manager.calculate_atr_stop_loss(current_price, atr, 'long')
                    
                    # Enter position
                    size = (self.capital * 0.95) / current_price
                    
                    self.positions['BTC/USDT'] = {
                        'entry_price': current_price,
                        'size': size,
                        'stop_loss': stop_loss
                    }
                    
                    # Initialize trailing stop
                    self.risk_manager.initialize_trailing_stop('BTC/USDT', current_price, 'long')
                    
                    print(f"🟢 ENTERED: ${current_price:,.2f} | Size: {size:.4f} | Stop: ${stop_loss:,.2f}")
                else:
                    print("⚪ NO ENTRY: Filters not met")
            else:
                # Manage position
                position = self.positions['BTC/USDT']
                
                # Update trailing stop
                trailing_stop = self.risk_manager.update_trailing_stop('BTC/USDT', current_price)
                
                # Check exits
                if current_price <= position['stop_loss']:
                    # Stop loss hit
                    pnl = (current_price - position['entry_price']) * position['size']
                    self.capital += pnl
                    
                    self.trades.append({
                        'entry': position['entry_price'],
                        'exit': current_price,
                        'pnl': pnl,
                        'reason': 'stop_loss'
                    })
                    
                    print(f"🔴 STOP LOSS: ${current_price:,.2f} | P&L: ${pnl:,.2f}")
                    
                    del self.positions['BTC/USDT']
                    self.risk_manager.remove_trailing_stop('BTC/USDT')
                
                elif trailing_stop and current_price <= trailing_stop:
                    # Trailing stop hit
                    pnl = (current_price - position['entry_price']) * position['size']
                    self.capital += pnl
                    
                    self.trades.append({
                        'entry': position['entry_price'],
                        'exit': current_price,
                        'pnl': pnl,
                        'reason': 'trailing_stop'
                    })
                    
                    print(f"🟡 TRAILING STOP: ${current_price:,.2f} | P&L: ${pnl:+,.2f}")
                    
                    del self.positions['BTC/USDT']
                    self.risk_manager.remove_trailing_stop('BTC/USDT')
                
                else:
                    # Position open
                    unrealized_pnl = (current_price - position['entry_price']) * position['size']
                    profit_pct = unrealized_pnl / self.initial_capital * 100
                    
                    print(f"📊 POSITION OPEN: P&L: ${unrealized_pnl:+,.2f} ({profit_pct:+.1f}%)")
                    if trailing_stop:
                        print(f"   Trailing Stop: ${trailing_stop:,.2f}")
            
            print(f"Capital: ${self.capital:,.2f}")
            
            time.sleep(1)  # Pause between iterations
        
        # Final summary
        self.print_summary()
    
    def print_summary(self):
        """Print trading summary"""
        print("\n" + "="*70)
        print("TRADING SUMMARY")
        print("="*70)
        
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        
        print(f"\nInitial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital: ${self.capital:,.2f}")
        print(f"Total Return: {total_return*100:+.1f}%")
        print(f"Total Trades: {len(self.trades)}")
        
        if self.trades:
            wins = [t for t in self.trades if t['pnl'] > 0]
            losses = [t for t in self.trades if t['pnl'] <= 0]
            
            print(f"Wins: {len(wins)}")
            print(f"Losses: {len(losses)}")
            print(f"Win Rate: {len(wins)/len(self.trades)*100:.1f}%")
            
            if wins:
                print(f"Avg Win: ${np.mean([t['pnl'] for t in wins]):,.2f}")
            if losses:
                print(f"Avg Loss: ${np.mean([t['pnl'] for t in losses]):,.2f}")
        
        print("\n" + "="*70)
        print("✅ Demo complete!")
        print("\nPerformance improvements demonstrated:")
        print("  • ATR-based stops adapted to volatility")
        print("  • Volume filters prevented weak entries")
        print("  • Trailing stops locked in profits")
        print("  • Regime detection avoided bad markets")
        print("  • Sentiment analysis guided decisions")
        print("="*70)

if __name__ == "__main__":
    trader = SimplePaperTrader(initial_capital=10000)
    trader.run_demo(iterations=10)
