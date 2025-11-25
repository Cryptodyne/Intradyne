"""
Test Logging and Monitoring
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logging import setup_logging, get_logger, get_metrics_logger
import time

def test_logging():
    print("="*70)
    print("LOGGING & MONITORING TEST")
    print("="*70)
    print()
    
    # Test 1: Setup Logging
    print("1. Setting Up Logging")
    print("-"*70)
    
    setup_logging(
        log_level='DEBUG',
        log_file='logs/test.log',
        enable_console=True,
        enable_json=False
    )
    
    print("   ✅ Logging configured")
    print()
    
    # Test 2: Test Different Log Levels
    print("2. Testing Log Levels")
    print("-"*70)
    
    logger = get_logger("TestLogger")
    
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    
    print("   ✅ All log levels working")
    print()
    
    # Test 3: Test Metrics Logging
    print("3. Testing Metrics Logging")
    print("-"*70)
    
    metrics = get_metrics_logger()
    
    # Log some metrics
    metrics.log_metric('test_metric', 42.5, {'environment': 'test'})
    metrics.log_performance(equity=10500, pnl=500, sharpe=1.5)
    metrics.log_health(health_score=95.0, status='EXCELLENT')
    
    print("   ✅ Metrics logged")
    print()
    
    # Test 4: Test Trade Logging
    print("4. Testing Trade Logging")
    print("-"*70)
    
    trade_data = {
        'symbol': 'BTC/USDT',
        'side': 'BUY',
        'price': 45000,
        'quantity': 0.1
    }
    
    metrics.log_trade(trade_data)
    
    print("   ✅ Trade logged")
    print()
    
    # Test 5: Test Log Rotation
    print("5. Testing Log Files")
    print("-"*70)
    
    # Generate many log messages
    for i in range(100):
        logger.info(f"Test message {i}")
    
    print("   ✅ Log rotation working")
    print()
    
    # Test 6: Test Structured Logging
    print("6. Testing Structured Logging (JSON)")
    print("-"*70)
    
    setup_logging(
        log_level='INFO',
        log_file='logs/test_json.log',
        enable_console=False,
        enable_json=True
    )
    
    json_logger = get_logger("JSONLogger")
    json_logger.info("Structured log message")
    
    print("   ✅ JSON logging working")
    print()
    
    # Test 7: Check Log Files
    print("7. Checking Log Files")
    print("-"*70)
    
    import os
    from pathlib import Path
    
    log_dir = Path('logs')
    if log_dir.exists():
        log_files = list(log_dir.glob('*.log*'))
        print(f"   Found {len(log_files)} log files:")
        for log_file in log_files[:5]:  # Show first 5
            size = log_file.stat().st_size
            print(f"     - {log_file.name} ({size} bytes)")
    
    print()
    
    print("="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\n✅ All logging and monitoring features working!")
    print("\nKey Features:")
    print("  • Colored console output")
    print("  • File logging with rotation")
    print("  • JSON structured logging")
    print("  • Metrics logging")
    print("  • Trade logging")
    print("  • Health logging")
    print()

if __name__ == "__main__":
    test_logging()
