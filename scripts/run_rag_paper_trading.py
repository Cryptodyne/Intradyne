# RAG-Enhanced Paper Trading with Sentiment Analysis
"""Paper trading enhanced with RAG-powered news sentiment.

This integrates:
- Real market data from Bitget
- RAG sentiment analysis from news
- Combined momentum + sentiment strategy
- Real-time logging and reporting
"""

import ccxt
import time
import signal
from datetime import datetime
from threading import Event
import pandas as pd
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.rag_engine import RAGEngine


class RAGEnhancedPaperTrader:
    """Paper trading with RAG sentiment analysis."""
    
    def __init__(
        self,
        initial_capital: float = 10000,
        symbols: list = None,
        check_interval: int = 60,
    ):
        """Initialize RAG-enhanced paper trader."""
        self.initial_capital = initial_capital
        self.symbols = symbols or ['BTC/USDT', 'ETH/USDT']
        self.check_interval = check_interval
        
        # Initialize Bitget
        self.exchange = ccxt.bitget({
            'apiKey': 'bg_9c5dcee3c08ae511344269760009c409',
            'secret': '6561347d257a454cbe50167dc7e305b683e74d2b85fb172a2d21fdbc263a9b5b',
            'password': 'Intradyne',
            'enableRateLimit': True,
        })
        
        # Initialize RAG
        print("🤖 Initializing RAG engine...")
        try:
            self.rag = RAGEngine()
            self.rag_enabled = True
            print("✅ RAG engine initialized successfully!")
        except Exception as e:
            print(f"⚠️ RAG initialization failed: {e}")
            print("   Continuing without RAG sentiment analysis")
            self.rag_enabled = False
        
        # Virtual portfolio
        self.cash = initial_capital
        self.holdings = {}
        self.trades = []
        self.price_history = {symbol: [] for symbol in self.symbols}
        
        # Stop event
        self._stop_event = Event()
        
        print(f"✅ RAG-Enhanced Paper Trader initialized")
        print(f"   Capital: ${initial_capital:,.2f}")
        print(f"   Symbols: {', '.join(self.symbols)}")
        print(f"   RAG Sentiment: {'✅ ENABLED' if self.rag_enabled else '❌ DISABLED'}")
    
    def start(self):
        """Start RAG-enhanced paper trading."""
        print("\n🚀 Starting RAG-Enhanced Paper Trading...")
        print("   Press Ctrl+C to stop\n")
        
        signal.signal(signal.SIGINT, self._signal_handler)
        
        iteration = 0
        
        while not self._stop_event.is_set():
            try:
                iteration += 1
                print(f"\n{'='*70}")
                print(f"Iteration #{iteration} - {datetime.now()}")
                print(f"{'='*70}")
                
                # Fetch market data
                self._fetch_market_data()
                
                # Get RAG sentiment
                sentiments = self._get_rag_sentiment() if self.rag_enabled else {}
                
                # Run enhanced strategy
                self._run_enhanced_strategy(sentiments)
                
                # Update portfolio
                self._update_portfolio()
                
                # Log performance
                self._log_performance()
                
                # Export every 10 iterations
                if iteration % 10 == 0:
                    self._export_trades()
                
                print(f"\n⏳ Waiting {self.check_interval}s...")
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)
        
        print("\n🛑 RAG-Enhanced Paper Trading stopped")
        self._final_report()
    
    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C."""
        print("\n\n🛑 Shutdown signal received...")
        self._stop_event.set()
    
    def _fetch_market_data(self):
        """Fetch real market data."""
        print("\n📊 Fetching market data...")
        
        for symbol in self.symbols:
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                price = ticker['last']
                
                self.price_history[symbol].append({
                    'timestamp': datetime.now(),
                    'price': price,
                    'volume': ticker.get('baseVolume', 0),
                })
                
                if len(self.price_history[symbol]) > 100:
                    self.price_history[symbol].pop(0)
                
                print(f"   {symbol}: ${price:,.2f}")
                
            except Exception as e:
                print(f"   ❌ {symbol} error: {e}")
    
    def _get_rag_sentiment(self):
        """Get RAG sentiment analysis for each symbol."""
        print("\n🤖 RAG Sentiment Analysis...")
        
        sentiments = {}
        
        for symbol in self.symbols:
            base_currency = symbol.split('/')[0]
            
            try:
                # Query RAG for sentiment
                query = f"What is the current market sentiment for {base_currency}?"
                response = self.rag.query(query, k=3)
                
                # Simple sentiment extraction (you could make this more sophisticated)
                sentiment_score = self._extract_sentiment_score(response)
                
                sentiments[symbol] = {
                    'score': sentiment_score,
                    'analysis': response[:200]  # First 200 chars
                }
                
                print(f"   {symbol}: Sentiment {sentiment_score:+.2f} (0=neutral, +1=bullish, -1=bearish)")
                
            except Exception as e:
                print(f"   ⚠️ {symbol} sentiment unavailable: {e}")
                sentiments[symbol] = {'score': 0, 'analysis': 'N/A'}
        
        return sentiments
    
    def _extract_sentiment_score(self, text: str) -> float:
        """Extract sentiment score from RAG response."""
        text_lower = text.lower()
        
        # Simple keyword-based sentiment
        bullish_words = ['bullish', 'positive', 'up', 'gain', 'rise', 'surge', 'rally']
        bearish_words = ['bearish', 'negative', 'down', 'loss', 'fall', 'drop', 'crash']
        
        bullish_count = sum(1 for word in bullish_words if word in text_lower)
        bearish_count = sum(1 for word in bearish_words if word in text_lower)
        
        if bullish_count + bearish_count == 0:
            return 0.0  # Neutral
        
        # Normalize to -1 to +1
        score = (bullish_count - bearish_count) / (bullish_count + bearish_count)
        return score
    
    def _run_enhanced_strategy(self, sentiments):
        """Run momentum + sentiment strategy."""
        print("\n🎯 Running ENHANCED Strategy (Momentum + Sentiment)...")
        
        for symbol in self.symbols:
            if len(self.price_history[symbol]) < 5:
                print(f"   {symbol}: Not enough data")
                continue
            
            # Calculate momentum
            prices = [p['price'] for p in self.price_history[symbol][-5:]]
            current_price = prices[-1]
            avg_price = sum(prices[:-1]) / len(prices[:-1])
            momentum = (current_price - avg_price) / avg_price * 100
            
            # Get sentiment
            sentiment_score = sentiments.get(symbol, {}).get('score', 0)
            
            # Calculate combined signal
            # Momentum weight: 70%, Sentiment weight: 30%
            combined_signal = (momentum * 0.7) + (sentiment_score * 0.3)
            
            # Get position
            current_position = self.holdings.get(symbol.split('/')[0], 0)
            
            print(f"   {symbol}:")
            print(f"      Momentum: {momentum:+.2f}%")
            print(f"      Sentiment: {sentiment_score:+.2f}")
            print(f"      Combined Signal: {combined_signal:+.2f}")
            print(f"      Position: {current_position:.6f}")
            
            # Trading logic with COMBINED signal
            if combined_signal > 0.3 and current_position == 0 and self.cash > 100:
                # BUY signal (enhanced by sentiment)
                order_value = min(self.cash * 0.2, 1000)
                amount = order_value / current_price
                self._execute_buy(symbol, amount, current_price, combined_signal)
                
            elif combined_signal < -0.3 and current_position > 0:
                # SELL signal (enhanced by sentiment)
                self._execute_sell(symbol, current_position, current_price, combined_signal)
    
    def _execute_buy(self, symbol, amount, price, signal_strength):
        """Execute simulated buy."""
        fee = amount * price * 0.001
        total_cost = (amount * price) + fee
        
        if total_cost > self.cash:
            return
        
        base_currency = symbol.split('/')[0]
        self.cash -= total_cost
        self.holdings[base_currency] = self.holdings.get(base_currency, 0) + amount
        
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': 'BUY',
            'amount': amount,
            'price': price,
            'value': amount * price,
            'fee': fee,
            'total_cost': total_cost,
            'signal_strength': signal_strength,
        }
        self.trades.append(trade)
        
        print(f"\n   ✅ SIMULATED BUY: {amount:.6f} {base_currency} @ ${price:,.2f}")
        print(f"      Signal Strength: {signal_strength:+.2f}")
        print(f"      Cost: ${total_cost:.2f}")
    
    def _execute_sell(self, symbol, amount, price, signal_strength):
        """Execute simulated sell."""
        fee = amount * price * 0.001
        total_proceeds = (amount * price) - fee
        
        base_currency = symbol.split('/')[0]
        self.cash += total_proceeds
        self.holdings[base_currency] = self.holdings.get(base_currency, 0) - amount
        
        if abs(self.holdings[base_currency]) < 0.000001:
            del self.holdings[base_currency]
        
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': 'SELL',
            'amount': amount,
            'price': price,
            'value': amount * price,
            'fee': fee,
            'total_proceeds': total_proceeds,
            'signal_strength': signal_strength,
        }
        self.trades.append(trade)
        
        print(f"\n   ✅ SIMULATED SELL: {amount:.6f} {base_currency} @ ${price:,.2f}")
        print(f"      Signal Strength: {signal_strength:+.2f}")
        print(f"      Proceeds: ${total_proceeds:.2f}")
    
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
        """Log performance."""
        print(f"\n💰 Portfolio:")
        print(f"   Cash: ${self.cash:,.2f}")
        print(f"   Holdings: ${self.equity - self.cash:,.2f}")
        print(f"   Equity: ${self.equity:,.2f}")
        print(f"   P&L: ${self.pnl:+,.2f} ({self.pnl_pct:+.2f}%)")
        print(f"   Trades: {len(self.trades)}")
    
    def _export_trades(self):
        """Export to CSV."""
        if not self.trades:
            return
        
        try:
            os.makedirs('reports', exist_ok=True)
            df = pd.DataFrame(self.trades)
            df.to_csv('reports/rag_paper_trades.csv', index=False)
            print(f"\n📄 Exported {len(self.trades)} trades")
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def _final_report(self):
        """Final report."""
        print(f"\n{'='*70}")
        print("📊 FINAL REPORT (RAG-Enhanced)")
        print(f"{'='*70}")
        print(f"Initial: ${self.initial_capital:,.2f}")
        print(f"Final: ${self.equity:,.2f}")
        print(f"P&L: ${self.pnl:+,.2f} ({self.pnl_pct:+.2f}%)")
        print(f"Trades: {len(self.trades)}")
        self._export_trades()
        print(f"{'='*70}\n")


def main():
    """Run RAG-enhanced paper trading."""
    print("\n" + "="*70)
    print("🤖 RAG-ENHANCED PAPER TRADING")
    print("="*70)
    print("✅ Real market data from Bitget")
    print("✅ AI-powered sentiment analysis (RAG)")
    print("✅ Combined momentum + sentiment signals")
    print("✅ NO REAL MONEY - Paper trading only")
    print("="*70 + "\n")
    
    trader = RAGEnhancedPaperTrader(
        initial_capital=10000,
        symbols=['BTC/USDT', 'ETH/USDT'],
        check_interval=60,
    )
    
    trader.start()


if __name__ == "__main__":
    main()
