"""
Backtesting Framework for Trading Strategies
Simulates trading with historical data to evaluate strategy performance.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from src.trading.ai_decision_engine import SignalGenerator
from src.trading.technical_indicators import TechnicalAnalyzer


class Backtester:
    """
    Backtest trading strategies on historical data.
    """
    
    def __init__(self, strategy_config: Optional[Dict] = None, initial_balance: float = 10000.0):
        """
        Initialize backtester.
        
        Args:
            strategy_config: Trading strategy configuration
            initial_balance: Starting balance in USD
        """
        self.strategy = SignalGenerator(strategy_config)
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
    def run(self, price_data: pd.DataFrame, symbol: str = 'BTC/USDT') -> Dict:
        """
        Run backtest on historical price data.
        
        Args:
            price_data: DataFrame with columns: timestamp, open, high, low, close, volume
            symbol: Trading symbol
        
        Returns:
            Performance metrics and trade history
        """
        print(f"🔄 Running backtest on {len(price_data)} candles...")
        
        self.balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
        # Ensure we have enough data for technical indicators
        if len(price_data) < 50:
            return {
                'error': 'Insufficient data for backtesting (need at least 50 candles)',
                'trades': [],
                'metrics': {}
            }
        
        # Run through each candle
        for i in range(50, len(price_data)):
            # Get historical data up to this point
            historical = price_data.iloc[:i+1].copy()
            current_row = price_data.iloc[i]
            
            current_price = current_row['close']
            timestamp = current_row['timestamp'] if 'timestamp' in current_row else datetime.now()
            
            # Calculate momentum (simple price change)
            if i > 0:
                prev_price = price_data.iloc[i-1]['close']
                momentum = (current_price - prev_price) / prev_price
            else:
                momentum = 0.0
            
            # Get current position if any
            position = self.positions.get(symbol)
            
            # Generate signal with price data for technical analysis
            signal = self.strategy.get_recommendation(
                symbol=symbol,
                current_price=current_price,
                momentum=momentum,
                position=position,
                price_data=historical
            )
            
            # Execute trade based on signal
            if signal['action'] == 'BUY' and not position:
                # Open position
                position_size = min(signal['suggestions']['position_size'], self.balance * 0.95)
                if position_size >= 100:  # Minimum position size
                    quantity = position_size / current_price
                    
                    self.positions[symbol] = {
                        'entry_price': current_price,
                        'entry_time': timestamp,
                        'quantity': quantity,
                        'position_size': position_size,
                        'stop_loss': signal['suggestions']['stop_loss'],
                        'take_profit': signal['suggestions']['take_profit'],
                        'side': 'BUY'
                    }
                    
                    self.balance -= position_size
                    
                    self.trades.append({
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'action': 'BUY',
                        'price': current_price,
                        'quantity': quantity,
                        'value': position_size,
                        'reasoning': signal['reasoning'],
                        'confidence': signal['confidence']
                    })
            
            elif signal['action'] == 'SELL' and position:
                # Close position
                exit_value = position['quantity'] * current_price
                pnl = exit_value - position['position_size']
                pnl_pct = (pnl / position['position_size']) * 100
                
                self.balance += exit_value
                
                self.trades.append({
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': current_price,
                    'quantity': position['quantity'],
                    'value': exit_value,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reasoning': signal['reasoning'],
                    'confidence': signal['confidence'],
                    'hold_time': (timestamp - position['entry_time']).total_seconds() / 60  # minutes
                })
                
                del self.positions[symbol]
            
            # Calculate current equity (balance + open positions value)
            equity = self.balance
            if position:
                equity += position['quantity'] * current_price
            
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': equity,
                'balance': self.balance,
                'positions_value': equity - self.balance
            })
        
        # Close any remaining positions at final price
        if self.positions:
            final_price = price_data.iloc[-1]['close']
            final_timestamp = price_data.iloc[-1]['timestamp'] if 'timestamp' in price_data.columns else datetime.now()
            
            for sym, pos in list(self.positions.items()):
                exit_value = pos['quantity'] * final_price
                pnl = exit_value - pos['position_size']
                pnl_pct = (pnl / pos['position_size']) * 100
                
                self.balance += exit_value
                
                self.trades.append({
                    'timestamp': final_timestamp,
                    'symbol': sym,
                    'action': 'SELL',
                    'price': final_price,
                    'quantity': pos['quantity'],
                    'value': exit_value,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reasoning': 'Backtest end',
                    'confidence': 1.0,
                    'hold_time': (final_timestamp - pos['entry_time']).total_seconds() / 60
                })
                
                del self.positions[sym]
        
        # Calculate performance metrics
        metrics = self._calculate_metrics()
        
        return {
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'metrics': metrics
        }
    
    def _calculate_metrics(self) -> Dict:
        """Calculate performance metrics from trades."""
        if not self.trades:
            return {
                'total_return': 0.0,
                'total_return_pct': 0.0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0
            }
        
        # Calculate total return
        final_balance = self.balance
        total_return = final_balance - self.initial_balance
        total_return_pct = (total_return / self.initial_balance) * 100
        
        # Analyze trades
        sell_trades = [t for t in self.trades if t['action'] == 'SELL' and 'pnl' in t]
        
        if not sell_trades:
            return {
                'total_return': total_return,
                'total_return_pct': total_return_pct,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'total_trades': len(self.trades),
                'winning_trades': 0,
                'losing_trades': 0
            }
        
        winning_trades = [t for t in sell_trades if t['pnl'] > 0]
        losing_trades = [t for t in sell_trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / len(sell_trades) if sell_trades else 0.0
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0.0
        avg_loss = abs(np.mean([t['pnl'] for t in losing_trades])) if losing_trades else 0.0
        
        total_wins = sum([t['pnl'] for t in winning_trades])
        total_losses = abs(sum([t['pnl'] for t in losing_trades]))
        
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Average hold time
        avg_hold_time = np.mean([t.get('hold_time', 0) for t in sell_trades])
        
        return {
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'win_rate': win_rate * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'total_trades': len(sell_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_hold_time_minutes': avg_hold_time,
            'sharpe_ratio': self._calculate_sharpe_ratio()
        }
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve."""
        if not self.equity_curve:
            return 0.0
        
        equity_values = [e['equity'] for e in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0.0
        
        for value in equity_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd * 100  # Return as percentage
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio (annualized)."""
        if len(self.equity_curve) < 2:
            return 0.0
        
        equity_values = [e['equity'] for e in self.equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        # Annualize (assuming daily data)
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        
        return sharpe
    
    def print_summary(self, metrics: Dict):
        """Print backtest summary."""
        print("\n" + "="*70)
        print("BACKTEST RESULTS")
        print("="*70)
        print(f"\n💰 RETURNS")
        print(f"   Starting Balance:  ${self.initial_balance:>12,.2f}")
        print(f"   Final Balance:     ${self.balance:>12,.2f}")
        print(f"   Total Return:      ${metrics['total_return']:>12,.2f} ({metrics['total_return_pct']:+.2f}%)")
        
        print(f"\n📊 TRADING STATISTICS")
        print(f"   Total Trades:      {metrics['total_trades']:>12}")
        print(f"   Winning Trades:    {metrics['winning_trades']:>12}")
        print(f"   Losing Trades:     {metrics['losing_trades']:>12}")
        print(f"   Win Rate:          {metrics['win_rate']:>11.1f}%")
        
        print(f"\n💵 PROFIT ANALYSIS")
        print(f"   Average Win:       ${metrics['avg_win']:>12,.2f}")
        print(f"   Average Loss:      ${metrics['avg_loss']:>12,.2f}")
        print(f"   Profit Factor:     {metrics['profit_factor']:>12.2f}")
        
        print(f"\n📈 RISK METRICS")
        print(f"   Max Drawdown:      {metrics['max_drawdown']:>11.2f}%")
        print(f"   Sharpe Ratio:      {metrics['sharpe_ratio']:>12.2f}")
        print(f"   Avg Hold Time:     {metrics['avg_hold_time_minutes']:>11.1f} min")
        
        print("\n" + "="*70)


def generate_sample_data(days: int = 30, symbol: str = 'BTC/USDT') -> pd.DataFrame:
    """
    Generate sample price data for testing.
    
    Args:
        days: Number of days of data
        symbol: Trading symbol
    
    Returns:
        DataFrame with OHLCV data
    """
    np.random.seed(42)
    
    # Generate timestamps
    start_date = datetime.now() - timedelta(days=days)
    timestamps = [start_date + timedelta(hours=i) for i in range(days * 24)]
    
    # Generate price data (random walk with trend)
    base_price = 50000 if 'BTC' in symbol else 3000
    prices = [base_price]
    
    for _ in range(len(timestamps) - 1):
        change_pct = np.random.normal(0.001, 0.02)  # 0.1% mean, 2% std
        new_price = prices[-1] * (1 + change_pct)
        prices.append(new_price)
    
    # Create OHLCV data
    data = []
    for i, (ts, close) in enumerate(zip(timestamps, prices)):
        volatility = close * 0.01  # 1% volatility
        high = close + abs(np.random.normal(0, volatility))
        low = close - abs(np.random.normal(0, volatility))
        open_price = prices[i-1] if i > 0 else close
        volume = np.random.uniform(1000000, 10000000)
        
        data.append({
            'timestamp': ts,
            'open': open_price,
            'high': max(high, close, open_price),
            'low': min(low, close, open_price),
            'close': close,
            'volume': volume
        })
    
    return pd.DataFrame(data)


# Example usage
if __name__ == "__main__":
    print("🧪 Testing Backtesting Framework...")
    
    # Generate sample data
    price_data = generate_sample_data(days=30)
    print(f"Generated {len(price_data)} hours of price data")
    
    # Run backtest with default config
    print("\n📊 Running backtest with DEFAULT config...")
    backtester = Backtester()
    results = backtester.run(price_data)
    backtester.print_summary(results['metrics'])
    
    # Run backtest with improved config
    print("\n\n📊 Running backtest with IMPROVED config...")
    improved_config = {
        'buy_threshold': 0.006,
        'sell_threshold': 0.004,
        'stop_loss_pct': 0.03,
        'take_profit_pct': 0.08,
        'confidence_threshold': 0.75,
        'use_technical_indicators': True
    }
    
    backtester2 = Backtester(strategy_config=improved_config)
    results2 = backtester2.run(price_data)
    backtester2.print_summary(results2['metrics'])
    
    print("\n✅ Backtesting framework test complete!")
