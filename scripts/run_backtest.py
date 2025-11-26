"""
Run Trading Strategy Backtest
Tests improved trading strategy against sample data.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.trading.backtester import Backtester, generate_sample_data


def main():
    print("=" * 70)
    print("TRADING STRATEGY BACKTEST")
    print("=" * 70)
    
    # Generate sample data
    print("\n📊 Generating 30 days of hourly price data...")
    price_data = generate_sample_data(days=30, symbol='BTC/USDT')
    print(f"   ✅ Generated {len(price_data)} candles")
    
    # Test 1: OLD config (weak thresholds)
    print("\n" + "=" * 70)
    print("TEST 1: OLD CONFIG (Before Improvements)")
    print("=" * 70)
    
    old_config = {
        'buy_threshold': 0.003,  # 0.3% - too sensitive
        'sell_threshold': -0.003,
        'stop_loss_pct': 0.05,  # 5%
        'take_profit_pct': 0.10,  # 10%
        'confidence_threshold': 0.70,  # 70%
        'use_technical_indicators': False,  # No indicators
        'min_hold_time_minutes': 0  # No minimum hold
    }
    
    backtester1 = Backtester(strategy_config=old_config, initial_balance=10000.0)
    results1 = backtester1.run(price_data, symbol='BTC/USDT')
    backtester1.print_summary(results1['metrics'])
    
    # Test 2: NEW config (improved thresholds + technical indicators)
    print("\n\n" + "=" * 70)
    print("TEST 2: NEW CONFIG (After Improvements)")
    print("=" * 70)
    
    new_config = {
        'buy_threshold': 0.006,  # 0.6% - less noise
        'sell_threshold': 0.004,  # 0.4% - more symmetric
        'stop_loss_pct': 0.03,  # 3% - tighter
        'take_profit_pct': 0.08,  # 8% - more realistic
        'confidence_threshold': 0.75,  # 75% - higher bar
        'use_technical_indicators': True,  # Use RSI, MACD, etc.
        'min_hold_time_minutes': 30,  # 30 min minimum
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'min_volume_ratio': 1.2
    }
    
    backtester2 = Backtester(strategy_config=new_config, initial_balance=10000.0)
    results2 = backtester2.run(price_data, symbol='BTC/USDT')
    backtester2.print_summary(results2['metrics'])
    
    # Compare results
    print("\n\n" + "=" * 70)
    print("COMPARISON: OLD vs NEW")
    print("=" * 70)
    
    old_metrics = results1['metrics']
    new_metrics = results2['metrics']
    
    improvements = {
        'Return': new_metrics['total_return_pct'] - old_metrics['total_return_pct'],
        'Win Rate': new_metrics['win_rate'] - old_metrics['win_rate'],
        'Profit Factor': new_metrics['profit_factor'] - old_metrics['profit_factor'],
        'Max Drawdown': old_metrics['max_drawdown'] - new_metrics['max_drawdown']  # Inverted (lower is better)
    }
    
    print(f"\n{'Metric':<20} {'Old':<15} {'New':<15} {'Change':<15}")
    print("-" * 70)
    print(f"{'Total Return':<20} {old_metrics['total_return_pct']:>13.2f}% {new_metrics['total_return_pct']:>13.2f}% {improvements['Return']:>13.2f}%")
    print(f"{'Win Rate':<20} {old_metrics['win_rate']:>13.1f}% {new_metrics['win_rate']:>13.1f}% {improvements['Win Rate']:>13.1f}%")
    print(f"{'Profit Factor':<20} {old_metrics['profit_factor']:>14.2f} {new_metrics['profit_factor']:>14.2f} {improvements['Profit Factor']:>14.2f}")
    print(f"{'Max Drawdown':<20} {old_metrics['max_drawdown']:>13.2f}% {new_metrics['max_drawdown']:>13.2f}% {improvements['Max Drawdown']:>13.2f}%")
    print(f"{'Total Trades':<20} {old_metrics['total_trades']:>14} {new_metrics['total_trades']:>14} {new_metrics['total_trades'] - old_metrics['total_trades']:>14}")
    
    print("\n" + "=" * 70)
    
    # Verdict
    if new_metrics['total_return_pct'] > old_metrics['total_return_pct']:
        print("✅ NEW CONFIG IS BETTER!")
        print(f"   Improvement: +{improvements['Return']:.2f}% return")
    else:
        print("❌ OLD CONFIG PERFORMED BETTER")
        print(f"   Note: Results may vary with different data/market conditions")
    
    print("=" * 70)
    
    print("\n📝 Note: This is a backtest on synthetic data.")
    print("   Real market performance may differ.")
    print("   Use paper trading to validate before going live.\n")


if __name__ == "__main__":
    main()
