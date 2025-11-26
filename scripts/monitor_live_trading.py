# Live Trading Monitor - Watch RAG-Enhanced Trades in Real-Time
"""Real-time monitoring dashboard for RAG-enhanced paper trading.

Shows:
- Latest market data
- RAG sentiment scores
- Combined signals
- Trade executions
- Portfolio P&L

Press Ctrl+C to stop
"""

import time
import os
from datetime import datetime


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def monitor_trading():
    """Monitor trading activity in real-time."""
    print("🔴 LIVE: RAG-Enhanced Paper Trading Monitor")
    print("="*70)
    print("Press Ctrl+C to stop monitoring\n")
    
    log_file = 'logs/paper_trading.log'
    
    # Check if log exists
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        print("   Make sure RAG paper trading is running!")
        return
    
    print(f"📊 Monitoring: {log_file}\n")
    print("="*70)
    
    # Read and display last 30 lines initially
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            initial_lines = lines[-30:] if len(lines) > 30 else lines
            print(''.join(initial_lines))
    except Exception as e:
        print(f"❌ Error reading log: {e}")
        return
    
    print("\n" + "="*70)
    print("🔴 LIVE UPDATES (new activity will appear below)")
    print("="*70 + "\n")
    
    # Follow new lines
    try:
        with open(log_file, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    # Highlight important events
                    if '✅ SIMULATED BUY' in line or '✅ SIMULATED SELL' in line:
                        print(f"\n🚨 TRADE EXECUTED: {line.strip()}")
                    elif 'Sentiment' in line:
                        print(f"🤖 {line.strip()}")
                    elif 'Combined Signal' in line:
                        print(f"📊 {line.strip()}")
                    elif 'P&L:' in line:
                        print(f"💰 {line.strip()}")
                    else:
                        print(line.strip())
                else:
                    time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    monitor_trading()
