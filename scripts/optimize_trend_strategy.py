import sys
import os
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.optimization import StrategyOptimizer
from src.engines import TrendEngine # Assuming this exists or we mock it

# Mock TrendEngine if not fully compatible with simple init
class MockTrendEngine:
    def __init__(self, rsi_period=14, macd_fast=12, macd_slow=26):
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow

def run_optimization():
    print("="*70)
    print("STRATEGY PARAMETER OPTIMIZATION DEMO")
    print("="*70)
    
    # 1. Load Data (Mock)
    data = pd.DataFrame({'close': [100, 101, 102]}) # Placeholder
    
    # 2. Define Parameter Grid
    param_grid = {
        'rsi_period': [10, 14, 20],
        'macd_fast': [10, 12, 15],
        'macd_slow': [20, 26, 30]
    }
    
    print("\nParameter Grid:")
    for k, v in param_grid.items():
        print(f"  {k}: {v}")
        
    # 3. Run Optimization
    optimizer = StrategyOptimizer(MockTrendEngine, data)
    results = optimizer.optimize_grid(param_grid, metric='sharpe')
    
    # 4. Display Results
    best_params = results['best_params']
    best_metrics = results['best_metrics']
    
    print("\n" + "="*70)
    print("✅ OPTIMIZATION COMPLETE")
    print("="*70)
    
    print("\n🏆 Best Parameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
        
    print("\n📈 Best Performance:")
    print(f"  Sharpe Ratio: {best_metrics['sharpe']:.4f}")
    print(f"  Total Return: {best_metrics['total_return']*100:.2f}%")
    print(f"  Win Rate:     {best_metrics['win_rate']*100:.2f}%")
    
    # Show top 5 results
    print("\n🔝 Top 5 Configurations:")
    df = results['all_results'].sort_values('sharpe', ascending=False).head(5)
    print(df[['rsi_period', 'macd_fast', 'macd_slow', 'sharpe', 'total_return']].to_string(index=False))

if __name__ == "__main__":
    run_optimization()
