import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategy.backtester import Backtester
from src.engines.core_engines import TrendEngine, VolatilityEngine, RiskEngine
import pandas as pd

def simple_sma_strategy(data: pd.DataFrame, index: int) -> str:
    """
    Simple SMA crossover strategy for testing.
    
    Args:
        data: OHLCV DataFrame
        index: Current candle index
        
    Returns:
        'BUY', 'SELL', or 'HOLD'
    """
    if index < 20:  # Need at least 20 candles for SMA
        return 'HOLD'
    
    # Calculate SMAs
    fast_period = 9
    slow_period = 20
    
    closes = data['close'].values[:index+1]
    
    sma_fast = sum(closes[-fast_period:]) / fast_period
    sma_slow = sum(closes[-slow_period:]) / slow_period
    
    # Previous SMAs
    if index > 0:
        prev_closes = data['close'].values[:index]
        prev_sma_fast = sum(prev_closes[-fast_period:]) / fast_period
        prev_sma_slow = sum(prev_closes[-slow_period:]) / slow_period
        
        # Crossover logic
        if sma_fast > sma_slow and prev_sma_fast <= prev_sma_slow:
            return 'BUY'
        elif sma_fast < sma_slow and prev_sma_fast >= prev_sma_slow:
            return 'SELL'
    
    return 'HOLD'

def test_backtester():
    print("="*60)
    print("Testing Backtesting Framework")
    print("="*60)
    
    # Initialize backtester
    print("\n1. Initializing backtester...")
    backtester = Backtester(
        initial_capital=10000,
        commission=0.001,  # 0.1%
        slippage=0.001,    # 0.1%
        position_size_method='fixed'
    )
    print("   ✓ Backtester initialized")
    print(f"     Initial capital: ${backtester.initial_capital:,.2f}")
    print(f"     Commission: {backtester.commission*100}%")
    print(f"     Slippage: {backtester.slippage*100}%")
    
    # Load historical data
    print("\n2. Loading historical data...")
    try:
        data = backtester.load_data(
            symbol='BTC/USDT',
            start_date='2024-01-01',
            end_date='2024-06-01',
            timeframe='5m',
            source='mock'  # Use mock data for testing
        )
        print(f"   ✓ Loaded {len(data)} candles")
        print(f"     Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
        print(f"     Price range: ${data['close'].min():,.2f} - ${data['close'].max():,.2f}")
    except Exception as e:
        print(f"   ✗ Failed to load data: {e}")
        return
    
    # Run backtest
    print("\n3. Running backtest with SMA crossover strategy...")
    try:
        results = backtester.run_backtest(
            strategy_func=simple_sma_strategy,
            data=data,
            position_size=0.1  # 10% of capital per trade
        )
        print("   ✓ Backtest complete")
    except Exception as e:
        print(f"   ✗ Backtest failed: {e}")
        return
    
    # Display metrics
    print("\n4. Performance Metrics:")
    metrics = results['metrics']
    
    print(f"\n   📊 Trading Activity:")
    print(f"     Total trades: {metrics['total_trades']}")
    print(f"     Winning trades: {metrics['winning_trades']}")
    print(f"     Losing trades: {metrics['losing_trades']}")
    print(f"     Win rate: {metrics['win_rate']*100:.1f}%")
    
    print(f"\n   💰 P&L Metrics:")
    print(f"     Total P&L: ${metrics['total_pnl']:,.2f}")
    print(f"     Total return: {metrics['total_return']*100:.2f}%")
    print(f"     Final capital: ${metrics['final_capital']:,.2f}")
    print(f"     Avg win: ${metrics['avg_win']:,.2f}")
    print(f"     Avg loss: ${metrics['avg_loss']:,.2f}")
    print(f"     Profit factor: {metrics['profit_factor']:.2f}")
    
    print(f"\n   📈 Risk Metrics:")
    print(f"     Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"     Max drawdown: {metrics['max_drawdown']*100:.2f}%")
    
    # Show sample trades
    print("\n5. Sample Trades (first 5):")
    for i, trade in enumerate(results['trades'][:5]):
        print(f"   Trade {i+1}:")
        print(f"     Entry: ${trade['entry_price']:,.2f}")
        print(f"     Exit: ${trade['exit_price']:,.2f}")
        print(f"     P&L: ${trade['pnl']:,.2f} ({trade['pnl_pct']*100:.2f}%)")
    
    # Export results
    print("\n6. Exporting results...")
    try:
        backtester.export_results('data/logs/backtest_results.json', format='json')
        print("   ✓ Results exported to data/logs/backtest_results.json")
    except Exception as e:
        print(f"   ⚠ Export failed: {e}")
    
    # Performance assessment
    print("\n7. Performance Assessment:")
    if metrics['sharpe_ratio'] > 1.0:
        print("   ✅ GOOD: Sharpe ratio > 1.0")
    else:
        print("   ⚠️  POOR: Sharpe ratio < 1.0")
    
    if metrics['win_rate'] > 0.5:
        print("   ✅ GOOD: Win rate > 50%")
    else:
        print("   ⚠️  POOR: Win rate < 50%")
    
    if metrics['profit_factor'] > 1.5:
        print("   ✅ GOOD: Profit factor > 1.5")
    else:
        print("   ⚠️  POOR: Profit factor < 1.5")
    
    if abs(metrics['max_drawdown']) < 0.20:
        print("   ✅ GOOD: Max drawdown < 20%")
    else:
        print("   ⚠️  HIGH RISK: Max drawdown > 20%")
    
    print("\n" + "="*60)
    print("Backtesting Framework Test Complete!")
    print("="*60)

if __name__ == "__main__":
    test_backtester()
