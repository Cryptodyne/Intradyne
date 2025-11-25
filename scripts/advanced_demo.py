"""
Advanced Trading Strategy Demo
Demonstrates all advanced features:
1. Multi-Engine Strategy (6 engines combined)
2. Parameter Optimization
3. ML Strategy with Random Forest
4. Advanced Indicators (MACD, RSI, Bollinger Bands)
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategy.backtester import Backtester
from src.strategy.optimizer import StrategyOptimizer
from src.strategy.analytics import PerformanceAnalytics
from src.engines.core_engines import (
    TrendEngine, VolatilityEngine, RiskEngine,
    MomentumEngine, MeanReversionEngine, VolumeEngine
)
import pandas as pd
import numpy as np

# ============================================================================
# STRATEGY 1: Multi-Engine Ensemble
# ============================================================================

def multi_engine_strategy(data: pd.DataFrame, index: int) -> str:
    """
    Combine all 6 engines for robust signals.
    Uses majority voting across engines.
    """
    if index < 50:  # Need enough data
        return 'HOLD'
    
    # Initialize all 6 engines
    engines = [
        TrendEngine(),
        MomentumEngine(),
        MeanReversionEngine(),
        VolatilityEngine(),
        VolumeEngine(),
        RiskEngine()
    ]
    
    # Prepare data for engines
    closes = data['close'].values[:index+1]
    highs = data['high'].values[:index+1] if 'high' in data.columns else closes
    lows = data['low'].values[:index+1] if 'low' in data.columns else closes
    volumes = data['volume'].values[:index+1] if 'volume' in data.columns else np.ones(len(closes))
    
    engine_data = {
        'closes': closes,
        'highs': highs,
        'lows': lows,
        'volumes': volumes
    }
    
    # Collect signals
    signals = []
    confidences = []
    
    for engine in engines:
        try:
            result = engine.analyze(engine_data)
            direction = result.get('direction', 'NEUTRAL')
            confidence = result.get('confidence', 0.5)
            
            # Weight by confidence
            if direction == 'LONG':
                signals.append(confidence)
            elif direction == 'SHORT':
                signals.append(-confidence)
            else:
                signals.append(0)
            
            confidences.append(confidence)
        except Exception as e:
            signals.append(0)
            confidences.append(0)
    
    # Aggregate signals (weighted average)
    avg_signal = np.mean(signals)
    avg_confidence = np.mean(confidences)
    
    # Decision thresholds
    if avg_signal > 0.3 and avg_confidence > 0.6:
        return 'BUY'
    elif avg_signal < -0.3 and avg_confidence > 0.6:
        return 'SELL'
    else:
        return 'HOLD'


# ============================================================================
# STRATEGY 2: Optimized SMA
# ============================================================================

def optimized_sma_strategy(data: pd.DataFrame, index: int,
                          fast_period: int = 9, slow_period: int = 20) -> str:
    """
    Optimized SMA crossover with best parameters.
    """
    if index < slow_period:
        return 'HOLD'
    
    closes = data['close'].values[:index+1]
    
    sma_fast = np.mean(closes[-fast_period:])
    sma_slow = np.mean(closes[-slow_period:])
    
    # Previous SMAs
    if index > 0:
        prev_closes = data['close'].values[:index]
        prev_sma_fast = np.mean(prev_closes[-fast_period:])
        prev_sma_slow = np.mean(prev_closes[-slow_period:])
        
        # Crossover
        if sma_fast > sma_slow and prev_sma_fast <= prev_sma_slow:
            return 'BUY'
        elif sma_fast < sma_slow and prev_sma_fast >= prev_sma_slow:
            return 'SELL'
    
    return 'HOLD'


# ============================================================================
# MAIN DEMO
# ============================================================================

def run_advanced_demo():
    print("="*70)
    print("ADVANCED TRADING STRATEGY DEMO")
    print("="*70)
    print()
    
    # Initialize components
    print("1. Initializing components...")
    backtester = Backtester(initial_capital=10000, commission=0.001, slippage=0.001)
    optimizer = StrategyOptimizer(backtester)
    analytics = PerformanceAnalytics()
    print("   ✓ Components initialized")
    print()
    
    # Load data
    print("2. Loading historical data...")
    data = backtester.load_data('BTC/USDT', '2024-01-01', '2024-06-01', source='mock')
    print(f"   ✓ Loaded {len(data)} candles")
    print()
    
    # ========================================================================
    # TEST 1: Multi-Engine Strategy
    # ========================================================================
    print("="*70)
    print("TEST 1: MULTI-ENGINE STRATEGY (6 Engines Combined)")
    print("="*70)
    print("Engines: Trend, Momentum, MeanReversion, Volatility, Volume, Risk")
    print()
    
    print("Running backtest...")
    multi_results = backtester.run_backtest(multi_engine_strategy, data, position_size=0.1)
    
    print("\n📊 Multi-Engine Results:")
    print(f"   Total Trades: {multi_results['metrics']['total_trades']}")
    print(f"   Win Rate: {multi_results['metrics']['win_rate']*100:.1f}%")
    print(f"   Total Return: {multi_results['metrics']['total_return']*100:.2f}%")
    print(f"   Sharpe Ratio: {multi_results['metrics']['sharpe_ratio']:.4f}")
    print(f"   Max Drawdown: {multi_results['metrics']['max_drawdown']*100:.2f}%")
    print(f"   Profit Factor: {multi_results['metrics']['profit_factor']:.2f}")
    print()
    
    # ========================================================================
    # TEST 2: Parameter Optimization
    # ========================================================================
    print("="*70)
    print("TEST 2: PARAMETER OPTIMIZATION (Grid Search)")
    print("="*70)
    print("Finding best SMA parameters...")
    print()
    
    param_grid = {
        'fast_period': [5, 9, 12],
        'slow_period': [20, 26, 50]
    }
    
    print(f"Testing {len(param_grid['fast_period']) * len(param_grid['slow_period'])} combinations...")
    
    opt_results = optimizer.grid_search(
        param_grid=param_grid,
        data=data,
        strategy_func=optimized_sma_strategy,
        metric='sharpe_ratio',
        position_size=0.1
    )
    
    print("\n📊 Optimization Results:")
    print(f"   Best Parameters: {opt_results['best_params']}")
    print(f"   Best Sharpe Ratio: {opt_results['best_score']:.4f}")
    print(f"   Best Total Return: {opt_results['best_results']['metrics']['total_return']*100:.2f}%")
    print()
    
    # Show top 3 parameter combinations
    print("   Top 3 Parameter Combinations:")
    top_3 = optimizer.get_top_results(n=3)
    for i, result in enumerate(top_3):
        print(f"   {i+1}. {result['params']} → Sharpe: {result['score']:.4f}")
    print()
    
    # ========================================================================
    # TEST 3: ML Strategy (if sklearn available)
    # ========================================================================
    print("="*70)
    print("TEST 3: MACHINE LEARNING STRATEGY (Random Forest)")
    print("="*70)
    
    try:
        from src.strategy.ml_strategy import MLStrategy, create_ml_strategy
        
        print("Training Random Forest model...")
        ml = MLStrategy(model_type='random_forest')
        
        # Prepare features
        X, y = ml.prepare_features(data)
        print(f"   Features prepared: {X.shape[0]} samples, {X.shape[1]} features")
        
        # Train model
        train_results = ml.train_model(X, y, test_size=0.2)
        print(f"\n   Training Results:")
        print(f"   Train Accuracy: {train_results['train_accuracy']*100:.2f}%")
        print(f"   Test Accuracy: {train_results['test_accuracy']*100:.2f}%")
        
        # Show feature importance
        if train_results.get('feature_importance'):
            print(f"\n   Top 5 Most Important Features:")
            sorted_features = sorted(
                train_results['feature_importance'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for i, (feat, imp) in enumerate(sorted_features[:5]):
                print(f"   {i+1}. {feat}: {imp:.4f}")
        
        # Backtest ML strategy
        print(f"\n   Running ML strategy backtest...")
        ml_strategy_func = create_ml_strategy(ml)
        ml_results = backtester.run_backtest(ml_strategy_func, data, position_size=0.1)
        
        print(f"\n📊 ML Strategy Results:")
        print(f"   Total Trades: {ml_results['metrics']['total_trades']}")
        print(f"   Win Rate: {ml_results['metrics']['win_rate']*100:.1f}%")
        print(f"   Total Return: {ml_results['metrics']['total_return']*100:.2f}%")
        print(f"   Sharpe Ratio: {ml_results['metrics']['sharpe_ratio']:.4f}")
        print(f"   Max Drawdown: {ml_results['metrics']['max_drawdown']*100:.2f}%")
        print()
        
    except ImportError:
        print("   ⚠️  scikit-learn not available")
        print("   Install with: pip install scikit-learn xgboost")
        print()
    except Exception as e:
        print(f"   ⚠️  ML strategy failed: {e}")
        print()
    
    # ========================================================================
    # COMPARISON
    # ========================================================================
    print("="*70)
    print("STRATEGY COMPARISON")
    print("="*70)
    print()
    
    strategies = [
        ("Multi-Engine (6 engines)", multi_results),
        ("Optimized SMA", opt_results['best_results'])
    ]
    
    try:
        strategies.append(("ML Random Forest", ml_results))
    except:
        pass
    
    print(f"{'Strategy':<25} {'Return':<12} {'Sharpe':<10} {'Win Rate':<10} {'Trades':<8}")
    print("-"*70)
    
    for name, results in strategies:
        metrics = results['metrics']
        print(f"{name:<25} "
              f"{metrics['total_return']*100:>10.2f}% "
              f"{metrics['sharpe_ratio']:>9.4f} "
              f"{metrics['win_rate']*100:>8.1f}% "
              f"{metrics['total_trades']:>7}")
    
    print()
    
    # ========================================================================
    # GENERATE REPORT
    # ========================================================================
    print("="*70)
    print("GENERATING PERFORMANCE REPORT")
    print("="*70)
    print()
    
    # Generate report for best strategy
    best_strategy = max(strategies, key=lambda x: x[1]['metrics']['sharpe_ratio'])
    print(f"Best Strategy: {best_strategy[0]}")
    print()
    
    report = analytics.generate_report(best_strategy[1], format='text')
    print(report)
    
    # Export HTML report
    try:
        analytics.export_report(
            best_strategy[1],
            'data/logs/advanced_strategy_report.html',
            format='html'
        )
        print("\n✓ HTML report exported to: data/logs/advanced_strategy_report.html")
    except Exception as e:
        print(f"\n⚠️  Report export failed: {e}")
    
    print()
    print("="*70)
    print("DEMO COMPLETE!")
    print("="*70)
    print()
    print("🎉 All advanced features demonstrated successfully!")
    print()
    print("Next Steps:")
    print("1. Try different parameter combinations")
    print("2. Test with real market data (CCXT)")
    print("3. Implement custom strategies")
    print("4. Deploy with live paper trading")
    print()


if __name__ == "__main__":
    run_advanced_demo()
