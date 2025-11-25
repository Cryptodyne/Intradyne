"""
Scenario Analysis for Trading Strategies
Stress testing and what-if analysis
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import logging

class ScenarioAnalyzer:
    """
    Scenario analysis for trading strategies.
    Test strategies under different market conditions.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ScenarioAnalyzer")
        self.scenarios: Dict[str, Dict] = {}
        self.results: Dict[str, Dict] = {}
    
    def add_scenario(self, name: str, parameters: Dict):
        """
        Add a market scenario.
        
        Args:
            name: Scenario name
            parameters: Scenario parameters (volatility, trend, etc.)
        """
        self.scenarios[name] = parameters
        self.logger.info(f"Added scenario: {name}")
    
    def create_market_scenarios(self) -> Dict[str, Dict]:
        """Create predefined market scenarios"""
        scenarios = {
            'Bull Market': {
                'mean_return': 0.002,  # 0.2% daily
                'volatility': 0.015,
                'trend': 'up',
                'description': 'Strong upward trend, low volatility'
            },
            'Bear Market': {
                'mean_return': -0.0015,  # -0.15% daily
                'volatility': 0.025,
                'trend': 'down',
                'description': 'Downward trend, elevated volatility'
            },
            'Sideways Market': {
                'mean_return': 0.0,
                'volatility': 0.02,
                'trend': 'sideways',
                'description': 'Range-bound, moderate volatility'
            },
            'High Volatility': {
                'mean_return': 0.001,
                'volatility': 0.04,
                'trend': 'volatile',
                'description': 'High volatility, uncertain direction'
            },
            'Market Crash': {
                'mean_return': -0.005,  # -0.5% daily
                'volatility': 0.06,
                'trend': 'crash',
                'description': 'Severe downturn, extreme volatility'
            },
            'Recovery': {
                'mean_return': 0.003,  # 0.3% daily
                'volatility': 0.03,
                'trend': 'recovery',
                'description': 'Strong recovery, high volatility'
            },
            'Low Volatility Bull': {
                'mean_return': 0.0015,
                'volatility': 0.01,
                'trend': 'up',
                'description': 'Steady uptrend, low volatility'
            },
            'Flash Crash': {
                'mean_return': -0.01,  # -1% daily
                'volatility': 0.08,
                'trend': 'crash',
                'description': 'Sudden severe drop, extreme volatility'
            }
        }
        
        for name, params in scenarios.items():
            self.add_scenario(name, params)
        
        return scenarios
    
    def simulate_scenario(self, scenario_name: str, 
                         initial_capital: float = 10000,
                         days: int = 252) -> Dict:
        """
        Simulate portfolio performance under scenario.
        
        Args:
            scenario_name: Name of scenario
            initial_capital: Starting capital
            days: Simulation days
        
        Returns:
            Simulation results
        """
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        scenario = self.scenarios[scenario_name]
        
        # Simulate price path
        prices = [initial_capital]
        for _ in range(days):
            drift = scenario['mean_return'] - 0.5 * scenario['volatility']**2
            shock = scenario['volatility'] * np.random.randn()
            prices.append(prices[-1] * np.exp(drift + shock))
        
        prices = np.array(prices)
        
        # Calculate metrics
        final_value = prices[-1]
        total_return = (final_value - initial_capital) / initial_capital
        max_value = np.max(prices)
        min_value = np.min(prices)
        max_drawdown = (max_value - min_value) / max_value
        
        # Daily returns
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        sharpe = (np.mean(returns) * 252) / volatility if volatility > 0 else 0
        
        results = {
            'scenario': scenario_name,
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'max_value': max_value,
            'min_value': min_value,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'prices': prices
        }
        
        self.results[scenario_name] = results
        return results
    
    def stress_test(self, initial_capital: float = 10000) -> pd.DataFrame:
        """
        Run stress test across all scenarios.
        
        Args:
            initial_capital: Starting capital
        
        Returns:
            DataFrame with results
        """
        if not self.scenarios:
            self.create_market_scenarios()
        
        results = []
        
        for scenario_name in self.scenarios:
            result = self.simulate_scenario(scenario_name, initial_capital)
            
            results.append({
                'Scenario': scenario_name,
                'Final Value': result['final_value'],
                'Return': result['total_return'],
                'Max DD': result['max_drawdown'],
                'Volatility': result['volatility'],
                'Sharpe': result['sharpe_ratio']
            })
        
        return pd.DataFrame(results)
    
    def what_if_analysis(self, base_params: Dict, 
                        variations: Dict[str, List]) -> pd.DataFrame:
        """
        What-if analysis by varying parameters.
        
        Args:
            base_params: Base scenario parameters
            variations: Parameters to vary {param: [values]}
        
        Returns:
            DataFrame with results
        """
        results = []
        
        for param_name, values in variations.items():
            for value in values:
                # Create scenario with varied parameter
                params = base_params.copy()
                params[param_name] = value
                
                scenario_name = f"{param_name}={value}"
                self.add_scenario(scenario_name, params)
                
                # Simulate
                result = self.simulate_scenario(scenario_name)
                
                results.append({
                    'Parameter': param_name,
                    'Value': value,
                    'Final Value': result['final_value'],
                    'Return': result['total_return'],
                    'Sharpe': result['sharpe_ratio']
                })
        
        return pd.DataFrame(results)
    
    def compare_scenarios(self, scenario_names: List[str]) -> Dict:
        """Compare multiple scenarios"""
        comparison = {
            'best_return': None,
            'worst_return': None,
            'best_sharpe': None,
            'worst_drawdown': None,
            'scenarios': {}
        }
        
        best_return = -float('inf')
        worst_return = float('inf')
        best_sharpe = -float('inf')
        worst_dd = 0
        
        for name in scenario_names:
            if name not in self.results:
                self.simulate_scenario(name)
            
            result = self.results[name]
            comparison['scenarios'][name] = result
            
            if result['total_return'] > best_return:
                best_return = result['total_return']
                comparison['best_return'] = name
            
            if result['total_return'] < worst_return:
                worst_return = result['total_return']
                comparison['worst_return'] = name
            
            if result['sharpe_ratio'] > best_sharpe:
                best_sharpe = result['sharpe_ratio']
                comparison['best_sharpe'] = name
            
            if result['max_drawdown'] > worst_dd:
                worst_dd = result['max_drawdown']
                comparison['worst_drawdown'] = name
        
        return comparison
    
    def print_stress_test_results(self, df: pd.DataFrame):
        """Print stress test results"""
        print("\n" + "="*90)
        print("STRESS TEST RESULTS")
        print("="*90)
        
        print(f"\n{df.to_string(index=False, float_format=lambda x: f'{x:,.2f}' if abs(x) > 1 else f'{x:.4f}')}")
        
        print("\n📊 Summary:")
        print(f"   Best Return: {df.loc[df['Return'].idxmax(), 'Scenario']} ({df['Return'].max()*100:+.1f}%)")
        print(f"   Worst Return: {df.loc[df['Return'].idxmin(), 'Scenario']} ({df['Return'].min()*100:+.1f}%)")
        print(f"   Best Sharpe: {df.loc[df['Sharpe'].idxmax(), 'Scenario']} ({df['Sharpe'].max():.2f})")
        print(f"   Worst Drawdown: {df.loc[df['Max DD'].idxmax(), 'Scenario']} ({df['Max DD'].max()*100:.1f}%)")
        
        print("="*90)
    
    def get_scenario_summary(self, scenario_name: str) -> str:
        """Get scenario description"""
        if scenario_name not in self.scenarios:
            return "Unknown scenario"
        
        scenario = self.scenarios[scenario_name]
        return scenario.get('description', 'No description')
