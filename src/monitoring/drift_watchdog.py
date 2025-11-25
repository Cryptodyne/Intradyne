"""
Drift Watchdog and Health Metrics
Monitors strategy performance drift and system health
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import numpy as np
import logging

class DriftWatchdog:
    """
    Monitors strategy performance for drift/degradation.
    Detects when strategy stops working as expected.
    """
    
    def __init__(self, baseline_sharpe: float = 1.5, 
                 baseline_win_rate: float = 0.55,
                 lookback_trades: int = 50):
        """
        Initialize drift watchdog.
        
        Args:
            baseline_sharpe: Expected Sharpe ratio
            baseline_win_rate: Expected win rate
            lookback_trades: Number of recent trades to analyze
        """
        self.baseline_sharpe = baseline_sharpe
        self.baseline_win_rate = baseline_win_rate
        self.lookback_trades = lookback_trades
        
        self.recent_trades = deque(maxlen=lookback_trades)
        self.logger = logging.getLogger("DriftWatchdog")
        
        # Drift thresholds
        self.sharpe_drift_threshold = 0.5  # 50% degradation
        self.win_rate_drift_threshold = 0.10  # 10% absolute drop
        
        self.drift_detected = False
        self.drift_reason = None
    
    def add_trade(self, trade: Dict):
        """Add trade to monitoring"""
        self.recent_trades.append(trade)
        
        # Check for drift after minimum trades
        if len(self.recent_trades) >= min(20, self.lookback_trades):
            self.check_drift()
    
    def check_drift(self) -> bool:
        """
        Check if performance drift detected.
        
        Returns:
            True if drift detected
        """
        if len(self.recent_trades) < 10:
            return False
        
        # Calculate recent metrics
        recent_metrics = self._calculate_recent_metrics()
        
        # Check Sharpe ratio drift
        sharpe_degradation = (self.baseline_sharpe - recent_metrics['sharpe']) / self.baseline_sharpe
        
        if sharpe_degradation > self.sharpe_drift_threshold:
            self.drift_detected = True
            self.drift_reason = f"Sharpe ratio degraded {sharpe_degradation*100:.1f}% ({recent_metrics['sharpe']:.2f} vs {self.baseline_sharpe:.2f})"
            self.logger.warning(f"DRIFT DETECTED: {self.drift_reason}")
            return True
        
        # Check win rate drift
        win_rate_drop = self.baseline_win_rate - recent_metrics['win_rate']
        
        if win_rate_drop > self.win_rate_drift_threshold:
            self.drift_detected = True
            self.drift_reason = f"Win rate dropped {win_rate_drop*100:.1f}% ({recent_metrics['win_rate']*100:.1f}% vs {self.baseline_win_rate*100:.1f}%)"
            self.logger.warning(f"DRIFT DETECTED: {self.drift_reason}")
            return True
        
        # No drift
        self.drift_detected = False
        self.drift_reason = None
        return False
    
    def _calculate_recent_metrics(self) -> Dict:
        """Calculate metrics from recent trades"""
        trades = list(self.recent_trades)
        
        # Win rate
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        # Returns for Sharpe
        returns = [t.get('pnl_pct', 0) for t in trades]
        
        # Sharpe ratio (simplified)
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe = 0
        
        return {
            'win_rate': win_rate,
            'sharpe': sharpe,
            'avg_return': np.mean(returns) if returns else 0,
            'trades_count': len(trades)
        }
    
    def get_status(self) -> Dict:
        """Get drift status"""
        recent_metrics = self._calculate_recent_metrics() if len(self.recent_trades) >= 10 else {}
        
        return {
            'drift_detected': self.drift_detected,
            'drift_reason': self.drift_reason,
            'recent_trades': len(self.recent_trades),
            'recent_sharpe': recent_metrics.get('sharpe', 0),
            'recent_win_rate': recent_metrics.get('win_rate', 0),
            'baseline_sharpe': self.baseline_sharpe,
            'baseline_win_rate': self.baseline_win_rate
        }


class HealthMetrics:
    """
    System health monitoring.
    Tracks uptime, errors, latency, and overall health.
    """
    
    def __init__(self):
        self.start_time = datetime.now()
        self.last_update = datetime.now()
        
        # Counters
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_signals = 0
        self.total_errors = 0
        
        # Latency tracking
        self.latency_samples = deque(maxlen=100)
        
        # Health score components
        self.uptime_score = 100
        self.error_score = 100
        self.latency_score = 100
        self.performance_score = 100
        
        self.logger = logging.getLogger("HealthMetrics")
    
    def record_trade(self, success: bool = True):
        """Record trade execution"""
        self.total_trades += 1
        if success:
            self.successful_trades += 1
        else:
            self.failed_trades += 1
        
        self.last_update = datetime.now()
        self._update_health()
    
    def record_signal(self):
        """Record signal generation"""
        self.total_signals += 1
        self.last_update = datetime.now()
    
    def record_error(self, error_type: str = "general"):
        """Record error occurrence"""
        self.total_errors += 1
        self.logger.warning(f"Error recorded: {error_type}")
        self._update_health()
    
    def record_latency(self, latency_ms: float):
        """Record operation latency"""
        self.latency_samples.append(latency_ms)
        self._update_health()
    
    def _update_health(self):
        """Update health scores"""
        # Error score (100 = no errors)
        if self.total_trades > 0:
            error_rate = self.total_errors / self.total_trades
            self.error_score = max(0, 100 - (error_rate * 100))
        
        # Latency score (100 = < 100ms avg)
        if self.latency_samples:
            avg_latency = np.mean(self.latency_samples)
            if avg_latency < 100:
                self.latency_score = 100
            elif avg_latency < 500:
                self.latency_score = 80
            elif avg_latency < 1000:
                self.latency_score = 60
            else:
                self.latency_score = 40
        
        # Performance score (based on success rate)
        if self.total_trades > 0:
            success_rate = self.successful_trades / self.total_trades
            self.performance_score = success_rate * 100
    
    def get_health_score(self) -> float:
        """
        Calculate overall health score (0-100).
        
        Returns:
            Health score
        """
        # Weighted average
        weights = {
            'uptime': 0.2,
            'error': 0.3,
            'latency': 0.2,
            'performance': 0.3
        }
        
        score = (
            self.uptime_score * weights['uptime'] +
            self.error_score * weights['error'] +
            self.latency_score * weights['latency'] +
            self.performance_score * weights['performance']
        )
        
        return round(score, 2)
    
    def get_uptime(self) -> timedelta:
        """Get system uptime"""
        return datetime.now() - self.start_time
    
    def get_status(self) -> Dict:
        """Get comprehensive health status"""
        uptime = self.get_uptime()
        health_score = self.get_health_score()
        
        # Determine health status
        if health_score >= 90:
            status = "EXCELLENT"
            emoji = "🟢"
        elif health_score >= 75:
            status = "GOOD"
            emoji = "🟡"
        elif health_score >= 50:
            status = "FAIR"
            emoji = "🟠"
        else:
            status = "POOR"
            emoji = "🔴"
        
        return {
            'health_score': health_score,
            'status': status,
            'emoji': emoji,
            'uptime': str(uptime),
            'uptime_seconds': uptime.total_seconds(),
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'failed_trades': self.failed_trades,
            'success_rate': self.successful_trades / self.total_trades if self.total_trades > 0 else 0,
            'total_signals': self.total_signals,
            'total_errors': self.total_errors,
            'error_rate': self.total_errors / self.total_trades if self.total_trades > 0 else 0,
            'avg_latency': np.mean(self.latency_samples) if self.latency_samples else 0,
            'scores': {
                'uptime': self.uptime_score,
                'error': self.error_score,
                'latency': self.latency_score,
                'performance': self.performance_score
            }
        }
    
    def print_status(self):
        """Print health status"""
        status = self.get_status()
        
        print(f"\n{status['emoji']} System Health: {status['status']} ({status['health_score']}/100)")
        print(f"   Uptime: {status['uptime']}")
        print(f"   Trades: {status['total_trades']} ({status['success_rate']*100:.1f}% success)")
        print(f"   Errors: {status['total_errors']} ({status['error_rate']*100:.1f}% rate)")
        print(f"   Avg Latency: {status['avg_latency']:.1f}ms")


class CompactMonitor:
    """
    Compact monitoring combining drift detection and health metrics.
    Single interface for all monitoring needs.
    """
    
    def __init__(self, baseline_sharpe: float = 1.5, baseline_win_rate: float = 0.55):
        self.drift_watchdog = DriftWatchdog(baseline_sharpe, baseline_win_rate)
        self.health_metrics = HealthMetrics()
        self.logger = logging.getLogger("CompactMonitor")
    
    def record_trade(self, trade: Dict, success: bool = True):
        """Record trade in both systems"""
        self.drift_watchdog.add_trade(trade)
        self.health_metrics.record_trade(success)
    
    def record_signal(self):
        """Record signal generation"""
        self.health_metrics.record_signal()
    
    def record_error(self, error_type: str = "general"):
        """Record error"""
        self.health_metrics.record_error(error_type)
    
    def get_status(self) -> Dict:
        """Get combined status"""
        drift_status = self.drift_watchdog.get_status()
        health_status = self.health_metrics.get_status()
        
        return {
            'drift': drift_status,
            'health': health_status,
            'timestamp': datetime.now().isoformat()
        }
    
    def print_status(self):
        """Print compact status"""
        status = self.get_status()
        
        print("\n" + "="*60)
        print("SYSTEM MONITOR")
        print("="*60)
        
        # Health
        health = status['health']
        print(f"\n{health['emoji']} Health: {health['status']} ({health['health_score']}/100)")
        print(f"   Uptime: {health['uptime']}")
        print(f"   Trades: {health['total_trades']} ({health['success_rate']*100:.1f}% success)")
        
        # Drift
        drift = status['drift']
        if drift['drift_detected']:
            print(f"\n⚠️  DRIFT DETECTED!")
            print(f"   {drift['drift_reason']}")
        else:
            print(f"\n✅ No Drift Detected")
            print(f"   Recent Sharpe: {drift['recent_sharpe']:.2f} (baseline: {drift['baseline_sharpe']:.2f})")
            print(f"   Recent Win Rate: {drift['recent_win_rate']*100:.1f}% (baseline: {drift['baseline_win_rate']*100:.1f}%)")
        
        print("="*60)
