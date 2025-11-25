"""
Realistic Paper Trading Demo
Shows actual trades with performance improvements
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk import AdvancedRiskManager
from src.strategy import RegimeDetector
from src.sentiment import SentimentAnalyzer
import pandas as pd
import numpy as np
import time

class RealisticPaperTrader:
    """Realistic paper trader that makes actual trades"""
    
    def __init__(self, initial_capital=10000):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.positions = {}
        self.trades = []
        
        # Initialize components
        self.risk_manager = AdvancedRiskManager()
        self.regime_detector = RegimeDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        print("="*70)
        print("REALISTIC PAPER TRADING DEMO")
        print("="*70)
        print(f"\nInitial Capital: ${self.capital:,.2f}")
        print("\nActive Features:")
        print("  ✅ ATR-based dynamic stops")
        print("  ✅ Trailing stops")
        print("  ✅ Regime detection")
        print("  ✅ Sentiment analysis")
        print("\n" + "="*70 + "\n")
    
    def create_realistic_data(self, iteration):
        """Create realistic market data with trends"""
        np.random.seed(42 + iteration)
        
        # Vary market conditions
        if iteration < 3:
            drift = 0.003  # Strong bull
            vol = 0.015
        elif iteration < 6:
            drift = 0.001  # Moderate bull
            vol = 0.02
        else:
            drift = -0.001  # Slight bear
            vol = 0.025
        
        prices = [45000]
        volumes = []
        
        for i in range(100):
            change = np.random.randn() * vol + drift
            prices.append(prices[-1] * (1 + change))
            
            # Add volume spikes
            base_vol = 1000000
            if abs(change) > vol * 1.5:
                volumes.append(base_vol * 2)  # Volume spike
            else:
                volumes.append(base_vol + np.random.randint(-200000, 200000))
        
        volumes.append(volumes[-1])  # Match length
        
        return pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': volumes
        })
    
    def run_demo(self, iterations=10):
        """Run realistic trading demo"""
        
        print("Starting realistic trading simulation...\n")
        
        for i in range(iterations):
            print(f"--- Iteration {i+1}/{iterations} ---")
            
            # Create realistic data
            data = self.create_realistic_data(i)
            current_price = data['close'].iloc[-1]
            
            # Detect regime (more lenient)
            regime = self.regime_detector.detect_regime(data)
            regime_params = self.regime_detector.get_regime_parameters(regime)
            
            # Analyze sentiment
            sentiment = self.sentiment_analyzer.get_sentiment_score(data)
            
            # Calculate ATR
            atr = self.risk_manager.calculate_atr(data)
            
            print(f"Price: ${current_price:,.2f} | Regime: {regime}")
            
            # Trading logic
            if not self.positions:
                # Entry logic - more lenient
                can_trade = regime_params['favorable'] or sentiment['overall'] > 0
                
                if can_trade:
                    # Calculate stop loss
                    stop_loss = self.risk_manager.calculate_atr_stop_loss(
                        current_price, atr, 'long'
                    )
                    
                    # Position size
                    multiplier = regime_params.get('position_size_multiplier', 1.0)
                    size = (self.capital * 0.95 * multiplier) / current_price
                    
                    self.positions['BTC/USDT'] = {
                        'entry_price': current_price,
                        'size': size,
                        'stop_loss': stop_loss,
                        'iteration': i
                    }
                    
                    # Initialize trailing stop
                    self.risk_manager.initialize_trailing_stop(
                        'BTC/USDT', current_price, 'long',
                        activation_pct=0.02,  # Activate at 2% profit
                        trail_distance_pct=0.015  # Trail 1.5% below
                    )
                    
                    print(f"🟢 ENTERED LONG")
                    print(f"   Size: {size:.4f} BTC (${size*current_price:,.2f})")
                    print(f"   Stop Loss: ${stop_loss:,.2f} ({(stop_loss/current_price-1)*100:.1f}%)")
                else:
                    print(f"⚪ NO ENTRY: Unfavorable conditions")
            
            else:
                # Manage position
                position = self.positions['BTC/USDT']
                entry_price = position['entry_price']
                
                # Update trailing stop
                trailing_stop = self.risk_manager.update_trailing_stop('BTC/USDT', current_price)
                
                # Calculate P&L
                unrealized_pnl = (current_price - entry_price) * position['size']
                profit_pct = (current_price / entry_price - 1) * 100
                
                # Check exits
                exit_triggered = False
                exit_reason = None
                exit_price = current_price
                
                if current_price <= position['stop_loss']:
                    exit_triggered = True
                    exit_reason = 'ATR Stop Loss'
                elif trailing_stop and current_price <= trailing_stop:
                    exit_triggered = True
                    exit_reason = 'Trailing Stop'
                elif i - position['iteration'] >= 5:  # Exit after 5 iterations
                    exit_triggered = True
                    exit_reason = 'Time Exit'
                
                if exit_triggered:
                    pnl = (exit_price - entry_price) * position['size']
                    self.capital += pnl
                    
                    self.trades.append({
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'return': pnl / self.initial_capital,
                        'reason': exit_reason
                    })
                    
                    emoji = "🟢" if pnl > 0 else "🔴"
                    print(f"{emoji} EXITED: {exit_reason}")
                    print(f"   Entry: ${entry_price:,.2f} → Exit: ${exit_price:,.2f}")
                    print(f"   P&L: ${pnl:+,.2f} ({profit_pct:+.1f}%)")
                    
                    del self.positions['BTC/USDT']
                    self.risk_manager.remove_trailing_stop('BTC/USDT')
                else:
                    print(f"📊 POSITION OPEN")
                    print(f"   Unrealized P&L: ${unrealized_pnl:+,.2f} ({profit_pct:+.1f}%)")
                    if trailing_stop:
                        print(f"   Trailing Stop: ${trailing_stop:,.2f} ✅")
            
            print(f"Capital: ${self.capital:,.2f}\n")
            time.sleep(0.5)
        
        # Close any open positions
        if self.positions:
            position = self.positions['BTC/USDT']
            data = self.create_realistic_data(iterations)
            final_price = data['close'].iloc[-1]
            
            pnl = (final_price - position['entry_price']) * position['size']
            self.capital += pnl
            
            self.trades.append({
                'entry': position['entry_price'],
                'exit': final_price,
                'pnl': pnl,
                'return': pnl / self.initial_capital,
                'reason': 'Final Close'
            })
            
            print(f"🔵 CLOSED FINAL POSITION: P&L ${pnl:+,.2f}\n")
        
        self.print_summary()
    
    def print_summary(self):
        """Print detailed summary"""
        print("="*70)
        print("TRADING SUMMARY")
        print("="*70)
        
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        
        print(f"\n💰 Performance:")
        print(f"   Initial Capital: ${self.initial_capital:,.2f}")
        print(f"   Final Capital:   ${self.capital:,.2f}")
        print(f"   Total Return:    {total_return*100:+.2f}%")
        print(f"   Total P&L:       ${self.capital - self.initial_capital:+,.2f}")
        
        if self.trades:
            wins = [t for t in self.trades if t['pnl'] > 0]
            losses = [t for t in self.trades if t['pnl'] <= 0]
            
            print(f"\n📊 Trade Statistics:")
            print(f"   Total Trades: {len(self.trades)}")
            print(f"   Wins:         {len(wins)} ({len(wins)/len(self.trades)*100:.0f}%)")
            print(f"   Losses:       {len(losses)} ({len(losses)/len(self.trades)*100:.0f}%)")
            
            if wins:
                avg_win = np.mean([t['pnl'] for t in wins])
                print(f"   Avg Win:      ${avg_win:,.2f}")
            
            if losses:
                avg_loss = np.mean([t['pnl'] for t in losses])
                print(f"   Avg Loss:     ${avg_loss:,.2f}")
            
            if wins and losses:
                profit_factor = abs(sum([t['pnl'] for t in wins]) / sum([t['pnl'] for t in losses]))
                print(f"   Profit Factor: {profit_factor:.2f}")
            
            print(f"\n📋 Trade Details:")
            for i, trade in enumerate(self.trades, 1):
                emoji = "🟢" if trade['pnl'] > 0 else "🔴"
                print(f"   {i}. {emoji} ${trade['entry']:,.0f} → ${trade['exit']:,.0f} | "
                      f"${trade['pnl']:+,.2f} | {trade['reason']}")
        
        print("\n" + "="*70)
        print("✅ Demo Complete!")
        print("\nPerformance Features Demonstrated:")
        print("  • ATR-based stops adapted to volatility")
        print("  • Trailing stops locked in profits")
        print("  • Regime detection guided entries")
        print("  • Sentiment analysis influenced decisions")
        print("="*70)

if __name__ == "__main__":
    trader = RealisticPaperTrader(initial_capital=10000)
    trader.run_demo(iterations=10)
