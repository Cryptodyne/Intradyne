import sys
import os
import pandas as pd
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk import TailRiskHedger

def test_hedging():
    print("="*70)
    print("TESTING TAIL RISK HEDGING")
    print("="*70)
    
    # 1. Setup
    portfolio_value = 100000 # $100k portfolio
    hedger = TailRiskHedger(portfolio_value, risk_threshold=0.05, hedge_ratio=1.0) # Full hedge
    
    print(f"Portfolio Value: ${portfolio_value:,.2f}")
    
    # 2. Simulate Market Crash
    print("\n--- Simulating Market Crash ---")
    start_price = 50000
    crash_price = 40000 # 20% drop
    volatility = 0.8 # High volatility
    
    print(f"Start Price: ${start_price:,.2f}")
    
    # Execute Hedge
    print("Executing Hedge (Buying Puts)...")
    hedge_info = hedger.execute_hedge(start_price, volatility)
    
    print(f"  Strike Price: ${hedge_info['strike_price']:,.2f} (5% OTM)")
    print(f"  Premium Paid: ${hedge_info['premium_paid']:,.2f}")
    
    # Calculate Portfolio Loss without Hedge
    portfolio_loss = portfolio_value * ((crash_price - start_price) / start_price)
    print(f"\nPortfolio Loss (Unhedged): ${portfolio_loss:,.2f}")
    
    # Calculate Hedge Value after Crash
    hedge_value = hedger.update_hedge_value(crash_price)
    hedge_pnl = hedger.close_hedge(crash_price)
    
    print(f"Hedge Payoff: ${hedge_value:,.2f}")
    print(f"Hedge P&L (Net): ${hedge_pnl:,.2f}")
    
    # Total P&L
    total_pnl = portfolio_loss + hedge_pnl
    print(f"\nTotal P&L (Hedged): ${total_pnl:,.2f}")
    print(f"Loss Reduction: {(1 - total_pnl/portfolio_loss)*100:.1f}%")
    
    # 3. Simulate Normal Market (Cost of Hedging)
    print("\n--- Simulating Normal Market (No Crash) ---")
    hedger = TailRiskHedger(portfolio_value)
    hedge_info = hedger.execute_hedge(start_price, 0.5) # Normal vol
    
    end_price = 51000 # Slight rise
    
    hedge_pnl = hedger.close_hedge(end_price)
    print(f"Price Move: ${start_price} -> ${end_price}")
    print(f"Hedge P&L (Cost): ${hedge_pnl:,.2f}")
    print(" (This is the 'insurance premium' lost when no crash happens)")

    print("\n" + "="*70)
    print("✅ Hedging Tests Complete")
    print("="*70)

if __name__ == "__main__":
    test_hedging()
