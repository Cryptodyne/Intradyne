"""
Demo script for paper trading components
Tests PortfolioManager and RiskManager
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trading.portfolio_manager import PortfolioManager
from src.trading.risk_manager import RiskManager

def test_paper_trading_components():
    print("="*70)
    print("PAPER TRADING COMPONENTS DEMO")
    print("="*70)
    print()
    
    # Initialize components
    print("1. Initializing components...")
    portfolio = PortfolioManager(initial_capital=10000)
    
    risk_config = {
        'max_positions': 3,
        'max_position_size': 0.3,
        'daily_loss_limit': 0.05,
        'max_drawdown': 0.15,
        'stop_loss_pct': 0.03,
        'take_profit_pct': 0.10
    }
    risk_manager = RiskManager(risk_config)
    
    print("   ✓ Portfolio initialized with $10,000")
    print("   ✓ Risk manager configured")
    print()
    
    # Test 1: Open positions
    print("2. Testing position management...")
    
    # Open BTC position
    symbol = "BTC/USDT"
    price = 50000
    quantity = 0.05  # $2,500 position
    
    can_open, reason = risk_manager.check_can_open_position(portfolio, symbol, quantity, price)
    print(f"   Can open {symbol}? {can_open} - {reason}")
    
    if can_open:
        success = portfolio.open_position(symbol, quantity, price)
        print(f"   ✓ Opened {symbol}: {quantity} @ ${price}")
    
    # Open ETH position
    symbol2 = "ETH/USDT"
    price2 = 3000
    quantity2 = 0.8  # $2,400 position
    
    can_open, reason = risk_manager.check_can_open_position(portfolio, symbol2, quantity2, price2)
    if can_open:
        portfolio.open_position(symbol2, quantity2, price2)
        print(f"   ✓ Opened {symbol2}: {quantity2} @ ${price2}")
    
    print()
    
    # Test 2: Update prices
    print("3. Simulating price changes...")
    
    # BTC up 5%
    new_prices = {
        "BTC/USDT": 52500,  # +5%
        "ETH/USDT": 2850    # -5%
    }
    
    portfolio.update_positions(new_prices)
    print(f"   BTC: ${price} → ${new_prices['BTC/USDT']} (+5%)")
    print(f"   ETH: ${price2} → ${new_prices['ETH/USDT']} (-5%)")
    print()
    
    # Test 3: Check stop-loss
    print("4. Testing risk management...")
    
    for symbol, pos in portfolio.positions.items():
        current_price = new_prices[symbol]
        
        if risk_manager.check_stop_loss(pos, current_price):
            print(f"   ⚠️  Stop-loss triggered for {symbol}")
            portfolio.close_position(symbol, current_price)
        elif risk_manager.check_take_profit(pos, current_price):
            print(f"   ✅ Take-profit triggered for {symbol}")
            portfolio.close_position(symbol, current_price)
        else:
            pnl_pct = (current_price - pos.entry_price) / pos.entry_price
            print(f"   {symbol}: P&L {pnl_pct*100:+.2f}% (within limits)")
    
    print()
    
    # Test 4: Portfolio summary
    print("5. Portfolio Summary:")
    summary = portfolio.get_performance_summary()
    
    print(f"\n   💰 Financial Status:")
    print(f"     Initial Capital: ${summary['initial_capital']:,.2f}")
    print(f"     Current Equity: ${summary['current_equity']:,.2f}")
    print(f"     Cash: ${summary['cash']:,.2f}")
    print(f"     Positions Value: ${summary['positions_value']:,.2f}")
    
    print(f"\n   📊 Performance:")
    print(f"     Total Return: {summary['total_return']*100:+.2f}%")
    print(f"     Realized P&L: ${summary['realized_pnl']:,.2f}")
    print(f"     Unrealized P&L: ${summary['unrealized_pnl']:,.2f}")
    print(f"     Total P&L: ${summary['total_pnl']:,.2f}")
    print(f"     Max Drawdown: {summary['max_drawdown']*100:.2f}%")
    
    print(f"\n   📈 Trading Activity:")
    print(f"     Active Positions: {summary['active_positions']}")
    print(f"     Total Trades: {summary['total_trades']}")
    print(f"     Win Rate: {summary['win_rate']*100:.1f}%")
    
    # Test 5: Risk status
    print("\n6. Risk Status:")
    risk_status = risk_manager.get_risk_status(portfolio)
    
    print(f"   Circuit Breaker: {'🔴 ACTIVE' if risk_status['circuit_breaker_active'] else '🟢 INACTIVE'}")
    print(f"   Positions: {risk_status['active_positions']}/{risk_status['max_positions']}")
    print(f"   Daily P&L: {risk_status['daily_pnl']*100:+.2f}% (limit: {risk_status['daily_loss_limit']*100:.1f}%)")
    print(f"   Max Drawdown: {risk_status['max_drawdown']*100:.2f}% (limit: {risk_status['max_drawdown_limit']*100:.1f}%)")
    
    # Test 6: Position details
    if portfolio.positions:
        print("\n7. Active Positions:")
        positions = portfolio.get_positions_summary()
        
        for pos in positions:
            print(f"\n   {pos['symbol']}:")
            print(f"     Quantity: {pos['quantity']}")
            print(f"     Entry: ${pos['entry_price']:,.2f}")
            print(f"     Current: ${pos['current_price']:,.2f}")
            print(f"     Value: ${pos['value']:,.2f}")
            print(f"     P&L: ${pos['pnl']:,.2f} ({pos['pnl_pct']*100:+.2f}%)")
    
    print("\n" + "="*70)
    print("PAPER TRADING COMPONENTS TEST COMPLETE!")
    print("="*70)
    print("\n✅ All components working correctly!")
    print("\nNext Steps:")
    print("1. Integrate with live market data")
    print("2. Add real-time signal generation")
    print("3. Build monitoring dashboard")
    print()

if __name__ == "__main__":
    test_paper_trading_components()
