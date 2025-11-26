import pandas as pd
from datetime import datetime

# Load trade data
df = pd.read_csv('reports/rag_paper_trades.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("=" * 70)
print(" BITGET PAPER TRADING REPORT - LATEST")
print("=" * 70)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Bot Runtime: 5h 24m (Since: {df['timestamp'].min()})")
print("=" * 70)

print("\nPORTFOLIO SUMMARY")
print("-" * 70)
starting_balance = 10000.0
total_trades = len(df)

# Calculate P&L
buys = df[df['side'] == 'BUY']['value'].sum()
sells = df[df['side'] == 'SELL']['value'].sum()
pnl = sells - buys

current_equity = starting_balance + pnl
pnl_pct = (pnl / starting_balance) * 100

print(f"Starting Balance:     ${starting_balance:>12,.2f}")
print(f"Current Equity:       ${current_equity:>12,.2f}")
print(f"Total P&L:            ${pnl:>12,.2f} ({pnl_pct:+.2f}%)")
print(f"Total Trades:         {total_trades:>12}")

print("\nTRADING SUMMARY")
print("-" * 70)
buy_count = len(df[df['side'] == 'BUY'])
sell_count = len(df[df['side'] == 'SELL'])
symbols = df['symbol'].unique()

print(f"Buy Orders:           {buy_count:>12}")
print(f"Sell Orders:          {sell_count:>12}")
print(f"Assets Traded:        {', '.join(symbols)}")

print("\nLATEST TRADES (Last 5)")
print("-" * 70)
print(f"{'Time':<20} {'Symbol':<12} {'Side':<6} {'Amount':<12} {'Price':<12} {'Value':<12}")
print("-" * 70)

for _, row in df.tail(5).iterrows():
    time_str = row['timestamp'].strftime('%Y-%m-%d %H:%M')
    print(f"{time_str:<20} {row['symbol']:<12} {row['side']:<6} {row['amount']:>11.4f} ${row['price']:>10,.2f} ${row['value']:>10,.2f}")

print("\n" + "=" * 70)

# Position summary
print("\nCURRENT POSITIONS")
print("-" * 70)
positions = {}
for _, trade in df.iterrows():
    symbol = trade['symbol']
    if symbol not in positions:
        positions[symbol] = {'amount': 0, 'cost_basis': 0}
    
    if trade['side'] == 'BUY':
        positions[symbol]['amount'] += trade['amount']
        positions[symbol]['cost_basis'] += trade['value']
    else:
        positions[symbol]['amount'] -= trade['amount']

for symbol, pos in positions.items():
    if pos['amount'] > 0:
        avg_price = pos['cost_basis'] / pos['amount']
        print(f"{symbol}: {pos['amount']:.4f} units @ ${avg_price:,.2f} avg")

print("\n" + "=" * 70)
print("Report Complete - AI Trading: ACTIVE (Hybrid/Moderate)")
print("=" * 70)
