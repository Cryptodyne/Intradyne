import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategy.backtester import Backtester
from src.strategy.optimizer import StrategyOptimizer
import pandas as pd

def sma_strategy_with_params(data: pd.DataFrame, index: int, 
                             fast_period: int = 9, slow_period: int = 20) -> str:
    """
    Parameterized SMA crossover strategy.
    
    Args:
        data: OHLCV DataFrame
        index: Current candle index
        fast_period: Fast SMA period
        slow_period: Slow SMA period
        
    Returns:
        'BUY', 'SELL', or 'HOLD'
    """
    if index < slow_period:
        return 'HOLD'
    
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

def test_optimizer():
    print("="*60)
    print("Testing Strategy Optimizer")
    print("="*60)
    
    # Initialize backtester
    print("\n1. Initializing backtester...")
    backtester = Backtester(initial_capital=10000, commission=0.001, slippage=0.001)
    print("   ✓ Backtester initialized")
    
    # Load data
    print("\n2. Loading historical data...")
    data = backtester.load_data('BTC/USDT', '2024-01-01', '2024-06-01', source='mock')
    print(f"   ✓ Loaded {len(data)} candles")
    
    # Initialize optimizer
    print("\n3. Initializing optimizer...")
    optimizer = StrategyOptimizer(backtester)
    print("   ✓ Optimizer initialized")
    
    # Test 1: Grid Search
    print("\n4. Running grid search optimization...")
    param_grid = {
        'fast_period': [5, 9, 12],
        'slow_period': [20, 26, 50]
    }
    
    print(f"   Parameter grid: {param_grid}")
    print(f"   Total combinations: {len(param_grid['fast_period']) * len(param_grid['slow_period'])}")
    
    try:
        grid_results = optimizer.grid_search(
            param_grid=param_grid,
            data=data,
            strategy_func=sma_strategy_with_params,
            metric='sharpe_ratio',
            position_size=0.1
        )
        
        print(f"\n   ✓ Grid search complete")
        print(f"   Best parameters: {grid_results['best_params']}")
        print(f"   Best Sharpe ratio: {grid_results['best_score']:.4f}")
        print(f"   Best total return: {grid_results['best_results']['metrics']['total_return']*100:.2f}%")
    except Exception as e:
        print(f"   ✗ Grid search failed: {e}")
    
    # Test 2: Random Search
    print("\n5. Running random search optimization...")
    param_ranges = {
        'fast_period': (5, 15),
        'slow_period': (20, 50)
    }
    
    print(f"   Parameter ranges: {param_ranges}")
    print(f"   Iterations: 20")
    
    try:
        random_results = optimizer.random_search(
            param_ranges=param_ranges,
            data=data,
            strategy_func=sma_strategy_with_params,
            n_iterations=20,
            metric='sharpe_ratio',
            position_size=0.1
        )
        
        print(f"\n   ✓ Random search complete")
        print(f"   Best parameters: {random_results['best_params']}")
        print(f"   Best Sharpe ratio: {random_results['best_score']:.4f}")
    except Exception as e:
        print(f"   ✗ Random search failed: {e}")
    
    # Test 3: Walk-Forward Optimization
    print("\n6. Running walk-forward optimization...")
    best_params = grid_results['best_params']
    
    print(f"   Using parameters: {best_params}")
    print(f"   Train window: 30 days, Test window: 7 days, Step: 7 days")
    
    try:
        wf_results = optimizer.walk_forward(
            data=data,
            strategy_func=sma_strategy_with_params,
            params=best_params,
            train_window=30,
            test_window=7,
            step_size=7,
            position_size=0.1
        )
        
        print(f"\n   ✓ Walk-forward complete")
        print(f"   Windows tested: {wf_results['n_windows']}")
        print(f"   In-sample Sharpe: {wf_results['in_sample_sharpe']:.4f}")
        print(f"   Out-of-sample Sharpe: {wf_results['out_sample_sharpe']:.4f}")
        print(f"   Overfitting ratio: {wf_results['overfitting_ratio']:.2f}")
        
        # Detect overfitting
        overfitting = optimizer.detect_overfitting(
            wf_results['in_sample_sharpe'],
            wf_results['out_sample_sharpe']
        )
        
        print(f"\n   Overfitting analysis:")
        print(f"     Status: {overfitting['status']}")
        print(f"     Degradation: {overfitting['degradation_pct']:.1f}%")
    except Exception as e:
        print(f"   ✗ Walk-forward failed: {e}")
    
    # Show top results
    print("\n7. Top 5 parameter combinations:")
    top_results = optimizer.get_top_results(n=5)
    for i, result in enumerate(top_results):
        print(f"   {i+1}. Params: {result['params']}")
        print(f"      Sharpe: {result['score']:.4f}, Return: {result['metrics']['total_return']*100:.2f}%")
    
    # Export results
    print("\n8. Exporting results...")
    try:
        optimizer.export_results('data/logs/optimization_results.json')
        print("   ✓ Results exported to data/logs/optimization_results.json")
    except Exception as e:
        print(f"   ⚠ Export failed: {e}")
    
    print("\n" + "="*60)
    print("Strategy Optimizer Test Complete!")
    print("="*60)

if __name__ == "__main__":
    test_optimizer()
