import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.monitoring.performance_monitor import PerformanceMonitor
from src.monitoring.alerts import AlertSystem, AlertLevel, console_alert_handler, file_alert_handler

def test_monitoring():
    print("="*60)
    print("Testing Monitoring & Alert System")
    print("="*60)
    
    # Initialize monitor
    print("\n1. Initializing Performance Monitor...")
    monitor = PerformanceMonitor(window_size=100)
    print("   ✓ Monitor initialized")
    
    # Initialize alert system
    print("\n2. Initializing Alert System...")
    alerts = AlertSystem()
    alerts.add_handler(console_alert_handler)
    alerts.add_handler(file_alert_handler())
    print("   ✓ Alert system initialized with 2 handlers")
    
    # Simulate API calls
    print("\n3. Simulating API calls...")
    for i in range(50):
        # Successful calls
        monitor.record_api_call(
            exchange='bitget',
            endpoint='/api/v3/ticker',
            latency=0.05 + (i % 10) * 0.01,  # 50-150ms
            success=True
        )
        
        # Some failures
        if i % 10 == 0:
            monitor.record_api_call(
                exchange='bitget',
                endpoint='/api/v3/ticker',
                latency=0.5,
                success=False,
                error="Timeout"
            )
    
    print(f"   ✓ Recorded 50 API calls")
    
    # Simulate cache stats
    print("\n4. Recording cache statistics...")
    for i in range(10):
        monitor.record_cache_stats({
            'enabled': True,
            'hits': 70 + i * 5,
            'misses': 30 - i * 2,
            'hit_rate': (70 + i * 5) / 100,
            'size': 50 + i,
            'max_size': 100
        })
    print("   ✓ Recorded cache stats")
    
    # Simulate data quality
    print("\n5. Recording data quality metrics...")
    for i in range(20):
        monitor.record_data_quality(
            symbol='BTC/USDT',
            checks={
                'completeness': True,
                'freshness': i % 5 != 0,  # Some stale data
                'consistency': True,
                'volume': True
            },
            score=0.95 if i % 5 != 0 else 0.75
        )
    print("   ✓ Recorded data quality metrics")
    
    # Get metrics
    print("\n6. Retrieving metrics...")
    
    api_metrics = monitor.get_api_metrics()
    print(f"\n   📡 API Metrics:")
    for ex, metrics in api_metrics.items():
        print(f"      {ex}:")
        print(f"        Total calls: {metrics['total_calls']}")
        print(f"        Success rate: {metrics['success_rate']:.1%}")
        print(f"        Calls/min: {metrics['calls_per_minute']:.1f}")
    
    latency_metrics = monitor.get_latency_metrics()
    print(f"\n   ⚡ Latency Metrics:")
    for ex, metrics in latency_metrics.items():
        print(f"      {ex}:")
        print(f"        Avg: {metrics['avg_ms']:.0f}ms")
        print(f"        P95: {metrics['p95_ms']:.0f}ms")
        print(f"        P99: {metrics['p99_ms']:.0f}ms")
    
    cache_metrics = monitor.get_cache_metrics()
    print(f"\n   💾 Cache Metrics:")
    print(f"      Hit rate: {cache_metrics['current_hit_rate']:.1%}")
    print(f"      Size: {cache_metrics['size']}/{cache_metrics['max_size']}")
    
    quality_metrics = monitor.get_data_quality_metrics()
    print(f"\n   ✅ Data Quality:")
    print(f"      Avg score: {quality_metrics['avg_quality_score']:.1%}")
    print(f"      Sample size: {quality_metrics['sample_size']}")
    
    # Check system health
    print("\n7. Checking system health...")
    health = monitor.get_system_health()
    print(f"\n   🏥 System Health:")
    print(f"      Status: {health['status']}")
    print(f"      Score: {health['health_score']}/100")
    print(f"      Uptime: {health['uptime_hours']:.2f} hours")
    if health['issues']:
        print(f"      Issues:")
        for issue in health['issues']:
            print(f"        - {issue}")
    
    # Test alerts
    print("\n8. Testing alert system...")
    
    # Check metrics and trigger alerts
    alerts.check_api_metrics(api_metrics)
    alerts.check_latency_metrics(latency_metrics)
    alerts.check_cache_metrics(cache_metrics)
    alerts.check_data_quality(quality_metrics)
    alerts.check_system_health(health)
    
    # Get recent alerts
    recent_alerts = alerts.get_recent_alerts(count=5)
    print(f"\n   Recent alerts: {len(recent_alerts)}")
    
    # Export metrics
    print("\n9. Exporting metrics...")
    monitor.export_metrics('data/logs/metrics.json')
    print("   ✓ Metrics exported to data/logs/metrics.json")
    
    # Print summary
    print("\n10. Performance Monitor Summary:")
    monitor.print_summary()
    
    print("\n" + "="*60)
    print("Monitoring System Tests Complete!")
    print("="*60)

if __name__ == "__main__":
    test_monitoring()
