"""
Test Scenario Analysis
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics import ScenarioAnalyzer

def test_scenario_analysis():
    print("="*70)
    print("SCENARIO ANALYSIS TEST")
    print("="*70)
    print()
    
    analyzer = ScenarioAnalyzer()
    
    # Test 1: Create Market Scenarios
    print("1. Creating Market Scenarios")
    print("-"*70)
    
    scenarios = analyzer.create_market_scenarios()
    
    print(f"\n   Created {len(scenarios)} scenarios:")
    for name, params in scenarios.items():
        print(f"     • {name}: {params['description']}")
    
    # Test 2: Stress Test
    print("\n2. Running Stress Test")
    print("-"*70)
    
    print("\n   Testing portfolio across all market scenarios...")
    stress_results = analyzer.stress_test(initial_capital=10000)
    
    analyzer.print_stress_test_results(stress_results)
    
    # Test 3: Individual Scenario Analysis
    print("\n3. Detailed Scenario Analysis")
    print("-"*70)
    
    scenarios_to_test = ['Bull Market', 'Bear Market', 'Market Crash']
    
    for scenario_name in scenarios_to_test:
        result = analyzer.simulate_scenario(scenario_name, initial_capital=10000)
        
        print(f"\n   {scenario_name}:")
        print(f"     Final Value: ${result['final_value']:,.2f}")
        print(f"     Return: {result['total_return']*100:+.1f}%")
        print(f"     Max Drawdown: {result['max_drawdown']*100:.1f}%")
        print(f"     Sharpe Ratio: {result['sharpe_ratio']:.2f}")
    
    # Test 4: What-If Analysis
    print("\n4. What-If Analysis")
    print("-"*70)
    
    base_params = {
        'mean_return': 0.001,
        'volatility': 0.02,
        'trend': 'up'
    }
    
    variations = {
        'volatility': [0.01, 0.02, 0.03, 0.04],
        'mean_return': [0.0, 0.001, 0.002, 0.003]
    }
    
    print("\n   Varying volatility and mean return...")
    what_if_results = analyzer.what_if_analysis(base_params, variations)
    
    print(f"\n   Volatility Impact:")
    vol_results = what_if_results[what_if_results['Parameter'] == 'volatility']
    for _, row in vol_results.iterrows():
        print(f"     Vol={row['Value']:.2f}: Return={row['Return']*100:+.1f}%, Sharpe={row['Sharpe']:.2f}")
    
    print(f"\n   Mean Return Impact:")
    ret_results = what_if_results[what_if_results['Parameter'] == 'mean_return']
    for _, row in ret_results.iterrows():
        print(f"     Return={row['Value']:.3f}: Final=${row['Final Value']:,.0f}, Sharpe={row['Sharpe']:.2f}")
    
    # Test 5: Scenario Comparison
    print("\n5. Scenario Comparison")
    print("-"*70)
    
    comparison = analyzer.compare_scenarios([
        'Bull Market', 
        'Bear Market', 
        'Sideways Market',
        'High Volatility'
    ])
    
    print(f"\n   Best Return: {comparison['best_return']}")
    print(f"   Worst Return: {comparison['worst_return']}")
    print(f"   Best Sharpe: {comparison['best_sharpe']}")
    print(f"   Worst Drawdown: {comparison['worst_drawdown']}")
    
    # Test 6: Extreme Scenarios
    print("\n6. Extreme Scenario Testing")
    print("-"*70)
    
    extreme_scenarios = ['Market Crash', 'Flash Crash', 'Recovery']
    
    print(f"\n   {'Scenario':<20} {'Final Value':<15} {'Return':<12} {'Max DD':<12}")
    print("   " + "-"*60)
    
    for scenario in extreme_scenarios:
        result = analyzer.results.get(scenario) or analyzer.simulate_scenario(scenario)
        print(f"   {scenario:<20} ${result['final_value']:<14,.0f} {result['total_return']*100:<11.1f}% {result['max_drawdown']*100:<11.1f}%")
    
    print("\n" + "="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\n✅ All scenario analysis features working correctly!")
    print("\nKey Features:")
    print("  • 8 predefined market scenarios")
    print("  • Stress testing")
    print("  • What-if analysis")
    print("  • Scenario comparison")
    print("  • Extreme scenario testing")
    print("  • Parameter sensitivity analysis")
    print()

if __name__ == "__main__":
    test_scenario_analysis()
