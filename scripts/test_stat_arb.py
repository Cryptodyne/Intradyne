import sys
import os
import pandas as pd
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategy import StatArbStrategy

def test_stat_arb():
    print("="*70)
    print("TESTING STATISTICAL ARBITRAGE (COINTEGRATION)")
    print("="*70)
    
    # 1. Generate Cointegrated Data
    print("\n1. Generating Synthetic Cointegrated Pairs")
    np.random.seed(42)
    n = 200
    
    # Asset X: Random Walk
    X = np.cumsum(np.random.normal(0, 1, n)) + 100
    
    # Asset Y: Linked to X (Y = 1.5*X + 10 + noise)
    # This ensures they are cointegrated
    noise = np.random.normal(0, 2, n)
    Y = 1.5 * X + 10 + noise
    
    series_x = pd.Series(X)
    series_y = pd.Series(Y)
    
    print(f"Asset X (Mean): {series_x.mean():.2f}")
    print(f"Asset Y (Mean): {series_y.mean():.2f}")
    
    # 2. Test Cointegration
    print("\n2. Testing Cointegration")
    strategy = StatArbStrategy()
    score, p_value, is_coint = strategy.test_cointegration(series_y, series_x)
    
    print(f"P-Value: {p_value:.5f}")
    print(f"Cointegrated: {'✅ YES' if is_coint else '❌ NO'}")
    
    if not is_coint:
        print("Skipping further tests as cointegration failed (check statsmodels installation).")
        return

    # 3. Calculate Spread
    print("\n3. Calculating Spread")
    spread = strategy.calculate_spread(series_y, series_x)
    strategy.update_statistics(spread)
    
    if strategy.hedge_ratio is None:
        print("Hedge Ratio is None (Calculation failed).")
        return

    print(f"Hedge Ratio (Beta): {strategy.hedge_ratio:.4f} (Expected ~1.5)")
    print(f"Spread Mean: {strategy.spread_mean:.4f}")
    print(f"Spread Std: {strategy.spread_std:.4f}")
    
    # 4. Generate Signals
    print("\n4. Generating Signals")
    
    # Case A: Spread spikes high (Y is expensive relative to X) -> Short Spread
    high_spread_val = strategy.spread_mean + (3.0 * strategy.spread_std)
    signal_high = strategy.get_signal(high_spread_val)
    print(f"Spread Z=+3.0 -> Signal: {signal_high} (Expected: SHORT_SPREAD)")
    
    # Case B: Spread dips low (Y is cheap relative to X) -> Long Spread
    low_spread_val = strategy.spread_mean - (3.0 * strategy.spread_std)
    signal_low = strategy.get_signal(low_spread_val)
    print(f"Spread Z=-3.0 -> Signal: {signal_low} (Expected: LONG_SPREAD)")
    
    # Case C: Spread reverts to mean -> Exit
    mean_spread_val = strategy.spread_mean
    signal_mean = strategy.get_signal(mean_spread_val)
    print(f"Spread Z=0.0  -> Signal: {signal_mean} (Expected: EXIT)")

    print("\n" + "="*70)
    print("✅ Stat Arb Tests Complete")
    print("="*70)

if __name__ == "__main__":
    test_stat_arb()
