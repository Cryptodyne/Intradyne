"""
AI Decision Engine for Automated Trading
Combines RAG sentiment, technical analysis, and risk management
to generate intelligent trading signals.
"""

import sys
import os
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from src.core.rag_engine import RAGEngine
    RAG_AVAILABLE = True
except:
    RAG_AVAILABLE = False

try:
    from src.trading.technical_indicators import TechnicalAnalyzer
    TECHNICAL_INDICATORS_AVAILABLE = True
except:
    TECHNICAL_INDICATORS_AVAILABLE = False
    print("Warning: Technical indicators not available")


class AIDecisionEngine:
    """
    Core AI engine that generates trading decisions.
    Combines multiple signals: RAG sentiment, momentum, volatility.
    """
    
    def __init__(self, rag_engine=None, config: Optional[Dict] = None):
        """Initialize AI Decision Engine with RAG integration."""
        self.rag_engine = rag_engine
        self.technical_analyzer = TechnicalAnalyzer() if TECHNICAL_INDICATORS_AVAILABLE else None
        
        # Daily loss tracking
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.daily_loss_count = 0
        self.trading_enabled = True
        self.last_reset_date = datetime.now().date()
        
        # Default configuration
        self.config = {
            'buy_threshold': 0.006,  # 0.6% - reduced from 0.3%
            'sell_threshold': 0.004,  # 0.4%
            'confidence_threshold': 0.75,  # Minimum 75% confidence
            'max_position_size': 500.0,  # USD
            'stop_loss_pct': 0.03,  # 3%
            'take_profit_pct': 0.08,  # 8%
            'trailing_stop_pct': 0.025,  # 2.5%
            'min_hold_time_minutes': 30,  # Minimum hold time
            'use_technical_indicators': True,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'min_volume_ratio': 1.2,  # Require 20% above average volume
            'daily_loss_limit': 500.0,  # Maximum daily loss in USD
            'max_daily_losses': 3,  # Maximum losing trades per day
            'use_multi_timeframe': True  # Use higher timeframe filter
        }
        
        # Update with user config
        if config:
            self.config.update(config)
    
    def generate_signal(self, symbol: str, current_price: float, 
                       momentum: float, position: Optional[Dict] = None,
                       price_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Generate trading signal based on multiple factors.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            current_price: Current market price
            momentum: Momentum indicator value (e.g., 0.004 = +0.4%)
            position: Current position dict or None
            price_data: DataFrame with price history for technical analysis
            
        Returns:
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'confidence': float (0-1),
                'reasoning': str,
                'signal_strength': float,
                'suggestions': {
                    'stop_loss': float,
                    'take_profit': float,
                    'position_size': float
                }
            }
        """
        
        # 1. Get technical indicators
        technical_score = 0.0
        technical_signals = {}
        
        if self.config.get('use_technical_indicators', True) and price_data is not None and self.technical_analyzer:
            technical_signals = self.technical_analyzer.analyze(price_data)
            technical_score = technical_signals.get('technical_score', 0.0)
        
        # 2. Get RAG sentiment
        sentiment_score = self._get_sentiment(symbol)
        
        # 3. Calculate combined signal with technical indicators
        momentum_component = momentum * 0.4  # Reduced weight
        sentiment_component = sentiment_score * 0.2
        technical_component = technical_score * 0.4  # New component
        
        combined_signal = momentum_component + sentiment_component + technical_component
        
        # 4. Generate decision
        action = 'HOLD'
        confidence = 0.5
        reasoning_parts = []
        
        # Check if we should block trades based on technical indicators
        trade_blocked = False
        blocking_reason = None
        
        if technical_signals:
            # Don't buy if RSI is overbought
            if technical_signals.get('rsi', 50) > self.config.get('rsi_overbought', 70):
                trade_blocked = True
                blocking_reason = f"RSI overbought ({technical_signals['rsi']:.1f})"
            
            # Don't sell if RSI is oversold  
            elif technical_signals.get('rsi', 50) < self.config.get('rsi_oversold', 30) and combined_signal < 0:
                trade_blocked = True
                blocking_reason = f"RSI oversold ({technical_signals['rsi']:.1f})"
            
            # Check volume confirmation
            volume_ratio = technical_signals.get('volume_ratio', 1.0)
            if volume_ratio < self.config.get('min_volume_ratio', 1.2) and combined_signal > 0:
                trade_blocked = True  
                blocking_reason = f"Low volume ({volume_ratio:.2f}x avg)"
        
        if not trade_blocked and combined_signal >= self.config['buy_threshold']:
            action = 'BUY'
            confidence = min(abs(combined_signal) / 0.02, 1.0)  # Scale to 0-1
            reasoning_parts.append(f"Momentum:{momentum:+.2%}")
            if technical_signals:
                reasoning_parts.append(f"RSI:{technical_signals.get('rsi', 0):.0f}")
                reasoning_parts.append(f"Tech:{technical_score:+.3f}")
            reasoning_parts.append(f"Signal:{combined_signal:+.2%}")
            
        elif not trade_blocked and combined_signal <= -self.config['sell_threshold']:
            action = 'SELL'
            confidence = min(abs(combined_signal) / 0.02, 1.0)
            reasoning_parts.append(f"Momentum:{momentum:+.2%}")
            if technical_signals:
                reasoning_parts.append(f"RSI:{technical_signals.get('rsi', 0):.0f}")
            reasoning_parts.append(f"Signal:{combined_signal:+.2%}")
        else:
            if blocking_reason:
                reasoning_parts.append(f"Blocked: {blocking_reason}")
            else:
                reasoning_parts.append(f"Signal weak ({combined_signal:+.2%})")
        
        # 5. Apply risk management and position exit checks
        if position:
            # Check minimum hold time
            min_hold_time = timedelta(minutes=self.config.get('min_hold_time_minutes', 30))
            entry_time = position.get('entry_time')
            
            if entry_time and datetime.now() - entry_time < min_hold_time:
                # Too soon to exit
                if action == 'SELL' and 'stop_loss' not in str(reasoning_parts):
                    action = 'HOLD'
                    reasoning_parts.append(f"Min hold time not met")
            else:
                # Check exit conditions
                exit_decision = self.should_exit(position, current_price)
                if exit_decision['exit']:
                    action = 'SELL'
                    confidence = 0.95
                    reasoning_parts.append(exit_decision['reason'])
        
        # 6. Calculate dynamic position size based on confidence and volatility
        volatility = 1.0
        if technical_signals:
            volatility = 1.5 if technical_signals.get('volatility') == 'HIGH' else 1.0
        
        position_size = self._calculate_position_size(confidence, volatility)
        
        suggestions = {
            'stop_loss': current_price * (1 - self.config['stop_loss_pct']),
            'take_profit': current_price * (1 + self.config['take_profit_pct']),
            'position_size': position_size
        }
        
        # 6. Validate with RAG (check compliance)
        if self.rag_engine and action in ['BUY', 'SELL']:
            compliance_check = self._check_compliance(symbol, action, suggestions['position_size'])
            if not compliance_check['approved']:
                action = 'HOLD'
                reasoning_parts.append(f"Blocked: {compliance_check['reason']}")
        
        return {
            'action': action,
            'confidence': confidence,
            'reasoning': ' | '.join(reasoning_parts),
            'signal_strength': combined_signal,
            'suggestions': suggestions,
            'timestamp': datetime.now().isoformat()
        }
    
    def should_exit(self, position: Dict, current_price: float) -> Dict:
        """
        Determine if an open position should be exited.
        
        Args:
            position: {'entry_price': float, 'quantity': float, 'symbol': str, 'side': str}
            current_price: Current market price
            
        Returns:
            {'exit': bool, 'reason': str, 'type': str}
        """
        entry_price = position.get('entry_price', current_price)
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Stop Loss
        if pnl_pct <= -self.config['stop_loss_pct']:
            return {
                'exit': True,
                'reason': f"Stop loss triggered: {pnl_pct:+.2%}",
                'type': 'STOP_LOSS'
            }
        
        # Take Profit
        if pnl_pct >= self.config['take_profit_pct']:
            return {
                'exit': True,
                'reason': f"Take profit reached: {pnl_pct:+.2%}",
                'type': 'TAKE_PROFIT'
            }
        
        # Trailing Stop (if price dropped from peak)
        if 'highest_price' in position:
            highest = position['highest_price']
            drop_from_peak = (current_price - highest) / highest
            
            if drop_from_peak <= -self.config['trailing_stop_pct']:
                return {
                    'exit': True,
                    'reason': f"Trailing stop triggered: {drop_from_peak:+.2%} from peak",
                    'type': 'TRAILING_STOP'
                }
        
        return {'exit': False, 'reason': '', 'type': ''}
    
    def _get_sentiment(self, symbol: str) -> float:
        """
        Query RAG engine for market sentiment.
        
        Returns:
            Sentiment score: -1 (bearish) to +1 (bullish)
        """
        if not self.rag_engine:
            return 0.0
        
        try:
            # Query RAG for recent news/sentiment
            query = f"What is the current market sentiment for {symbol}?"
            results = self.rag_engine.hybrid_search(query, n=2)
            
            if not results:
                return 0.0
            
            # Simple sentiment scoring based on keywords
            sentiment = 0.0
            for result in results:
                doc = result.get('document', '').lower()
                
                # Bullish keywords
                if any(word in doc for word in ['bullish', 'positive', 'uptrend', 'buy']):
                    sentiment += 0.002
                
                # Bearish keywords
                if any(word in doc for word in ['bearish', 'negative', 'downtrend', 'sell']):
                    sentiment -= 0.002
            
            return max(min(sentiment, 0.01), -0.01)  # Cap at ±0.01
            
        except Exception as e:
            print(f"RAG sentiment error: {e}")
            return 0.0
    
    def _check_compliance(self, symbol: str, action: str, position_size: float) -> Dict:
        """
        Validate trade against compliance rules (Shariah, risk limits).
        
        Returns:
            {'approved': bool, 'reason': str}
        """
        if not self.rag_engine:
            return {'approved': True, 'reason': 'RAG not available'}
        
        try:
            # Query RAG for compliance rules
            query = f"Is trading {symbol} allowed? Are there any restrictions?"
            results = self.rag_engine.query_rules(query, n=1)
            
            if not results:
                return {'approved': True, 'reason': 'No restrictions found'}
            
            # Simple check for forbidden keywords
            doc = results[0].get('document', '').lower()
            
            if any(word in doc for word in ['forbidden', 'prohibited', 'not allowed']):
                return {'approved': False, 'reason': 'Asset not compliant'}
            
            # Check position size limits
            if position_size > self.config['max_position_size']:
                return {
                    'approved': False, 
                    'reason': f'Position size ${position_size:.2f} exceeds limit ${self.config["max_position_size"]:.2f}'
                }
            
            return {'approved': True, 'reason': 'Compliant'}
            
        except Exception as e:
            print(f"Compliance check error: {e}")
            return {'approved': True, 'reason': f'Check failed: {e}'}
    
    def _calculate_position_size(self, confidence: float, volatility: float = 1.0) -> float:
        """
        Calculate dynamic position size based on confidence and market conditions.
        
        Args:
            confidence: Signal confidence (0-1)
            volatility: Volatility multiplier (1.0 = normal, 1.5 = high)
        
        Returns:
            Position size in USD
        """
        base_size = self.config['max_position_size']
        
        # Reduce size in high volatility
        volatility_adjustment = max(0.5, 1.0 / volatility)
        
        # Scale with confidence (exponential to favor high-confidence trades)
        confidence_adjustment = confidence ** 2
        
        # Calculate final size
        position_size = base_size * confidence_adjustment * volatility_adjustment
        
        # Apply bounds
        min_size = 100.0  # Minimum $100
        return max(min_size, min(position_size, base_size))



class SignalGenerator:
    """
    High-level signal generator that wraps AIDecisionEngine.
    Provides simplified interface for trading scripts.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.engine = AIDecisionEngine(config)
    
    def get_recommendation(self, symbol: str, current_price: float, 
                          momentum: float, position: Optional[Dict] = None) -> Dict:
        """
        Get trading recommendation for a symbol.
        Wrapper around AIDecisionEngine.generate_signal
        """
        return self.engine.generate_signal(symbol, current_price, momentum, position)
    
    def update_config(self, new_config: Dict):
        """Update engine configuration"""
        self.engine.config.update(new_config)
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return self.engine.config.copy()


if __name__ == "__main__":
    # Test the engine
    print("🤖 Testing AI Decision Engine...")
    
    engine = SignalGenerator()
    
    # Test BUY signal
    print("\n--- Test 1: Strong BUY signal ---")
    signal = engine.get_recommendation(
        symbol='BTC/USDT',
        current_price=96500.0,
        momentum=0.004  # +0.4% momentum
    )
    print(f"Action: {signal['action']}")
    print(f"Confidence: {signal['confidence']:.0%}")
    print(f"Reasoning: {signal['reasoning']}")
    print(f"Suggestions: SL=${signal['suggestions']['stop_loss']:.2f}, TP=${signal['suggestions']['take_profit']:.2f}")
    
    # Test SELL signal (stop loss)
    print("\n--- Test 2: Stop Loss trigger ---")
    position = {
        'entry_price': 96500.0,
        'quantity': 0.01,
        'symbol': 'BTC/USDT',
        'side': 'BUY'
    }
    signal = engine.get_recommendation(
        symbol='BTC/USDT',
        current_price=91675.0,  # -5% drop
        momentum=-0.003,
        position=position
    )
    print(f"Action: {signal['action']}")
    print(f"Confidence: {signal['confidence']:.0%}")
    print(f"Reasoning: {signal['reasoning']}")
    
    print("\n✅ AI Decision Engine test complete!")
