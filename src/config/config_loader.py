"""
Configuration Management System
Loads and validates configuration from YAML files and environment variables
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

class ConfigLoader:
    """Load and manage configuration"""
    
    def __init__(self, environment: str = None):
        """
        Initialize configuration loader.
        
        Args:
            environment: Environment name (development, staging, production)
        """
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.config_dir = Path(__file__).parent.parent / 'config'
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger("ConfigLoader")
        
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        config_file = self.config_dir / f'{self.environment}.yaml'
        
        if not config_file.exists():
            self.logger.warning(f"Config file not found: {config_file}")
            config_file = self.config_dir / 'development.yaml'
        
        try:
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
            
            self.logger.info(f"Loaded config from {config_file}")
            
            # Override with environment variables
            self._load_env_overrides()
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise
    
    def _load_env_overrides(self):
        """Override config with environment variables"""
        # Trading
        if os.getenv('INITIAL_CAPITAL'):
            self.config['trading']['initial_capital'] = float(os.getenv('INITIAL_CAPITAL'))
        
        if os.getenv('SYMBOLS'):
            self.config['trading']['symbols'] = os.getenv('SYMBOLS').split(',')
        
        if os.getenv('UPDATE_INTERVAL'):
            self.config['trading']['update_interval'] = int(os.getenv('UPDATE_INTERVAL'))
        
        # Exchange
        if os.getenv('EXCHANGE_NAME'):
            self.config['exchange']['name'] = os.getenv('EXCHANGE_NAME')
        
        # Risk Management
        if os.getenv('MAX_POSITIONS'):
            self.config['risk_management']['max_positions'] = int(os.getenv('MAX_POSITIONS'))
        
        if os.getenv('STOP_LOSS_PCT'):
            self.config['risk_management']['stop_loss_pct'] = float(os.getenv('STOP_LOSS_PCT'))
        
        if os.getenv('TAKE_PROFIT_PCT'):
            self.config['risk_management']['take_profit_pct'] = float(os.getenv('TAKE_PROFIT_PCT'))
        
        # Logging
        if os.getenv('LOG_LEVEL'):
            self.config['logging']['level'] = os.getenv('LOG_LEVEL')
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot notation key.
        
        Args:
            key: Dot notation key (e.g., 'trading.initial_capital')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_trading_config(self) -> Dict:
        """Get trading configuration"""
        return self.config.get('trading', {})
    
    def get_exchange_config(self) -> Dict:
        """Get exchange configuration"""
        config = self.config.get('exchange', {})
        
        # Add API keys from environment
        config['api_key'] = os.getenv('EXCHANGE_API_KEY', '')
        config['secret'] = os.getenv('EXCHANGE_SECRET', '')
        config['password'] = os.getenv('EXCHANGE_PASSWORD', '')
        
        return config
    
    def get_risk_config(self) -> Dict:
        """Get risk management configuration"""
        return self.config.get('risk_management', {})
    
    def get_monitoring_config(self) -> Dict:
        """Get monitoring configuration"""
        return self.config.get('monitoring', {})
    
    def get_logging_config(self) -> Dict:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def validate(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if valid, raises exception otherwise
        """
        required_keys = [
            'trading.initial_capital',
            'trading.symbols',
            'exchange.name',
            'risk_management.max_positions'
        ]
        
        for key in required_keys:
            value = self.get(key)
            if value is None:
                raise ValueError(f"Missing required config: {key}")
        
        # Validate ranges
        if self.get('trading.initial_capital') <= 0:
            raise ValueError("initial_capital must be positive")
        
        if self.get('risk_management.max_positions') <= 0:
            raise ValueError("max_positions must be positive")
        
        if not 0 < self.get('risk_management.stop_loss_pct') < 1:
            raise ValueError("stop_loss_pct must be between 0 and 1")
        
        self.logger.info("Configuration validated successfully")
        return True
    
    def print_config(self):
        """Print current configuration (hiding secrets)"""
        print("\n" + "="*70)
        print(f"CONFIGURATION ({self.environment.upper()})")
        print("="*70)
        
        # Trading
        print("\n📊 Trading:")
        trading = self.get_trading_config()
        print(f"   Mode: {trading.get('mode')}")
        print(f"   Capital: ${trading.get('initial_capital'):,}")
        print(f"   Symbols: {', '.join(trading.get('symbols', []))}")
        print(f"   Update Interval: {trading.get('update_interval')}s")
        
        # Exchange
        print("\n🔌 Exchange:")
        exchange = self.get_exchange_config()
        print(f"   Name: {exchange.get('name')}")
        print(f"   API Key: {'***' if exchange.get('api_key') else 'Not set'}")
        
        # Risk
        print("\n🛡️  Risk Management:")
        risk = self.get_risk_config()
        print(f"   Max Positions: {risk.get('max_positions')}")
        print(f"   Stop Loss: {risk.get('stop_loss_pct')*100:.1f}%")
        print(f"   Take Profit: {risk.get('take_profit_pct')*100:.1f}%")
        print(f"   Daily Loss Limit: {risk.get('daily_loss_limit')*100:.1f}%")
        
        # Monitoring
        print("\n📈 Monitoring:")
        monitoring = self.get_monitoring_config()
        drift = monitoring.get('drift_detection', {})
        print(f"   Drift Detection: {'✅' if drift.get('enabled') else '❌'}")
        print(f"   Health Metrics: {'✅' if monitoring.get('health_metrics', {}).get('enabled') else '❌'}")
        
        print("\n" + "="*70)


# Global config instance
_config: Optional[ConfigLoader] = None

def get_config(environment: str = None) -> ConfigLoader:
    """
    Get global configuration instance.
    
    Args:
        environment: Environment name
    
    Returns:
        ConfigLoader instance
    """
    global _config
    
    if _config is None:
        _config = ConfigLoader(environment)
    
    return _config


def reload_config(environment: str = None):
    """Reload configuration"""
    global _config
    _config = ConfigLoader(environment)
    return _config
