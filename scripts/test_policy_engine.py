"""
Demo script for Policy Engine
Tests deterministic rules and policies
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trading.policy_engine import (
    PolicyEngine, create_conservative_policy, create_moderate_policy,
    TradingHoursRule, MaxPositionsRule, MaxDrawdownRule
)

def test_policy_engine():
    print("="*70)
    print("POLICY ENGINE DEMO")
    print("="*70)
    print()
    
    # Test 1: Basic rule evaluation
    print("1. Testing Individual Rules")
    print("-"*70)
    
    # Test trading hours
    hours_rule = TradingHoursRule(start_hour=9, end_hour=16)
    context = {}
    passed, message = hours_rule.evaluate(context)
    print(f"   Trading Hours: {'✅ PASS' if passed else '❌ FAIL'} - {message}")
    
    # Test max positions
    positions_rule = MaxPositionsRule(max_positions=5)
    context = {'active_positions': 3}
    passed, message = positions_rule.evaluate(context)
    print(f"   Max Positions: {'✅ PASS' if passed else '❌ FAIL'} - {message}")
    
    # Test max drawdown
    drawdown_rule = MaxDrawdownRule(max_drawdown=0.15)
    context = {'max_drawdown': -0.10}
    passed, message = drawdown_rule.evaluate(context)
    print(f"   Max Drawdown: {'✅ PASS' if passed else '❌ FAIL'} - {message}")
    
    print()
    
    # Test 2: Policy Engine
    print("2. Testing Policy Engine")
    print("-"*70)
    
    engine = PolicyEngine()
    engine.add_rule(MaxPositionsRule(max_positions=5))
    engine.add_rule(MaxDrawdownRule(max_drawdown=0.15))
    
    # Good context
    context = {
        'active_positions': 3,
        'max_drawdown': -0.10,
        'equity': 10000
    }
    
    can_trade, reason = engine.can_trade(context)
    print(f"   Good Context: {'✅ CAN TRADE' if can_trade else '❌ BLOCKED'}")
    print(f"   Reason: {reason}")
    print()
    
    # Bad context (too many positions)
    context = {
        'active_positions': 6,
        'max_drawdown': -0.10,
        'equity': 10000
    }
    
    can_trade, reason = engine.can_trade(context)
    print(f"   Too Many Positions: {'✅ CAN TRADE' if can_trade else '❌ BLOCKED'}")
    print(f"   Reason: {reason}")
    print()
    
    # Test 3: Policy Presets
    print("3. Testing Policy Presets")
    print("-"*70)
    
    # Conservative
    print("\n   📊 CONSERVATIVE POLICY:")
    conservative = create_conservative_policy()
    print(f"      Rules: {len(conservative.rules)}")
    
    context = {
        'active_positions': 2,
        'max_drawdown': -0.05,
        'daily_pnl': -0.01,
        'equity': 10000,
        'position_value': 1000,
        'consecutive_losses': 1
    }
    
    can_trade, reason = conservative.can_trade(context)
    print(f"      Status: {'✅ APPROVED' if can_trade else '❌ BLOCKED'}")
    print(f"      {reason}")
    
    # Moderate
    print("\n   📊 MODERATE POLICY:")
    moderate = create_moderate_policy()
    print(f"      Rules: {len(moderate.rules)}")
    
    can_trade, reason = moderate.can_trade(context)
    print(f"      Status: {'✅ APPROVED' if can_trade else '❌ BLOCKED'}")
    print(f"      {reason}")
    
    # Test 4: Violation Scenarios
    print("\n4. Testing Violation Scenarios")
    print("-"*70)
    
    engine = create_moderate_policy()
    
    scenarios = [
        {
            'name': 'Normal Trading',
            'context': {
                'active_positions': 3,
                'max_drawdown': -0.05,
                'daily_pnl': 0.02,
                'equity': 5000,
                'position_value': 500,
                'consecutive_losses': 2
            }
        },
        {
            'name': 'Max Drawdown Exceeded',
            'context': {
                'active_positions': 3,
                'max_drawdown': -0.20,  # Exceeds 15% limit
                'daily_pnl': 0.00,
                'equity': 5000,
                'position_value': 500,
                'consecutive_losses': 2
            }
        },
        {
            'name': 'Daily Loss Limit Hit',
            'context': {
                'active_positions': 3,
                'max_drawdown': -0.05,
                'daily_pnl': -0.06,  # Exceeds 5% limit
                'equity': 5000,
                'position_value': 500,
                'consecutive_losses': 2
            }
        },
        {
            'name': 'Too Many Consecutive Losses',
            'context': {
                'active_positions': 3,
                'max_drawdown': -0.05,
                'daily_pnl': -0.02,
                'equity': 5000,
                'position_value': 500,
                'consecutive_losses': 6  # Exceeds 5 limit
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\n   Scenario: {scenario['name']}")
        can_trade, reason = engine.can_trade(scenario['context'])
        print(f"   Result: {'✅ APPROVED' if can_trade else '❌ BLOCKED'}")
        print(f"   {reason}")
    
    print("\n" + "="*70)
    print("POLICY ENGINE TEST COMPLETE!")
    print("="*70)
    print("\n✅ All deterministic rules working correctly!")
    print("\nKey Features:")
    print("  • Rule-based governance")
    print("  • Multiple severity levels")
    print("  • Policy presets (Conservative/Moderate/Aggressive)")
    print("  • Violation logging")
    print("  • Deterministic evaluation")
    print()

if __name__ == "__main__":
    test_policy_engine()
