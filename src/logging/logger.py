"""
Production Logging Configuration
Structured logging with rotation and multiple handlers
"""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def setup_logging(
    log_level: str = 'INFO',
    log_file: str = 'logs/intradyne.log',
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_json: bool = False
):
    """
    Configure production logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        enable_console: Enable console logging
        enable_json: Enable JSON structured logging
    """
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    if enable_json:
        file_handler.setFormatter(StructuredFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    root_logger.addHandler(file_handler)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter(
            '%(levelname)s - %(name)s - %(message)s'
        ))
        root_logger.addHandler(console_handler)
    
    # Log startup
    logging.info(f"Logging configured: level={log_level}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class MetricsLogger:
    """Log metrics for monitoring"""
    
    def __init__(self):
        self.logger = get_logger("Metrics")
        self.metrics_file = Path('logs/metrics.jsonl')
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """
        Log a metric.
        
        Args:
            metric_name: Metric name
            value: Metric value
            tags: Optional tags
        """
        metric_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'metric': metric_name,
            'value': value,
            'tags': tags or {}
        }
        
        # Append to metrics file
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(metric_data) + '\n')
        
        self.logger.debug(f"Metric: {metric_name}={value}")
    
    def log_trade(self, trade_data: Dict[str, Any]):
        """Log trade execution"""
        self.log_metric('trade_executed', 1, {
            'symbol': trade_data.get('symbol'),
            'side': trade_data.get('side'),
            'price': str(trade_data.get('price'))
        })
    
    def log_performance(self, equity: float, pnl: float, sharpe: float = None):
        """Log performance metrics"""
        self.log_metric('portfolio_equity', equity)
        self.log_metric('portfolio_pnl', pnl)
        
        if sharpe is not None:
            self.log_metric('sharpe_ratio', sharpe)
    
    def log_health(self, health_score: float, status: str):
        """Log system health"""
        self.log_metric('health_score', health_score, {'status': status})


# Global metrics logger
_metrics_logger: MetricsLogger = None

def get_metrics_logger() -> MetricsLogger:
    """Get global metrics logger"""
    global _metrics_logger
    
    if _metrics_logger is None:
        _metrics_logger = MetricsLogger()
    
    return _metrics_logger
