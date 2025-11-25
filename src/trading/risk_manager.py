"""
Risk Manager for Paper Trading
Implements position limits, stop-loss, circuit breakers
"""

from typing import Dict, Optional
import logging

class RiskManager:
    """Advanced risk management for paper trading"""
    
    def __init__(self, config: Dict):
        self.max_positions = config.get('max_positions', 5)
        self.max_position_size = config.get('max_position_size', 0.2)  # 20% of capital
        self.daily_loss_limit = config.get('daily_loss_limit', 0.05)  # 5%
        self.max_drawdown = config.get('max_drawdown', 0.15)  # 15%
        self.stop_loss_pct = config.get('stop_loss_pct', 0.03)  # 3%
        self.take_profit_pct = config.get('take_profit_pct', 0.10)  # 10%
        
        self.circuit_breaker_active = False
        self.daily_start_equity = None
        self.logger = logging.getLogger("RiskManager")
    
    def check_can_open_position(self, portfolio, symbol: str, quantity: float, 
                                price: float) -> tuple[bool, str]:
        """
        Check if position can be opened based on risk limits.
        
        Returns:
            (can_open, reason)
        """
        # Check circuit breaker
        if self.circuit_breaker_active:
            return False, "Circuit breaker active"
        
        # Check max positions
        if len(portfolio.positions) >= self.max_positions:
            return False, f"Max positions limit reached ({self.max_positions})"
        
        # Check position size
        position_value = quantity * price
        total_equity = portfolio.get_total_equity()
        position_pct = position_value / total_equity
        
        if position_pct > self.max_position_size:
            return False, f"Position size ({position_pct*100:.1f}%) exceeds limit ({self.max_position_size*100:.1f}%)"
        
        # Check daily loss limit
        if self.daily_start_equity is None:
            self.daily_start_equity = total_equity
        
        daily_return = (total_equity - self.daily_start_equity) / self.daily_start_equity
        if daily_return < -self.daily_loss_limit:
            self.circuit_breaker_active = True
            return False, f"Daily loss limit exceeded ({daily_return*100:.2f}%)"
        
        # Check max drawdown
        if portfolio.max_drawdown < -self.max_drawdown:
            self.circuit_breaker_active = True
            return False, f"Max drawdown exceeded ({portfolio.max_drawdown*100:.2f}%)"
        
        return True, "OK"
    
    def check_stop_loss(self, position, current_price: float) -> bool:
        """Check if stop-loss should trigger"""
        pnl_pct = (current_price - position.entry_price) / position.entry_price
        
        if pnl_pct <= -self.stop_loss_pct:
            self.logger.warning(f"Stop-loss triggered for {position.symbol}: {pnl_pct*100:.2f}%")
            return True
        
        return False
    
    def check_take_profit(self, position, current_price: float) -> bool:
        """Check if take-profit should trigger"""
        pnl_pct = (current_price - position.entry_price) / position.entry_price
        
        if pnl_pct >= self.take_profit_pct:
            self.logger.info(f"Take-profit triggered for {position.symbol}: {pnl_pct*100:.2f}%")
            return True
        
        return False
    
    def reset_daily_limits(self, current_equity: float):
        """Reset daily limits (call at start of new day)"""
        self.daily_start_equity = current_equity
        self.circuit_breaker_active = False
        self.logger.info("Daily risk limits reset")
    
    def get_risk_status(self, portfolio) -> Dict:
        """Get current risk status"""
        total_equity = portfolio.get_total_equity()
        
        daily_pnl = 0
        if self.daily_start_equity:
            daily_pnl = (total_equity - self.daily_start_equity) / self.daily_start_equity
        
        return {
            'circuit_breaker_active': self.circuit_breaker_active,
            'active_positions': len(portfolio.positions),
            'max_positions': self.max_positions,
            'daily_pnl': daily_pnl,
            'daily_loss_limit': -self.daily_loss_limit,
            'max_drawdown': portfolio.max_drawdown,
            'max_drawdown_limit': -self.max_drawdown
        }
