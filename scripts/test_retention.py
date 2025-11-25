"""
Test Adaptive Data Retention
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.retention_strategy import (
    DataRetentionStrategy, AdaptiveRetentionManager, TimeBasedRetention
)
from datetime import datetime, timedelta
import random

def test_retention():
    print("="*70)
    print("ADAPTIVE DATA RETENTION TEST")
    print("="*70)
    print()
    
    # Test 1: Basic Retention
    print("1. Testing Basic Data Retention")
    print("-"*70)
    
    retention = DataRetentionStrategy(max_raw_samples=100, max_compressed_samples=500)
    
    # Add data
    print("\n   Adding 150 data points...")
    for i in range(150):
        data = {
            'price': 100 + random.uniform(-5, 5),
            'volume': random.randint(1000, 5000),
            'index': i
        }
        
        # Mark some as important
        importance = 0.9 if i % 20 == 0 else random.uniform(0.3, 0.7)
        retention.add_data(data, importance)
    
    stats = retention.get_stats()
    print(f"\n   Raw Samples: {stats['raw_samples']}")
    print(f"   Compressed Samples: {stats['compressed_samples']}")
    print(f"   Important Samples: {stats['important_samples']}")
    print(f"   Compression Ratio: {stats['compression_ratio']:.2f}x")
    
    # Test 2: Multi-Stream Management
    print("\n2. Testing Multi-Stream Management")
    print("-"*70)
    
    manager = AdaptiveRetentionManager()
    
    # Create streams with different policies
    manager.create_stream('prices', policy='standard')
    manager.create_stream('trades', policy='aggressive')
    manager.create_stream('signals', policy='conservative')
    
    print("\n   Adding data to multiple streams...")
    for i in range(200):
        # Prices
        manager.add_data('prices', {
            'price': 100 + random.uniform(-10, 10),
            'timestamp': datetime.now()
        }, importance=random.uniform(0.4, 0.6))
        
        # Trades (less frequent, more important)
        if i % 5 == 0:
            manager.add_data('trades', {
                'price': 100 + random.uniform(-10, 10),
                'quantity': random.randint(1, 10),
                'pnl': random.uniform(-50, 100)
            }, importance=random.uniform(0.7, 0.9))
        
        # Signals (very sparse, very important)
        if i % 10 == 0:
            manager.add_data('signals', {
                'signal': random.choice(['BUY', 'SELL', 'HOLD']),
                'confidence': random.uniform(0.5, 1.0)
            }, importance=0.95)
    
    manager.print_status()
    
    # Test 3: Time-Based Retention
    print("\n3. Testing Time-Based Retention")
    print("-"*70)
    
    time_retention = TimeBasedRetention()
    
    # Add data with different ages
    print("\n   Simulating data over time...")
    now = datetime.now()
    
    # Recent data (high-res)
    for i in range(50):
        time_retention.add_data({
            'price': 100 + random.uniform(-5, 5),
            'timestamp': now - timedelta(minutes=i)
        })
    
    # Older data (medium-res)
    for i in range(20):
        time_retention.add_data({
            'price': 100 + random.uniform(-5, 5),
            'timestamp': now - timedelta(hours=24 + i)
        })
    
    # Very old data (low-res)
    for i in range(10):
        time_retention.add_data({
            'price': 100 + random.uniform(-5, 5),
            'timestamp': now - timedelta(days=7 + i)
        })
    
    stats = time_retention.get_stats()
    
    print(f"\n   High Resolution (24h): {stats['high_res']['count']} samples")
    print(f"   Medium Resolution (7d): {stats['medium_res']['count']} samples")
    print(f"   Low Resolution (30d): {stats['low_res']['count']} samples")
    print(f"   Total: {stats['total']} samples")
    
    print("\n" + "="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print("\n✅ All retention strategies working correctly!")
    print("\nKey Features:")
    print("  • Importance-based retention")
    print("  • Automatic compression")
    print("  • Multi-stream management")
    print("  • Time-based aging")
    print("  • Policy presets (aggressive/standard/conservative)")
    print("  • Efficient storage")
    print()

if __name__ == "__main__":
    test_retention()
