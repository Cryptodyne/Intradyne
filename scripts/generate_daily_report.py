# Daily Paper Trading Report Generator with Charts
"""Generate daily performance reports for Bitget paper trading.

This script:
- Analyzes paper trading results from CSV
- Calculates daily performance metrics
- Generates formatted markdown report with charts
- Creates PNG charts (equity curve, P&L, volume breakdown)
- Saves to reports/daily/daily_report_YYYY-MM-DD.md
"""

import pandas as pd
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def generate_charts(df, today_trades, output_dir):
    """Generate performance charts."""
    charts_dir = os.path.join(output_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    chart_paths = {}
    
    # Set style
    plt.style.use('dark_background')
    
    # Chart 1: Equity Curve (last 7 days)
    try:
        last_7_days = df[df['date'] >= (datetime.now().date() - timedelta(days=7))]
        
        if not last_7_days.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Simulate equity curve (simplified)
            daily_pnl = last_7_days.groupby('date').apply(
                lambda x: x[x['side'] == 'SELL']['total_proceeds'].sum() - x[x['side'] == 'BUY']['total_cost'].sum()
                if 'total_proceeds' in x.columns and 'total_cost' in x.columns else 0
            )
            
            cumulative_pnl = daily_pnl.cumsum()
            equity = 10000 + cumulative_pnl  # Starting capital + cumulative P&L
            
            ax.plot(equity.index, equity.values, marker='o', linewidth=2, color='#00ff41', markersize=8)
            ax.fill_between(equity.index, 10000, equity.values, alpha=0.3, color='#00ff41')
            ax.axhline(y=10000, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')
            
            ax.set_title('📈 Equity Curve (Last 7 Days)', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Equity ($)', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format y-axis
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            plt.tight_layout()
            chart_path = os.path.join(charts_dir, f'equity_curve_{today_str}.png')
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            chart_paths['equity'] = chart_path
    except Exception as e:
        print(f"⚠️ Could not generate equity chart: {e}")
    
    # Chart 2: Daily Trading Volume (last 7 days)
    try:
        last_7_days = df[df['date'] >= (datetime.now().date() - timedelta(days=7))]
        
        if not last_7_days.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            daily_volume = last_7_days.groupby('date')['value'].sum()
            
            colors = ['#00ff41' if i == len(daily_volume)-1 else '#0088ff' for i in range(len(daily_volume))]
            ax.bar(daily_volume.index, daily_volume.values, color=colors, edgecolor='white', linewidth=1.5)
            
            ax.set_title('💰 Daily Trading Volume (Last 7 Days)', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Volume ($)', fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            
            # Format y-axis
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            # Highlight today
            if len(daily_volume) > 0:
                ax.text(daily_volume.index[-1], daily_volume.values[-1], '← TODAY', 
                       fontsize=10, va='bottom', ha='left', color='#00ff41')
            
            plt.tight_layout()
            chart_path = os.path.join(charts_dir, f'daily_volume_{today_str}.png')
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            chart_paths['volume'] = chart_path
    except Exception as e:
        print(f"⚠️ Could not generate volume chart: {e}")
    
    # Chart 3: Symbol Distribution (today)
    try:
        if not today_trades.empty and len(today_trades) > 0:
            fig, ax = plt.subplots(figsize=(10, 8))
            
            symbol_volume = today_trades.groupby('symbol')['value'].sum()
            
            colors = ['#00ff41', '#0088ff', '#ff00ff', '#ffaa00']
            explode = [0.05] * len(symbol_volume)
            
            wedges, texts, autotexts = ax.pie(
                symbol_volume.values,
                labels=symbol_volume.index,
                autopct='%1.1f%%',
                colors=colors[:len(symbol_volume)],
                explode=explode,
                textprops={'fontsize': 12, 'weight': 'bold'}
            )
            
            ax.set_title('🥧 Trading Volume by Symbol (Today)', fontsize=16, fontweight='bold', pad=20)
            
            plt.tight_layout()
            chart_path = os.path.join(charts_dir, f'symbol_distribution_{today_str}.png')
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            chart_paths['distribution'] = chart_path
    except Exception as e:
        print(f"⚠️ Could not generate distribution chart: {e}")
    
    return chart_paths


def generate_daily_report(trades_file='reports/paper_trades.csv', output_dir='reports/daily'):
    """Generate daily paper trading report with charts."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if trades file exists
    if not os.path.exists(trades_file):
        print("❌ No trades file found. Run paper trading first.")
        print(f"   Expected file: {trades_file}")
        print("\n💡 Start paper trading: python scripts/run_continuous_paper_trading.py")
        return None
    
    # Load trades
    try:
        df = pd.read_csv(trades_file)
    except Exception as e:
        print(f"❌ Error reading trades file: {e}")
        return None
    
    if df.empty:
        print("❌ No trades found in CSV.")
        return None
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Get today's date
    today = datetime.now().date()
    today_str = today.strftime('%Y-%m-%d')
    
    # Filter today's trades
    df['date'] = df['timestamp'].dt.date
    today_trades = df[df['date'] == today]
    
    # Calculate metrics
    total_trades = len(today_trades)
    buy_trades = len(today_trades[today_trades['side'] == 'BUY'])
    sell_trades = len(today_trades[today_trades['side'] == 'SELL'])
    
    total_volume = today_trades['value'].sum() if total_trades > 0 else 0
    total_fees = today_trades['fee'].sum() if total_trades > 0 else 0
    
    sell_proceeds = today_trades[today_trades['side'] == 'SELL']['total_proceeds'].sum() if 'total_proceeds' in today_trades.columns and sell_trades > 0 else 0
    buy_costs = today_trades[today_trades['side'] == 'BUY']['total_cost'].sum() if 'total_cost' in today_trades.columns and buy_trades > 0 else 0
    daily_pnl = sell_proceeds - buy_costs
    
    # Generate charts
    print("\n📊 Generating performance charts...")
    chart_paths = generate_charts(df, today_trades, output_dir)
    
    # Generate report markdown
    report = f"""# 📊 Daily Paper Trading Report
**Date**: {today_str}  
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 💰 Trading Summary

| Metric | Value |
|--------|-------|
| **Total Trades** | {total_trades} |
| **Buy Orders** | {buy_trades} |
| **Sell Orders** | {sell_trades} |
| **Total Volume** | ${total_volume:,.2f} |
| **Total Fees** | ${total_fees:.2f} |
| **Net P&L (Today)** | ${daily_pnl:+,.2f} |

---

## 📈 Performance Charts

"""
    
    # Add chart images
    if 'equity' in chart_paths:
        report += f"### Equity Curve\n![Equity Curve]({os.path.relpath(chart_paths['equity'], output_dir)})\n\n"
    
    if 'volume' in chart_paths:
        report += f"### Daily Volume\n![Daily Volume]({os.path.relpath(chart_paths['volume'], output_dir)})\n\n"
    
    if 'distribution' in chart_paths:
        report += f"### Symbol Distribution\n![Symbol Distribution]({os.path.relpath(chart_paths['distribution'], output_dir)})\n\n"
    
    report += """---

## 📋 Trade Details

"""
    
    if total_trades > 0:
        report += "| Time | Symbol | Side | Amount | Price | Value | Fee |\n"
        report += "|------|--------|------|--------|-------|-------|-----|\n"
        
        for _, trade in today_trades.iterrows():
            time_str = trade['timestamp'].strftime('%H:%M:%S')
            report += f"| {time_str} | {trade['symbol']} | {trade['side']} | {trade['amount']:.6f} | ${trade['price']:,.2f} | ${trade['value']:,.2f} | ${trade['fee']:.2f} |\n"
    else:
        report += "*No trades executed today*\n"
    
    # Add rest of report sections
    report += f"""
---

## 🔍 Performance Analysis

"""
    
    if total_trades > 0:
        report += f"""### Trading Efficiency
- **Average Trade Size**: ${total_volume / total_trades:,.2f}
- **Effective Fee Rate**: {(total_fees / total_volume * 100) if total_volume > 0 else 0:.3f}%

---

"""
    
    report += """## ⚠️ Notes

- 🔒 **Paper Trading Only**: All trades are simulated
- 📊 **Real Data**: Using Bitget production API
- 💵 **Zero Risk**: No real money involved

---

*Report generated by Intradyne v2.1.0*
"""
    
    # Save report
    report_path = os.path.join(output_dir, f'daily_report_{today_str}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Report generated: {report_path}")
    print(f"   Charts saved: {len(chart_paths)} PNG files")
    print(f"\n📊 Summary: {total_trades} trades | ${total_volume:,.2f} volume | ${daily_pnl:+,.2f} P&L")
    
    return report_path


def main():
    """Generate today's report."""
    print("\n" + "="*70)
    print("📊 DAILY PAPER TRADING REPORT GENERATOR (with Charts)")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    try:
        report_path = generate_daily_report()
        
        if report_path:
            print(f"\n✅ Report generation complete!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
