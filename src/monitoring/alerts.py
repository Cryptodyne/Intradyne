import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertSystem:
    """
    Alert system for monitoring and notifying about critical events.
    """
    
    def __init__(self):
        """Initialize the alert system."""
        self.logger = logging.getLogger("AlertSystem")
        self.alert_handlers = []
        self.alert_history = []
        self.max_history = 1000
        
        # Alert thresholds
        self.thresholds = {
            'api_success_rate': 0.95,
            'latency_p95_ms': 1000,
            'cache_hit_rate': 0.50,
            'data_quality_score': 0.90,
            'health_score': 70
        }
    
    def add_handler(self, handler: Callable):
        """
        Add an alert handler function.
        
        Args:
            handler: Function that takes (level, title, message, data)
        """
        self.alert_handlers.append(handler)
        self.logger.info(f"Added alert handler: {handler.__name__}")
    
    def send_alert(self, level: AlertLevel, title: str, message: str, 
                   data: Optional[Dict[str, Any]] = None):
        """
        Send an alert.
        
        Args:
            level: Alert severity level
            title: Alert title
            message: Alert message
            data: Additional data
        """
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level.value,
            'title': title,
            'message': message,
            'data': data or {}
        }
        
        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        # Log
        log_msg = f"[{level.value.upper()}] {title}: {message}"
        if level == AlertLevel.CRITICAL:
            self.logger.critical(log_msg)
        elif level == AlertLevel.ERROR:
            self.logger.error(log_msg)
        elif level == AlertLevel.WARNING:
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)
        
        # Call handlers
        for handler in self.alert_handlers:
            try:
                handler(level, title, message, data)
            except Exception as e:
                self.logger.error(f"Alert handler {handler.__name__} failed: {e}")
    
    def check_api_metrics(self, metrics: Dict[str, Any]):
        """Check API metrics and send alerts if needed."""
        for exchange, data in metrics.items():
            success_rate = data.get('success_rate', 1.0)
            
            if success_rate < self.thresholds['api_success_rate']:
                self.send_alert(
                    AlertLevel.ERROR,
                    f"{exchange} API Success Rate Low",
                    f"Success rate: {success_rate:.1%} (threshold: {self.thresholds['api_success_rate']:.1%})",
                    {'exchange': exchange, 'success_rate': success_rate}
                )
    
    def check_latency_metrics(self, metrics: Dict[str, Any]):
        """Check latency metrics and send alerts if needed."""
        for exchange, data in metrics.items():
            p95_ms = data.get('p95_ms', 0)
            
            if p95_ms > self.thresholds['latency_p95_ms']:
                self.send_alert(
                    AlertLevel.WARNING,
                    f"{exchange} High Latency",
                    f"P95 latency: {p95_ms:.0f}ms (threshold: {self.thresholds['latency_p95_ms']}ms)",
                    {'exchange': exchange, 'p95_ms': p95_ms}
                )
    
    def check_cache_metrics(self, metrics: Dict[str, Any]):
        """Check cache metrics and send alerts if needed."""
        if not metrics.get('enabled'):
            return
        
        hit_rate = metrics.get('current_hit_rate', 0)
        
        if hit_rate < self.thresholds['cache_hit_rate']:
            self.send_alert(
                AlertLevel.WARNING,
                "Low Cache Hit Rate",
                f"Hit rate: {hit_rate:.1%} (threshold: {self.thresholds['cache_hit_rate']:.1%})",
                {'hit_rate': hit_rate}
            )
    
    def check_data_quality(self, metrics: Dict[str, Any]):
        """Check data quality metrics and send alerts if needed."""
        if metrics.get('no_data'):
            return
        
        score = metrics.get('avg_quality_score', 1.0)
        
        if score < self.thresholds['data_quality_score']:
            self.send_alert(
                AlertLevel.ERROR,
                "Data Quality Issues",
                f"Quality score: {score:.1%} (threshold: {self.thresholds['data_quality_score']:.1%})",
                {'quality_score': score}
            )
    
    def check_system_health(self, health: Dict[str, Any]):
        """Check system health and send alerts if needed."""
        health_score = health.get('health_score', 100)
        status = health.get('status', 'UNKNOWN')
        
        if health_score < self.thresholds['health_score']:
            level = AlertLevel.CRITICAL if health_score < 50 else AlertLevel.ERROR
            
            self.send_alert(
                level,
                f"System Health {status}",
                f"Health score: {health_score}/100 (threshold: {self.thresholds['health_score']})",
                {
                    'health_score': health_score,
                    'status': status,
                    'issues': health.get('issues', [])
                }
            )
    
    def get_recent_alerts(self, count: int = 10, level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """
        Get recent alerts.
        
        Args:
            count: Number of alerts to return
            level: Filter by alert level
            
        Returns:
            List of recent alerts
        """
        alerts = self.alert_history
        
        if level:
            alerts = [a for a in alerts if a['level'] == level.value]
        
        return alerts[-count:]
    
    def clear_history(self):
        """Clear alert history."""
        self.alert_history.clear()
        self.logger.info("Alert history cleared")


# Built-in alert handlers

def console_alert_handler(level: AlertLevel, title: str, message: str, data: Dict[str, Any]):
    """Print alerts to console."""
    emoji = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨"
    }
    
    print(f"\n{emoji.get(level, '📢')} [{level.value.upper()}] {title}")
    print(f"   {message}")
    if data:
        print(f"   Data: {data}")

def file_alert_handler(filepath: str = "data/logs/alerts.log"):
    """Create a file alert handler."""
    import os
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    def handler(level: AlertLevel, title: str, message: str, data: Dict[str, Any]):
        with open(filepath, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] [{level.value.upper()}] {title}: {message}\n")
            if data:
                f.write(f"  Data: {data}\n")
    
    return handler
