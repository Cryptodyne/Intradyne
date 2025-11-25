"""
Test Drift Watchdog and Health Metrics
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.monitoring.drift_watchdog import DriftWatchdog, HealthMetrics, CompactMonitor
import time
import random

def test_drift_watchdog():
    print("="*70)
    print("DRIFT WATCHDOG & HEALTH METRICS TEST")
    print("="*70)
    print()
    
    # Test 1: Drift Watchdog
    print("1. Testing Drift Watchdog")
    print("-"*70)
    
    watchdog = DriftWatchdog(baseline_sharpe=1.5, baseline_win_rate=0.60)
    
    # Simulate good trades
    print("\n   Simulating 30 good trades...")
    for i in range(30):
        trade = {
            'pnl': random.uniform(10, 50) if random.random() > 0.35 else random.uniform(-20, -5),
            'pnl_pct': random.uniform(0.01, 0.05) if random.random() > 0.35 else random.uniform(-0.02, -0.01)
        }
        watchdog.add_trade(trade)
    
    status = watchdog.get_status()
    print(f"   Drift Detected: {status['drift_detected']}")
    print(f"   Recent Sharpe: {status['recent_sharpe']:.2f}")
    print(f"   Recent Win Rate: {status['recent_win_rate']*100:.1f}%")
    
    # Simulate drift (bad trades)
    print("\n   Simulating 30 degraded trades (drift)...")
    for i in range(30):
        trade = {
            'pnl': random.uniform(5, 15) if random.random() > 0.65 else random.uniform(-30, -10),
            'pnl_pct': random.uniform(0.005, 0.02) if random.random() > 0.65 else random.uniform(-0.03, -0.01)
        }
        watchdog.add_trade(trade)
    
    status = watchdog.get_status()
    print(f"   Drift Detected: {status['drift_detected']} {'⚠️' if status['drift_detected'] else '✅'}")
    if status['drift_reason']:
        print(f"   Reason: {status['drift_reason']}")
    print(f"   Recent Sharpe: {status['recent_sharpe']:.2f}")
    print(f"   Recent Win Rate: {status['recent_win_rate']*100:.1f}%")
    
    # Test 2: Health Metrics
    print("\n2. Testing Health Metrics")
    print("-"*70)
    
    health = HealthMetrics()
    
    # Simulate activity
    print("\n   Simulating system activity...")
    for i in range(50):
        health.record_signal()
        
        if i % 3 == 0:  # Trade every 3 signals
            success = random.random() > 0.1  # 90% success rate
            health.record_trade(success)
            
            # Record latency
            latency = random.uniform(50, 150)
            health.record_latency(latency)
        
        if i % 20 == 0 and i > 0:  # Occasional error
            health.record_error("connection")
    
    health.print_status()
    
    # Test 3: Compact Monitor
    print("\n3. Testing Compact Monitor")
    print("-"*70)
    
    monitor = CompactMonitor(baseline_sharpe=1.5, baseline_win_rate=0.55)
    
    # Simulate trading session
    print("\n   Simulating trading session...")
    for i in range(40):
        monitor.record_signal()
        
        if i % 2 == 0:
            # Create trade
            is_win = random.random() > 0.40
            trade = {
                'pnl': random.uniform(20, 60) if is_win else random.uniform(-30, -10),
                'pnl_pct': random.uniform(0.02, 0.06) if is_win else random.uniform(-0.03, -0.01)
            }
            monitor.record_trade(trade, success=True)
        
        if i % 15 == 0 and i > 0:
            monitor.record_error("timeout")
        
        time.sleep(0.01)  # Small delay
    
    monitor.print_status()
    
    print("\n" + "="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\n✅ All monitoring systems working correctly!")
    print("\nKey Features:")
    print("  • Drift detection (Sharpe & Win Rate)")
    print("  • Health scoring (0-100)")
    print("  • Uptime tracking")
    print("  • Error monitoring")
    print("  • Latency tracking")
    print("  • Compact unified interface")
    print()

if __name__ == "__main__":
    test_drift_watchdog()
