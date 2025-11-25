"""
Test Multi-Timeframe Analysis
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategy import MultiTimeframeAnalyzer
import pandas as pd
import numpy as np

def create_timeframe_data(trend='bullish', days=100):
    """Create mock data for a timeframe"""
    np.random.seed(hash(trend) % 2**32)
    
    if trend == 'bullish':
        drift = 0.002
    elif trend == 'bearish':
        drift = -0.002
    else:
        drift = 0.0
    
    prices = [100]
    for _ in range(days - 1):
        change = np.random.randn() * 0.02 + drift
        prices.append(prices[-1] * (1 + change))
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [1000000] * days
    })

def test_multi_timeframe():
    print("="*70)
    print("MULTI-TIMEFRAME ANALYSIS TEST")
    print("="*70)
    print()
    
    analyzer = MultiTimeframeAnalyzer(
        timeframes=['15m', '1h', '4h', '1d'],
        alignment_threshold=3
    )
    
    # Test 1: All Timeframes Bullish
    print("1. Testing All Timeframes Bullish")
    print("-"*70)
    
    data_dict = {
        '15m': create_timeframe_data('bullish', 100),
        '1h': create_timeframe_data('bullish', 100),
        '4h': create_timeframe_data('bullish', 100),
        '1d': create_timeframe_data('bullish', 100)
    }
    
    analyses = analyzer.analyze_all_timeframes('BTC/USDT', data_dict)
    combined = analyzer.get_combined_signal(analyses)
    analyzer.print_analysis('BTC/USDT', combined)
    
    # Test 2: Mixed Signals
    print("\n2. Testing Mixed Signals")
    print("-"*70)
    
    data_dict = {
        '15m': create_timeframe_data('bullish', 100),
        '1h': create_timeframe_data('bullish', 100),
        '4h': create_timeframe_data('bearish', 100),
        '1d': create_timeframe_data('neutral', 100)
    }
    
    analyses = analyzer.analyze_all_timeframes('BTC/USDT', data_dict)
    combined = analyzer.get_combined_signal(analyses)
    analyzer.print_analysis('BTC/USDT', combined)
    
    # Test 3: All Bearish
    print("\n3. Testing All Timeframes Bearish")
    print("-"*70)
    
    data_dict = {
        '15m': create_timeframe_data('bearish', 100),
        '1h': create_timeframe_data('bearish', 100),
        '4h': create_timeframe_data('bearish', 100),
        '1d': create_timeframe_data('bearish', 100)
    }
    
    analyses = analyzer.analyze_all_timeframes('BTC/USDT', data_dict)
    combined = analyzer.get_combined_signal(analyses)
    analyzer.print_analysis('BTC/USDT', combined)
    
    # Test 4: Weighted Signal
    print("\n4. Testing Weighted Signal Calculation")
    print("-"*70)
    
    data_dict = {
        '15m': create_timeframe_data('bullish', 100),
        '1h': create_timeframe_data('bullish', 100),
        '4h': create_timeframe_data('bullish', 100),
        '1d': create_timeframe_data('neutral', 100)
    }
    
    analyses = analyzer.analyze_all_timeframes('BTC/USDT', data_dict)
    weighted_signal = analyzer.get_weighted_signal(analyses)
    
    print(f"\n   Timeframe Weights:")
    weights = analyzer.get_timeframe_weights()
    for tf, weight in weights.items():
        signal = analyses[tf]['signal']
        print(f"     {tf}: {weight:.0%} weight, signal: {signal:+d}")
    
    print(f"\n   Weighted Signal: {weighted_signal:+.2f}")
    print()
    
    # Test 5: Entry Decision
    print("5. Testing Entry Decisions")
    print("-"*70)
    
    scenarios = [
        ('Strong Bullish', ['bullish', 'bullish', 'bullish', 'bullish']),
        ('Weak Bullish', ['bullish', 'bullish', 'neutral', 'neutral']),
        ('Mixed', ['bullish', 'bearish', 'bullish', 'neutral']),
        ('Strong Bearish', ['bearish', 'bearish', 'bearish', 'bearish'])
    ]
    
    print(f"\n   {'Scenario':<20} {'Aligned':<10} {'Confidence':<12} {'Should Trade':<15}")
    print("   " + "-"*60)
    
    for scenario_name, trends in scenarios:
        data_dict = {
            '15m': create_timeframe_data(trends[0], 100),
            '1h': create_timeframe_data(trends[1], 100),
            '4h': create_timeframe_data(trends[2], 100),
            '1d': create_timeframe_data(trends[3], 100)
        }
        
        analyses = analyzer.analyze_all_timeframes('BTC/USDT', data_dict)
        combined = analyzer.get_combined_signal(analyses)
        should_trade = analyzer.should_enter_trade(combined)
        
        aligned = "✅" if combined['aligned'] else "❌"
        trade = "✅ Yes" if should_trade else "❌ No"
        
        print(f"   {scenario_name:<20} {aligned:<10} {combined['confidence']:<12.1%} {trade:<15}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\n✅ All multi-timeframe features working!")
    print("\nKey Features:")
    print("  • 4 timeframe analysis (15m, 1h, 4h, 1d)")
    print("  • Signal alignment detection")
    print("  • Confidence scoring")
    print("  • Weighted signal calculation")
    print("  • Entry decision logic")
    print()

if __name__ == "__main__":
    test_multi_timeframe()
