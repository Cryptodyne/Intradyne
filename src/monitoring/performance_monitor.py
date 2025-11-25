import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import os

class PerformanceMonitor:
    """
    Monitors system performance metrics including API calls, latency, 
    cache performance, and data quality.
    """
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            window_size: Number of recent metrics to keep in memory
        """
        self.window_size = window_size
        self.logger = logging.getLogger("PerformanceMonitor")
        
        # Metrics storage
        self.api_calls = defaultdict(lambda: deque(maxlen=window_size))
        self.latencies = defaultdict(lambda: deque(maxlen=window_size))
        self.errors = defaultdict(lambda: deque(maxlen=window_size))
        self.cache_stats = deque(maxlen=window_size)
        self.data_quality = deque(maxlen=window_size)
        
        # Counters
        self.total_api_calls = defaultdict(int)
        self.total_errors = defaultdict(int)
        self.start_time = time.time()
    
    def record_api_call(self, exchange: str, endpoint: str, latency: float, 
                       success: bool = True, error: Optional[str] = None):
        """
        Record an API call.
        
        Args:
            exchange: Exchange name
            endpoint: API endpoint
            latency: Response time in seconds
            success: Whether the call succeeded
            error: Error message if failed
        """
        timestamp = time.time()
        
        # Record API call
        self.api_calls[exchange].append({
            'timestamp': timestamp,
            'endpoint': endpoint,
            'latency': latency,
            'success': success
        })
        
        # Record latency
        if success:
            self.latencies[exchange].append(latency)
        
        # Record error
        if not success:
            self.errors[exchange].append({
                'timestamp': timestamp,
                'endpoint': endpoint,
                'error': error
            })
            self.total_errors[exchange] += 1
        
        # Update counters
        self.total_api_calls[exchange] += 1
    
    def record_cache_stats(self, stats: Dict[str, Any]):
        """
        Record cache statistics.
        
        Args:
            stats: Cache statistics dictionary
        """
        stats['timestamp'] = time.time()
        self.cache_stats.append(stats)
    
    def record_data_quality(self, symbol: str, checks: Dict[str, bool], 
                           score: float):
        """
        Record data quality metrics.
        
        Args:
            symbol: Trading pair
            checks: Quality check results
            score: Overall quality score (0-1)
        """
        self.data_quality.append({
            'timestamp': time.time(),
            'symbol': symbol,
            'checks': checks,
            'score': score
        })
    
    def get_api_metrics(self, exchange: Optional[str] = None, 
                       time_window: int = 3600) -> Dict[str, Any]:
        """
        Get API call metrics.
        
        Args:
            exchange: Specific exchange or None for all
            time_window: Time window in seconds
            
        Returns:
            Dictionary with API metrics
        """
        cutoff_time = time.time() - time_window
        
        if exchange:
            exchanges = [exchange]
        else:
            exchanges = list(self.api_calls.keys())
        
        metrics = {}
        
        for ex in exchanges:
            calls = [c for c in self.api_calls[ex] if c['timestamp'] > cutoff_time]
            
            if not calls:
                continue
            
            successful = [c for c in calls if c['success']]
            failed = [c for c in calls if not c['success']]
            
            metrics[ex] = {
                'total_calls': len(calls),
                'successful': len(successful),
                'failed': len(failed),
                'success_rate': len(successful) / len(calls) if calls else 0,
                'calls_per_minute': len(calls) / (time_window / 60),
                'total_lifetime_calls': self.total_api_calls[ex],
                'total_lifetime_errors': self.total_errors[ex]
            }
        
        return metrics
    
    def get_latency_metrics(self, exchange: Optional[str] = None) -> Dict[str, Any]:
        """
        Get latency metrics.
        
        Args:
            exchange: Specific exchange or None for all
            
        Returns:
            Dictionary with latency metrics
        """
        if exchange:
            exchanges = [exchange]
        else:
            exchanges = list(self.latencies.keys())
        
        metrics = {}
        
        for ex in exchanges:
            latencies = list(self.latencies[ex])
            
            if not latencies:
                continue
            
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            
            metrics[ex] = {
                'avg_ms': sum(latencies) / n * 1000,
                'min_ms': min(latencies) * 1000,
                'max_ms': max(latencies) * 1000,
                'p50_ms': sorted_latencies[n // 2] * 1000,
                'p95_ms': sorted_latencies[int(n * 0.95)] * 1000,
                'p99_ms': sorted_latencies[int(n * 0.99)] * 1000,
                'sample_size': n
            }
        
        return metrics
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """
        Get cache performance metrics.
        
        Returns:
            Dictionary with cache metrics
        """
        if not self.cache_stats:
            return {'enabled': False}
        
        latest = self.cache_stats[-1]
        
        # Calculate trends
        if len(self.cache_stats) > 1:
            recent = list(self.cache_stats)[-10:]
            avg_hit_rate = sum(s.get('hit_rate', 0) for s in recent) / len(recent)
        else:
            avg_hit_rate = latest.get('hit_rate', 0)
        
        return {
            'enabled': latest.get('enabled', True),
            'current_hit_rate': latest.get('hit_rate', 0),
            'avg_hit_rate': avg_hit_rate,
            'total_hits': latest.get('hits', 0),
            'total_misses': latest.get('misses', 0),
            'evictions': latest.get('evictions', 0),
            'size': latest.get('size', 0),
            'max_size': latest.get('max_size', 0)
        }
    
    def get_data_quality_metrics(self, time_window: int = 3600) -> Dict[str, Any]:
        """
        Get data quality metrics.
        
        Args:
            time_window: Time window in seconds
            
        Returns:
            Dictionary with data quality metrics
        """
        cutoff_time = time.time() - time_window
        recent = [d for d in self.data_quality if d['timestamp'] > cutoff_time]
        
        if not recent:
            return {'no_data': True}
        
        avg_score = sum(d['score'] for d in recent) / len(recent)
        
        # Aggregate check results
        check_results = defaultdict(list)
        for d in recent:
            for check, result in d['checks'].items():
                check_results[check].append(result)
        
        check_pass_rates = {
            check: sum(results) / len(results)
            for check, results in check_results.items()
        }
        
        return {
            'avg_quality_score': avg_score,
            'sample_size': len(recent),
            'check_pass_rates': check_pass_rates,
            'latest_score': recent[-1]['score']
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Dictionary with health status
        """
        uptime = time.time() - self.start_time
        
        # Get metrics
        api_metrics = self.get_api_metrics(time_window=300)  # Last 5 minutes
        latency_metrics = self.get_latency_metrics()
        cache_metrics = self.get_cache_metrics()
        quality_metrics = self.get_data_quality_metrics(time_window=300)
        
        # Calculate health score (0-100)
        health_score = 100
        issues = []
        
        # Check API success rate
        for ex, metrics in api_metrics.items():
            if metrics['success_rate'] < 0.95:
                health_score -= 20
                issues.append(f"{ex} success rate low: {metrics['success_rate']:.1%}")
        
        # Check latency
        for ex, metrics in latency_metrics.items():
            if metrics['p95_ms'] > 1000:  # > 1 second
                health_score -= 10
                issues.append(f"{ex} high latency: {metrics['p95_ms']:.0f}ms")
        
        # Check cache
        if cache_metrics.get('enabled') and cache_metrics.get('current_hit_rate', 0) < 0.5:
            health_score -= 10
            issues.append(f"Low cache hit rate: {cache_metrics['current_hit_rate']:.1%}")
        
        # Check data quality
        if not quality_metrics.get('no_data') and quality_metrics.get('avg_quality_score', 1) < 0.9:
            health_score -= 15
            issues.append(f"Data quality issues: {quality_metrics['avg_quality_score']:.1%}")
        
        health_score = max(0, health_score)
        
        # Determine status
        if health_score >= 90:
            status = "HEALTHY"
        elif health_score >= 70:
            status = "DEGRADED"
        else:
            status = "UNHEALTHY"
        
        return {
            'status': status,
            'health_score': health_score,
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600,
            'issues': issues,
            'timestamp': datetime.now().isoformat()
        }
    
    def export_metrics(self, filepath: str):
        """
        Export all metrics to JSON file.
        
        Args:
            filepath: Path to export file
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time() - self.start_time,
            'api_metrics': self.get_api_metrics(),
            'latency_metrics': self.get_latency_metrics(),
            'cache_metrics': self.get_cache_metrics(),
            'data_quality_metrics': self.get_data_quality_metrics(),
            'system_health': self.get_system_health()
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        self.logger.info(f"Metrics exported to {filepath}")
    
    def print_summary(self):
        """Print a summary of current metrics."""
        print("\n" + "="*60)
        print("PERFORMANCE MONITOR SUMMARY")
        print("="*60)
        
        # System health
        health = self.get_system_health()
        print(f"\n🏥 System Health: {health['status']} ({health['health_score']}/100)")
        print(f"   Uptime: {health['uptime_hours']:.1f} hours")
        if health['issues']:
            print("   Issues:")
            for issue in health['issues']:
                print(f"     - {issue}")
        
        # API metrics
        print("\n📡 API Metrics (Last 5 minutes):")
        api_metrics = self.get_api_metrics(time_window=300)
        for ex, metrics in api_metrics.items():
            print(f"   {ex}:")
            print(f"     Calls: {metrics['total_calls']} ({metrics['calls_per_minute']:.1f}/min)")
            print(f"     Success Rate: {metrics['success_rate']:.1%}")
        
        # Latency
        print("\n⚡ Latency Metrics:")
        latency_metrics = self.get_latency_metrics()
        for ex, metrics in latency_metrics.items():
            print(f"   {ex}:")
            print(f"     Avg: {metrics['avg_ms']:.0f}ms | P95: {metrics['p95_ms']:.0f}ms | P99: {metrics['p99_ms']:.0f}ms")
        
        # Cache
        print("\n💾 Cache Metrics:")
        cache_metrics = self.get_cache_metrics()
        if cache_metrics.get('enabled'):
            print(f"   Hit Rate: {cache_metrics['current_hit_rate']:.1%}")
            print(f"   Size: {cache_metrics['size']}/{cache_metrics['max_size']}")
        else:
            print("   Cache disabled")
        
        # Data quality
        print("\n✅ Data Quality:")
        quality_metrics = self.get_data_quality_metrics(time_window=300)
        if not quality_metrics.get('no_data'):
            print(f"   Avg Score: {quality_metrics['avg_quality_score']:.1%}")
        else:
            print("   No data")
        
        print("\n" + "="*60 + "\n")
