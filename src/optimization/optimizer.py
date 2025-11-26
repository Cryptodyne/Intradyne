import itertools
import numpy as np
import pandas as pd
from typing import Dict, List, Type, Any

class StrategyOptimizer:
    """
    Optimizes strategy parameters using Grid Search.
    """
    
    def __init__(self, strategy_class: Type, data: pd.DataFrame):
        self.strategy_class = strategy_class
        self.data = data
        self.results = []

    def optimize_grid(self, param_grid: Dict[str, List[Any]], metric: str = 'sharpe') -> Dict[str, Any]:
        """
        Runs grid search over parameter combinations.
        
        Args:
            param_grid: Dictionary where keys are parameter names and values are lists of values to try.
            metric: Metric to optimize for ('sharpe', 'total_return', 'win_rate').
            
        Returns:
            Dictionary containing best parameters and performance metrics.
        """
        keys = param_grid.keys()
        combinations = list(itertools.product(*param_grid.values()))
        
        print(f"Starting optimization with {len(combinations)} combinations...")
        
        best_score = -float('inf')
        best_params = None
        best_metrics = None
        
        for i, combo in enumerate(combinations):
            params = dict(zip(keys, combo))
            
            # Run simulation with these params
            metrics = self._evaluate(params)
            
            # Store result
            result = {**params, **metrics}
            self.results.append(result)
            
            # Check if best
            score = metrics.get(metric, -float('inf'))
            if score > best_score:
                best_score = score
                best_params = params
                best_metrics = metrics
                
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(combinations)} combinations...")
                
        return {
            'best_params': best_params,
            'best_metrics': best_metrics,
            'all_results': pd.DataFrame(self.results)
        }

    def _evaluate(self, params: Dict[str, Any]) -> Dict[str, float]:
        """
        Instantiates strategy with params and runs simulation.
        This is a simplified simulation for demonstration.
        """
        # Instantiate strategy
        strategy = self.strategy_class(**params)
        
        # Run strategy on data (Simplified backtest logic)
        # In a real scenario, this would call the full Backtester
        
        # Mocking the backtest result based on params for demonstration
        # We'll assume some params are "better" to show optimization working
        
        # Example: TrendEngine params (rsi_period, macd_fast, macd_slow)
        # Let's pretend RSI=14, Fast=12, Slow=26 is the "golden" standard
        
        score_base = 1.0
        
        # RSI Penalty
        if 'rsi_period' in params:
            diff = abs(params['rsi_period'] - 14)
            score_base -= diff * 0.05
            
        # MACD Penalty
        if 'macd_fast' in params:
            diff = abs(params['macd_fast'] - 12)
            score_base -= diff * 0.02
            
        # Add some randomness
        np.random.seed(sum(int(v) for v in params.values() if isinstance(v, (int, float))))
        random_factor = np.random.normal(0, 0.1)
        
        sharpe = max(0.1, score_base + random_factor + 1.0) # Shift to be positive usually
        total_return = sharpe * 0.2 # Rough correlation
        win_rate = 0.5 + (sharpe * 0.1)
        
        return {
            'sharpe': sharpe,
            'total_return': total_return,
            'win_rate': min(0.9, win_rate)
        }
