"""
Rule and Policy Engine
Deterministic rules for trading governance and compliance
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, time
import logging

class Rule:
    """Base class for trading rules"""
    
    def __init__(self, name: str, description: str, severity: str = 'WARNING'):
        self.name = name
        self.description = description
        self.severity = severity  # INFO, WARNING, ERROR, CRITICAL
        self.enabled = True
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        """
        Evaluate rule against context.
        
        Returns:
            (passed, message)
        """
        raise NotImplementedError


class PolicyEngine:
    """
    Deterministic policy engine for trading governance.
    Enforces rules before allowing trades.
    """
    
    def __init__(self):
        self.rules: List[Rule] = []
        self.policies: Dict[str, Any] = {}
        self.logger = logging.getLogger("PolicyEngine")
        self.violations_log = []
    
    def add_rule(self, rule: Rule):
        """Add a rule to the engine"""
        self.rules.append(rule)
        self.logger.info(f"Added rule: {rule.name}")
    
    def set_policy(self, key: str, value: Any):
        """Set a policy parameter"""
        self.policies[key] = value
        self.logger.info(f"Set policy: {key} = {value}")
    
    def evaluate_all(self, context: Dict) -> tuple[bool, List[Dict]]:
        """
        Evaluate all rules.
        
        Returns:
            (all_passed, violations)
        """
        violations = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                passed, message = rule.evaluate(context)
                
                if not passed:
                    violation = {
                        'rule': rule.name,
                        'severity': rule.severity,
                        'message': message,
                        'timestamp': datetime.now()
                    }
                    violations.append(violation)
                    self.violations_log.append(violation)
                    
                    if rule.severity in ['ERROR', 'CRITICAL']:
                        self.logger.error(f"Rule violation: {rule.name} - {message}")
                    else:
                        self.logger.warning(f"Rule violation: {rule.name} - {message}")
            
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.name}: {e}")
        
        all_passed = len(violations) == 0
        return all_passed, violations
    
    def can_trade(self, context: Dict) -> tuple[bool, str]:
        """
        Check if trading is allowed.
        
        Returns:
            (allowed, reason)
        """
        all_passed, violations = self.evaluate_all(context)
        
        if not all_passed:
            # Check for critical violations
            critical = [v for v in violations if v['severity'] == 'CRITICAL']
            if critical:
                return False, f"Critical violation: {critical[0]['message']}"
            
            # Check for errors
            errors = [v for v in violations if v['severity'] == 'ERROR']
            if errors:
                return False, f"Error: {errors[0]['message']}"
            
            # Warnings don't block trading
            return True, f"Trading allowed with {len(violations)} warning(s)"
        
        return True, "All rules passed"


# ============================================================================
# Predefined Rules
# ============================================================================

class TradingHoursRule(Rule):
    """Only allow trading during specific hours"""
    
    def __init__(self, start_hour: int = 0, end_hour: int = 24):
        super().__init__(
            "TradingHours",
            f"Trading only allowed between {start_hour}:00 and {end_hour}:00",
            severity='ERROR'
        )
        self.start_hour = start_hour
        self.end_hour = end_hour
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        current_hour = datetime.now().hour
        
        if self.start_hour <= current_hour < self.end_hour:
            return True, "Within trading hours"
        
        return False, f"Outside trading hours ({current_hour}:00)"


class MaxPositionsRule(Rule):
    """Limit maximum number of positions"""
    
    def __init__(self, max_positions: int = 5):
        super().__init__(
            "MaxPositions",
            f"Maximum {max_positions} positions allowed",
            severity='ERROR'
        )
        self.max_positions = max_positions
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        current_positions = context.get('active_positions', 0)
        
        if current_positions < self.max_positions:
            return True, f"Positions: {current_positions}/{self.max_positions}"
        
        return False, f"Max positions reached ({current_positions}/{self.max_positions})"


class MinimumCapitalRule(Rule):
    """Require minimum capital to trade"""
    
    def __init__(self, min_capital: float = 1000):
        super().__init__(
            "MinimumCapital",
            f"Minimum ${min_capital} capital required",
            severity='CRITICAL'
        )
        self.min_capital = min_capital
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        current_capital = context.get('equity', 0)
        
        if current_capital >= self.min_capital:
            return True, f"Capital: ${current_capital:,.2f}"
        
        return False, f"Insufficient capital (${current_capital:,.2f} < ${self.min_capital:,.2f})"


class MaxDrawdownRule(Rule):
    """Stop trading if drawdown exceeds limit"""
    
    def __init__(self, max_drawdown: float = 0.20):
        super().__init__(
            "MaxDrawdown",
            f"Maximum {max_drawdown*100}% drawdown allowed",
            severity='CRITICAL'
        )
        self.max_drawdown = max_drawdown
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        current_drawdown = abs(context.get('max_drawdown', 0))
        
        if current_drawdown <= self.max_drawdown:
            return True, f"Drawdown: {current_drawdown*100:.2f}%"
        
        return False, f"Max drawdown exceeded ({current_drawdown*100:.2f}% > {self.max_drawdown*100:.2f}%)"


class DailyLossLimitRule(Rule):
    """Stop trading if daily loss exceeds limit"""
    
    def __init__(self, max_daily_loss: float = 0.05):
        super().__init__(
            "DailyLossLimit",
            f"Maximum {max_daily_loss*100}% daily loss allowed",
            severity='ERROR'
        )
        self.max_daily_loss = max_daily_loss
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        daily_pnl = context.get('daily_pnl', 0)
        
        if daily_pnl >= -self.max_daily_loss:
            return True, f"Daily P&L: {daily_pnl*100:+.2f}%"
        
        return False, f"Daily loss limit exceeded ({daily_pnl*100:.2f}% < {-self.max_daily_loss*100:.2f}%)"


class PositionSizeRule(Rule):
    """Limit position size as percentage of capital"""
    
    def __init__(self, max_position_pct: float = 0.20):
        super().__init__(
            "PositionSize",
            f"Maximum {max_position_pct*100}% of capital per position",
            severity='ERROR'
        )
        self.max_position_pct = max_position_pct
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        position_value = context.get('position_value', 0)
        equity = context.get('equity', 1)
        
        position_pct = position_value / equity if equity > 0 else 0
        
        if position_pct <= self.max_position_pct:
            return True, f"Position size: {position_pct*100:.1f}%"
        
        return False, f"Position too large ({position_pct*100:.1f}% > {self.max_position_pct*100:.1f}%)"


class VolatilityRule(Rule):
    """Reduce trading during high volatility"""
    
    def __init__(self, max_volatility: float = 0.05):
        super().__init__(
            "Volatility",
            f"Maximum {max_volatility*100}% volatility allowed",
            severity='WARNING'
        )
        self.max_volatility = max_volatility
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        volatility = context.get('volatility', 0)
        
        if volatility <= self.max_volatility:
            return True, f"Volatility: {volatility*100:.2f}%"
        
        return False, f"High volatility ({volatility*100:.2f}% > {self.max_volatility*100:.2f}%)"


class MinimumLiquidityRule(Rule):
    """Require minimum liquidity to trade"""
    
    def __init__(self, min_volume: float = 1000000):
        super().__init__(
            "MinimumLiquidity",
            f"Minimum ${min_volume:,.0f} daily volume required",
            severity='WARNING'
        )
        self.min_volume = min_volume
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        volume = context.get('volume', 0)
        
        if volume >= self.min_volume:
            return True, f"Volume: ${volume:,.0f}"
        
        return False, f"Low liquidity (${volume:,.0f} < ${self.min_volume:,.0f})"


class ConsecutiveLossesRule(Rule):
    """Stop after consecutive losses"""
    
    def __init__(self, max_consecutive_losses: int = 5):
        super().__init__(
            "ConsecutiveLosses",
            f"Stop after {max_consecutive_losses} consecutive losses",
            severity='ERROR'
        )
        self.max_consecutive_losses = max_consecutive_losses
    
    def evaluate(self, context: Dict) -> tuple[bool, str]:
        consecutive_losses = context.get('consecutive_losses', 0)
        
        if consecutive_losses < self.max_consecutive_losses:
            return True, f"Consecutive losses: {consecutive_losses}"
        
        return False, f"Too many consecutive losses ({consecutive_losses})"


# ============================================================================
# Policy Presets
# ============================================================================

def create_conservative_policy() -> PolicyEngine:
    """Create conservative policy engine"""
    engine = PolicyEngine()
    
    # Add rules
    engine.add_rule(TradingHoursRule(start_hour=9, end_hour=16))  # 9 AM - 4 PM
    engine.add_rule(MaxPositionsRule(max_positions=3))
    engine.add_rule(MinimumCapitalRule(min_capital=5000))
    engine.add_rule(MaxDrawdownRule(max_drawdown=0.10))  # 10%
    engine.add_rule(DailyLossLimitRule(max_daily_loss=0.02))  # 2%
    engine.add_rule(PositionSizeRule(max_position_pct=0.10))  # 10%
    engine.add_rule(ConsecutiveLossesRule(max_consecutive_losses=3))
    
    return engine


def create_moderate_policy() -> PolicyEngine:
    """Create moderate policy engine"""
    engine = PolicyEngine()
    
    engine.add_rule(MaxPositionsRule(max_positions=5))
    engine.add_rule(MinimumCapitalRule(min_capital=1000))
    engine.add_rule(MaxDrawdownRule(max_drawdown=0.15))  # 15%
    engine.add_rule(DailyLossLimitRule(max_daily_loss=0.05))  # 5%
    engine.add_rule(PositionSizeRule(max_position_pct=0.20))  # 20%
    engine.add_rule(ConsecutiveLossesRule(max_consecutive_losses=5))
    
    return engine


def create_aggressive_policy() -> PolicyEngine:
    """Create aggressive policy engine"""
    engine = PolicyEngine()
    
    engine.add_rule(MaxPositionsRule(max_positions=10))
    engine.add_rule(MinimumCapitalRule(min_capital=500))
    engine.add_rule(MaxDrawdownRule(max_drawdown=0.25))  # 25%
    engine.add_rule(DailyLossLimitRule(max_daily_loss=0.10))  # 10%
    engine.add_rule(PositionSizeRule(max_position_pct=0.30))  # 30%
    
    return engine
