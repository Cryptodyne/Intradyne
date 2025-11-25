"""
Monte Carlo Simulation for Risk Analysis
Simulate thousands of possible portfolio outcomes
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta

class MonteCarloSimulator:
    """
    Monte Carlo simulation for portfolio risk analysis.
    Simulates thousands of possible future scenarios.
    """
    
    def __init__(self, num_simulations: int = 10000, time_horizon: int = 252):
        """
        Initialize Monte Carlo simulator.
        
        Args:
            num_simulations: Number of simulations to run
            time_horizon: Time horizon in days (252 = 1 year)
        """
        self.num_simulations = num_simulations
        self.time_horizon = time_horizon
        self.logger = logging.getLogger("MonteCarloSimulator")
        
        self.simulations: Optional[np.ndarray] = None
        self.results: Optional[Dict] = None
    
    def simulate_returns(self, initial_capital: float, 
                        mean_return: float, volatility: float,
                        sharpe_ratio: float = None) -> np.ndarray:
        """
        Simulate portfolio returns using geometric Brownian motion.
        
        Args:
            initial_capital: Starting capital
            mean_return: Expected daily return
            volatility: Daily volatility
            sharpe_ratio: Optional Sharpe ratio (overrides mean_return)
        
        Returns:
            Array of simulated portfolio values [simulations x time_horizon]
        """
        # Adjust mean return if Sharpe ratio provided
        if sharpe_ratio is not None:
            mean_return = sharpe_ratio * volatility
        
        # Initialize array
        simulations = np.zeros((self.num_simulations, self.time_horizon + 1))
        simulations[:, 0] = initial_capital
        
        # Run simulations
        for sim in range(self.num_simulations):
            for day in range(1, self.time_horizon + 1):
                # Geometric Brownian motion
                drift = mean_return - 0.5 * volatility**2
                shock = volatility * np.random.randn()
                
                simulations[sim, day] = simulations[sim, day-1] * np.exp(drift + shock)
        
        self.simulations = simulations
        self.logger.info(f"Completed {self.num_simulations} simulations over {self.time_horizon} days")
        
        return simulations
    
    def analyze_results(self) -> Dict:
        """
        Analyze simulation results.
        
        Returns:
            Dictionary with statistical analysis
        """
        if self.simulations is None:
            raise ValueError("No simulations run yet")
        
        final_values = self.simulations[:, -1]
        initial_value = self.simulations[0, 0]
        
        # Calculate returns
        returns = (final_values - initial_value) / initial_value
        
        # Calculate statistics
        self.results = {
            'initial_capital': initial_value,
            'mean_final_value': np.mean(final_values),
            'median_final_value': np.median(final_values),
            'std_final_value': np.std(final_values),
            'min_final_value': np.min(final_values),
            'max_final_value': np.max(final_values),
            
            'mean_return': np.mean(returns),
            'median_return': np.median(returns),
            'std_return': np.std(returns),
            
            # Percentiles
            'percentile_5': np.percentile(final_values, 5),
            'percentile_25': np.percentile(final_values, 25),
            'percentile_75': np.percentile(final_values, 75),
            'percentile_95': np.percentile(final_values, 95),
            
            # Risk metrics
            'probability_profit': np.mean(returns > 0),
            'probability_loss': np.mean(returns < 0),
            'probability_loss_50pct': np.mean(returns < -0.5),
            'value_at_risk_95': np.percentile(final_values, 5),
            'conditional_var_95': np.mean(final_values[final_values <= np.percentile(final_values, 5)])
        }
        
        return self.results
    
    def get_confidence_intervals(self, confidence: float = 0.95) -> Dict:
        """Get confidence intervals for final portfolio value"""
        if self.simulations is None:
            raise ValueError("No simulations run yet")
        
        final_values = self.simulations[:, -1]
        
        alpha = 1 - confidence
        lower_pct = (alpha / 2) * 100
        upper_pct = (1 - alpha / 2) * 100
        
        return {
            'confidence': confidence,
            'lower_bound': np.percentile(final_values, lower_pct),
            'upper_bound': np.percentile(final_values, upper_pct),
            'median': np.median(final_values)
        }
    
    def calculate_risk_of_ruin(self, ruin_threshold: float = 0.5) -> float:
        """
        Calculate probability of losing more than threshold.
        
        Args:
            ruin_threshold: Loss threshold (0.5 = 50% loss)
        
        Returns:
            Probability of ruin
        """
        if self.simulations is None:
            raise ValueError("No simulations run yet")
        
        initial_value = self.simulations[0, 0]
        min_values = np.min(self.simulations, axis=1)
        
        ruin_level = initial_value * (1 - ruin_threshold)
        probability = np.mean(min_values < ruin_level)
        
        return probability
    
    def print_summary(self):
        """Print simulation summary"""
        if self.results is None:
            self.analyze_results()
        
        r = self.results
        
        print("\n" + "="*70)
        print("MONTE CARLO SIMULATION RESULTS")
        print("="*70)
        
        print(f"\nSimulations: {self.num_simulations:,}")
        print(f"Time Horizon: {self.time_horizon} days")
        print(f"Initial Capital: ${r['initial_capital']:,.2f}")
        
        print(f"\n📊 Final Portfolio Value:")
        print(f"   Mean: ${r['mean_final_value']:,.2f}")
        print(f"   Median: ${r['median_final_value']:,.2f}")
        print(f"   Std Dev: ${r['std_final_value']:,.2f}")
        print(f"   Range: ${r['min_final_value']:,.2f} - ${r['max_final_value']:,.2f}")
        
        print(f"\n📈 Returns:")
        print(f"   Mean: {r['mean_return']*100:+.1f}%")
        print(f"   Median: {r['median_return']*100:+.1f}%")
        print(f"   Std Dev: {r['std_return']*100:.1f}%")
        
        print(f"\n🎯 Confidence Intervals:")
        print(f"   5th Percentile: ${r['percentile_5']:,.2f}")
        print(f"   25th Percentile: ${r['percentile_25']:,.2f}")
        print(f"   75th Percentile: ${r['percentile_75']:,.2f}")
        print(f"   95th Percentile: ${r['percentile_95']:,.2f}")
        
        print(f"\n⚠️  Risk Metrics:")
        print(f"   Probability of Profit: {r['probability_profit']*100:.1f}%")
        print(f"   Probability of Loss: {r['probability_loss']*100:.1f}%")
        print(f"   Probability of 50%+ Loss: {r['probability_loss_50pct']*100:.1f}%")
        print(f"   Value at Risk (95%): ${r['value_at_risk_95']:,.2f}")
        print(f"   Conditional VaR (95%): ${r['conditional_var_95']:,.2f}")
        
        # Risk of ruin
        ruin_prob = self.calculate_risk_of_ruin(0.5)
        print(f"   Risk of Ruin (50% loss): {ruin_prob*100:.2f}%")
        
        print("="*70)
    
    def get_simulation_paths(self, num_paths: int = 100) -> np.ndarray:
        """Get sample simulation paths for visualization"""
        if self.simulations is None:
            raise ValueError("No simulations run yet")
        
        indices = np.random.choice(self.num_simulations, num_paths, replace=False)
        return self.simulations[indices]


class StrategyComparison:
    """Compare multiple trading strategies"""
    
    def __init__(self):
        self.logger = logging.getLogger("StrategyComparison")
        self.strategies: Dict[str, Dict] = {}
    
    def add_strategy(self, name: str, results: Dict):
        """
        Add strategy results for comparison.
        
        Args:
            name: Strategy name
            results: Backtest or trading results
        """
        self.strategies[name] = results
        self.logger.info(f"Added strategy: {name}")
    
    def compare_metrics(self) -> pd.DataFrame:
        """Compare key metrics across strategies"""
        metrics = []
        
        for name, results in self.strategies.items():
            metrics.append({
                'Strategy': name,
                'Total Return': results.get('total_return', 0),
                'Sharpe Ratio': results.get('sharpe_ratio', 0),
                'Max Drawdown': results.get('max_drawdown', 0),
                'Win Rate': results.get('win_rate', 0),
                'Total Trades': results.get('total_trades', 0),
                'Avg Win': results.get('avg_win', 0),
                'Avg Loss': results.get('avg_loss', 0)
            })
        
        return pd.DataFrame(metrics)
    
    def rank_strategies(self, metric: str = 'sharpe_ratio') -> List[Tuple[str, float]]:
        """
        Rank strategies by metric.
        
        Args:
            metric: Metric to rank by
        
        Returns:
            List of (strategy_name, metric_value) sorted by rank
        """
        rankings = []
        
        for name, results in self.strategies.items():
            value = results.get(metric, 0)
            rankings.append((name, value))
        
        # Sort descending (higher is better for most metrics)
        if metric in ['max_drawdown', 'avg_loss']:
            rankings.sort(key=lambda x: x[1])  # Lower is better
        else:
            rankings.sort(key=lambda x: x[1], reverse=True)  # Higher is better
        
        return rankings
    
    def print_comparison(self):
        """Print strategy comparison"""
        df = self.compare_metrics()
        
        print("\n" + "="*90)
        print("STRATEGY COMPARISON")
        print("="*90)
        
        print(f"\n{df.to_string(index=False)}")
        
        print("\n📊 Rankings:")
        
        # Rank by Sharpe Ratio
        print("\n   By Sharpe Ratio:")
        for i, (name, value) in enumerate(self.rank_strategies('sharpe_ratio'), 1):
            print(f"     {i}. {name}: {value:.2f}")
        
        # Rank by Total Return
        print("\n   By Total Return:")
        for i, (name, value) in enumerate(self.rank_strategies('total_return'), 1):
            print(f"     {i}. {name}: {value*100:+.1f}%")
        
        print("="*90)
