"""
Portfolio Manager for Paper Trading
Manages virtual positions, cash, and P&L tracking
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

class Position:
    """Represents a trading position"""
    
    def __init__(self, symbol: str, quantity: float, entry_price: float, 
                 timestamp: datetime):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_timestamp = timestamp
        self.current_price = entry_price
        self.unrealized_pnl = 0.0
        self.stop_loss = None
        self.take_profit = None
    
    def update_price(self, current_price: float):
        """Update current price and unrealized P&L"""
        self.current_price = current_price
        self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
    
    def get_value(self) -> float:
        """Get current position value"""
        return self.current_price * self.quantity
    
    def get_pnl_pct(self) -> float:
        """Get P&L percentage"""
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price


class PortfolioManager:
    """Manages virtual portfolio for paper trading"""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_trades = []
        self.logger = logging.getLogger("PortfolioManager")
        
        # Performance tracking
        self.total_pnl = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0
    
    def get_total_equity(self) -> float:
        """Calculate total portfolio equity"""
        positions_value = sum(pos.get_value() for pos in self.positions.values())
        return self.cash + positions_value
    
    def get_available_cash(self) -> float:
        """Get available cash for trading"""
        return self.cash
    
    def can_open_position(self, symbol: str, quantity: float, price: float) -> bool:
        """Check if position can be opened"""
        required_capital = quantity * price
        return self.cash >= required_capital
    
    def open_position(self, symbol: str, quantity: float, price: float, 
                     commission: float = 0.001) -> bool:
        """Open a new position"""
        if symbol in self.positions:
            self.logger.warning(f"Position already exists for {symbol}")
            return False
        
        cost = quantity * price
        commission_cost = cost * commission
        total_cost = cost + commission_cost
        
        if not self.can_open_position(symbol, quantity, price):
            self.logger.warning(f"Insufficient cash to open position: {symbol}")
            return False
        
        # Create position
        position = Position(symbol, quantity, price, datetime.now())
        self.positions[symbol] = position
        
        # Update cash
        self.cash -= total_cost
        
        self.logger.info(f"Opened position: {symbol} x{quantity} @ ${price:.2f}")
        return True
    
    def close_position(self, symbol: str, price: float, 
                      commission: float = 0.001) -> Optional[Dict]:
        """Close an existing position"""
        if symbol not in self.positions:
            self.logger.warning(f"No position to close for {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Calculate proceeds
        proceeds = position.quantity * price
        commission_cost = proceeds * commission
        net_proceeds = proceeds - commission_cost
        
        # Calculate P&L
        pnl = net_proceeds - (position.quantity * position.entry_price)
        pnl_pct = pnl / (position.quantity * position.entry_price)
        
        # Update cash
        self.cash += net_proceeds
        
        # Record trade
        trade = {
            'symbol': symbol,
            'quantity': position.quantity,
            'entry_price': position.entry_price,
            'exit_price': price,
            'entry_time': position.entry_timestamp,
            'exit_time': datetime.now(),
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'commission': commission_cost * 2  # Entry + exit
        }
        
        self.closed_trades.append(trade)
        self.realized_pnl += pnl
        
        # Remove position
        del self.positions[symbol]
        
        self.logger.info(f"Closed position: {symbol} P&L: ${pnl:.2f} ({pnl_pct*100:.2f}%)")
        
        return trade
    
    def update_positions(self, prices: Dict[str, float]):
        """Update all positions with current prices"""
        self.unrealized_pnl = 0.0
        
        for symbol, position in self.positions.items():
            if symbol in prices:
                position.update_price(prices[symbol])
                self.unrealized_pnl += position.unrealized_pnl
        
        # Update drawdown
        current_equity = self.get_total_equity()
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        drawdown = (current_equity - self.peak_equity) / self.peak_equity
        if drawdown < self.max_drawdown:
            self.max_drawdown = drawdown
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if position exists"""
        return symbol in self.positions
    
    def get_performance_summary(self) -> Dict:
        """Get portfolio performance summary"""
        total_equity = self.get_total_equity()
        total_return = (total_equity - self.initial_capital) / self.initial_capital
        
        # Calculate win rate
        winning_trades = [t for t in self.closed_trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(self.closed_trades) if self.closed_trades else 0
        
        return {
            'initial_capital': self.initial_capital,
            'current_equity': total_equity,
            'cash': self.cash,
            'positions_value': sum(p.get_value() for p in self.positions.values()),
            'total_return': total_return,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'total_pnl': self.realized_pnl + self.unrealized_pnl,
            'max_drawdown': self.max_drawdown,
            'total_trades': len(self.closed_trades),
            'win_rate': win_rate,
            'active_positions': len(self.positions)
        }
    
    def get_positions_summary(self) -> List[Dict]:
        """Get summary of all positions"""
        return [
            {
                'symbol': symbol,
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'value': pos.get_value(),
                'pnl': pos.unrealized_pnl,
                'pnl_pct': pos.get_pnl_pct(),
                'entry_time': pos.entry_timestamp
            }
            for symbol, pos in self.positions.items()
        ]
