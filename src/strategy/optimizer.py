import numpy as np
from typing import Dict, List, Any, Callable, Tuple
import itertools
from datetime import datetime
import logging

class StrategyOptimizer:
    """
    Strategy parameter optimization with multiple methods.
    Supports grid search, random search, and walk-forward optimization.
    """
    
    def __init__(self, backtester):
        """
        Initialize optimizer.
        
        Args:
            backtester: Backtester instance
        """
        self.backtester = backtester
        self.logger = logging.getLogger("StrategyOptimizer")
        self.optimization_results = []
    
    def grid_search(self, param_grid: Dict[str, List], data, 
                   strategy_func: Callable, metric: str = 'sharpe_ratio',
                   position_size: float = 0.1) -> Dict[str, Any]:
        """
        Exhaustive grid search over parameter space.
        
        Args:
            param_grid: Dictionary of parameter names to lists of values
            data: Historical data
            strategy_func: Strategy function that takes (data, index, **params)
            metric: Metric to optimize ('sharpe_ratio', 'total_return', 'profit_factor')
            position_size: Position size for backtesting
            
        Returns:
            Best parameters and results
        """
        self.logger.info(f"Starting grid search with {len(param_grid)} parameters")
        
        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        total_combinations = len(combinations)
        self.logger.info(f"Testing {total_combinations} parameter combinations")
        
        best_score = -np.inf
        best_params = None
        best_results = None
        
        for i, combination in enumerate(combinations):
            params = dict(zip(param_names, combination))
            
            # Create strategy with these parameters
            def parameterized_strategy(data, index):
                return strategy_func(data, index, **params)
            
            # Run backtest
            try:
                results = self.backtester.run_backtest(
                    parameterized_strategy, data, position_size
                )
                
                score = results['metrics'].get(metric, -np.inf)
                
                # Track result
                self.optimization_results.append({
                    'params': params,
                    'score': score,
                    'metrics': results['metrics']
                })
                
                # Update best
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_results = results
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Progress: {i+1}/{total_combinations} ({(i+1)/total_combinations*100:.1f}%)")
            
            except Exception as e:
                self.logger.warning(f"Failed to test params {params}: {e}")
        
        self.logger.info(f"Grid search complete. Best {metric}: {best_score:.4f}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'best_results': best_results,
            'all_results': self.optimization_results
        }
    
    def random_search(self, param_ranges: Dict[str, Tuple], data,
                     strategy_func: Callable, n_iterations: int = 50,
                     metric: str = 'sharpe_ratio', position_size: float = 0.1) -> Dict[str, Any]:
        """
        Random search over parameter space.
        
        Args:
            param_ranges: Dictionary of parameter names to (min, max) tuples
            data: Historical data
            strategy_func: Strategy function
            n_iterations: Number of random samples
            metric: Metric to optimize
            position_size: Position size
            
        Returns:
            Best parameters and results
        """
        self.logger.info(f"Starting random search with {n_iterations} iterations")
        
        best_score = -np.inf
        best_params = None
        best_results = None
        
        for i in range(n_iterations):
            # Sample random parameters
            params = {}
            for param_name, (min_val, max_val) in param_ranges.items():
                if isinstance(min_val, int):
                    params[param_name] = np.random.randint(min_val, max_val + 1)
                else:
                    params[param_name] = np.random.uniform(min_val, max_val)
            
            # Create strategy
            def parameterized_strategy(data, index):
                return strategy_func(data, index, **params)
            
            # Run backtest
            try:
                results = self.backtester.run_backtest(
                    parameterized_strategy, data, position_size
                )
                
                score = results['metrics'].get(metric, -np.inf)
                
                # Track result
                self.optimization_results.append({
                    'params': params,
                    'score': score,
                    'metrics': results['metrics']
                })
                
                # Update best
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_results = results
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Progress: {i+1}/{n_iterations} ({(i+1)/n_iterations*100:.1f}%)")
            
            except Exception as e:
                self.logger.warning(f"Failed to test params {params}: {e}")
        
        self.logger.info(f"Random search complete. Best {metric}: {best_score:.4f}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'best_results': best_results,
            'all_results': self.optimization_results
        }
    
    def walk_forward(self, data, strategy_func: Callable, params: Dict,
                    train_window: int = 30, test_window: int = 7,
                    step_size: int = 7, position_size: float = 0.1) -> Dict[str, Any]:
        """
        Walk-forward optimization and testing.
        
        Args:
            data: Historical data
            strategy_func: Strategy function
            params: Strategy parameters
            train_window: Training window size (days)
            test_window: Testing window size (days)
            step_size: Step size for rolling window
            position_size: Position size
            
        Returns:
            Walk-forward results
        """
        self.logger.info(f"Starting walk-forward optimization")
        self.logger.info(f"Train: {train_window} days, Test: {test_window} days, Step: {step_size} days")
        
        # Calculate number of windows
        total_periods = len(data)
        window_size = train_window + test_window
        n_windows = (total_periods - window_size) // step_size + 1
        
        self.logger.info(f"Total windows: {n_windows}")
        
        in_sample_results = []
        out_sample_results = []
        
        for i in range(n_windows):
            start_idx = i * step_size
            train_end_idx = start_idx + train_window
            test_end_idx = train_end_idx + test_window
            
            if test_end_idx > total_periods:
                break
            
            # Split data
            train_data = data.iloc[start_idx:train_end_idx]
            test_data = data.iloc[train_end_idx:test_end_idx]
            
            # Create strategy
            def parameterized_strategy(data, index):
                return strategy_func(data, index, **params)
            
            # Train (in-sample)
            try:
                train_results = self.backtester.run_backtest(
                    parameterized_strategy, train_data, position_size
                )
                in_sample_results.append(train_results['metrics'])
            except Exception as e:
                self.logger.warning(f"Train window {i} failed: {e}")
                continue
            
            # Test (out-of-sample)
            try:
                test_results = self.backtester.run_backtest(
                    parameterized_strategy, test_data, position_size
                )
                out_sample_results.append(test_results['metrics'])
            except Exception as e:
                self.logger.warning(f"Test window {i} failed: {e}")
        
        # Aggregate results
        if in_sample_results and out_sample_results:
            avg_is_sharpe = np.mean([r['sharpe_ratio'] for r in in_sample_results])
            avg_oos_sharpe = np.mean([r['sharpe_ratio'] for r in out_sample_results])
            avg_is_return = np.mean([r['total_return'] for r in in_sample_results])
            avg_oos_return = np.mean([r['total_return'] for r in out_sample_results])
            
            self.logger.info(f"In-sample Sharpe: {avg_is_sharpe:.4f}")
            self.logger.info(f"Out-of-sample Sharpe: {avg_oos_sharpe:.4f}")
            
            return {
                'in_sample_sharpe': avg_is_sharpe,
                'out_sample_sharpe': avg_oos_sharpe,
                'in_sample_return': avg_is_return,
                'out_sample_return': avg_oos_return,
                'n_windows': len(in_sample_results),
                'in_sample_results': in_sample_results,
                'out_sample_results': out_sample_results,
                'overfitting_ratio': avg_is_sharpe / avg_oos_sharpe if avg_oos_sharpe != 0 else np.inf
            }
        else:
            return {'error': 'No valid results'}
    
    def detect_overfitting(self, in_sample_metric: float, 
                          out_sample_metric: float) -> Dict[str, Any]:
        """
        Detect overfitting by comparing in-sample vs out-of-sample performance.
        
        Args:
            in_sample_metric: In-sample performance
            out_sample_metric: Out-of-sample performance
            
        Returns:
            Overfitting analysis
        """
        ratio = in_sample_metric / out_sample_metric if out_sample_metric != 0 else np.inf
        degradation = (in_sample_metric - out_sample_metric) / in_sample_metric if in_sample_metric != 0 else 0
        
        if ratio > 1.5:
            status = "SEVERE_OVERFITTING"
        elif ratio > 1.2:
            status = "MODERATE_OVERFITTING"
        elif ratio > 1.0:
            status = "SLIGHT_OVERFITTING"
        else:
            status = "ROBUST"
        
        return {
            'status': status,
            'ratio': ratio,
            'degradation_pct': degradation * 100,
            'in_sample': in_sample_metric,
            'out_sample': out_sample_metric
        }
    
    def get_top_results(self, n: int = 10, metric: str = 'score') -> List[Dict]:
        """Get top N optimization results."""
        sorted_results = sorted(
            self.optimization_results,
            key=lambda x: x.get(metric, -np.inf),
            reverse=True
        )
        return sorted_results[:n]
    
    def export_results(self, filepath: str):
        """Export optimization results to JSON."""
        import json
        
        with open(filepath, 'w') as f:
            json.dump(self.optimization_results, f, indent=2, default=str)
        
        self.logger.info(f"Optimization results exported to {filepath}")
