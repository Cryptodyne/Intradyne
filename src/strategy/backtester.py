import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import logging

class Backtester:
    """
    Advanced backtesting engine with realistic trade simulation.
    Supports slippage, commissions, position sizing, and comprehensive metrics.
    """
    
    def __init__(self, initial_capital: float = 10000, 
                 commission: float = 0.001,
                 slippage: float = 0.001,
                 position_size_method: str = 'fixed'):
        """
        Initialize the backtester.
        
        Args:
            initial_capital: Starting capital
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage rate (0.001 = 0.1%)
            position_size_method: 'fixed', 'percent', 'kelly'
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.position_size_method = position_size_method
        
        self.logger = logging.getLogger("Backtester")
        
        # State
        self.capital = initial_capital
        self.position = 0  # Current position size
        self.entry_price = 0
        self.trades = []
        self.equity_curve = []
        
    def load_data(self, symbol: str, start_date: str, end_date: str,
                  timeframe: str = '5m', source: str = 'ccxt') -> pd.DataFrame:
        """
        Load historical data for backtesting.
        
        Args:
            symbol: Trading pair
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            timeframe: Candle timeframe
            source: Data source ('ccxt', 'csv', 'mock')
            
        Returns:
            DataFrame with OHLCV data
        """
        if source == 'mock':
            # Generate mock data for testing
            return self._generate_mock_data(symbol, start_date, end_date, timeframe)
        elif source == 'ccxt':
            # Load from CCXT (requires network)
            return self._load_from_ccxt(symbol, start_date, end_date, timeframe)
        elif source == 'csv':
            # Load from CSV file
            return self._load_from_csv(symbol, start_date, end_date)
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def _generate_mock_data(self, symbol: str, start_date: str, end_date: str,
                           timeframe: str) -> pd.DataFrame:
        """Generate mock OHLCV data for testing."""
        # Parse dates
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Generate date range
        if timeframe == '5m':
            freq = '5T'
        elif timeframe == '15m':
            freq = '15T'
        elif timeframe == '1h':
            freq = '1H'
        elif timeframe == '1d':
            freq = '1D'
        else:
            freq = '5T'
        
        dates = pd.date_range(start=start, end=end, freq=freq)
        
        # Generate realistic price data (random walk with trend)
        np.random.seed(42)
        base_price = 50000  # Starting price
        returns = np.random.normal(0.0001, 0.02, len(dates))  # Slight upward bias
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Generate OHLCV
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * (1 + np.abs(np.random.normal(0, 0.005, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.005, len(dates)))),
            'close': prices * (1 + np.random.normal(0, 0.003, len(dates))),
            'volume': np.random.uniform(100, 1000, len(dates))
        })
        
        return data
    
    def _load_from_ccxt(self, symbol: str, start_date: str, end_date: str,
                       timeframe: str) -> pd.DataFrame:
        """Load data from CCXT exchange."""
        try:
            from src.data.market_data import MarketDataFetcher
            
            fetcher = MarketDataFetcher('binance')
            
            # Convert dates to timestamps
            start_ts = int(pd.to_datetime(start_date).timestamp() * 1000)
            
            # Fetch data
            ohlcv = fetcher.fetch_ohlcv(symbol, timeframe, limit=1000, since=start_ts)
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Filter by date range
            df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to load from CCXT: {e}")
            self.logger.info("Falling back to mock data")
            return self._generate_mock_data(symbol, start_date, end_date, timeframe)
    
    def _load_from_csv(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Load data from CSV file."""
        filename = f"data/historical/{symbol.replace('/', '_')}.csv"
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        return df
    
    def run_backtest(self, strategy_func: Callable, data: pd.DataFrame,
                    position_size: float = 0.1) -> Dict[str, Any]:
        """
        Run backtest with given strategy.
        
        Args:
            strategy_func: Function that takes (data, index) and returns signal
            data: Historical OHLCV data
            position_size: Position size (0.1 = 10% of capital)
            
        Returns:
            Backtest results dictionary
        """
        self.logger.info(f"Starting backtest with {len(data)} candles")
        
        # Reset state
        self.capital = self.initial_capital
        self.position = 0
        self.entry_price = 0
        self.trades = []
        self.equity_curve = []
        
        # Run through each candle
        for i in range(len(data)):
            current_price = data.iloc[i]['close']
            
            # Get strategy signal
            signal = strategy_func(data, i)
            
            # Execute trades based on signal
            if signal == 'BUY' and self.position == 0:
                self._open_position('LONG', current_price, position_size)
            elif signal == 'SELL' and self.position > 0:
                self._close_position(current_price)
            
            # Track equity
            equity = self._calculate_equity(current_price)
            self.equity_curve.append({
                'timestamp': data.iloc[i]['timestamp'],
                'equity': equity,
                'capital': self.capital,
                'position_value': self.position * current_price if self.position > 0 else 0
            })
        
        # Close any open position at end
        if self.position > 0:
            final_price = data.iloc[-1]['close']
            self._close_position(final_price)
        
        # Calculate metrics
        metrics = self.calculate_metrics()
        
        self.logger.info(f"Backtest complete: {len(self.trades)} trades, Final capital: ${self.capital:.2f}")
        
        return {
            'metrics': metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'final_capital': self.capital,
            'total_return': (self.capital - self.initial_capital) / self.initial_capital
        }
    
    def _open_position(self, direction: str, price: float, size: float):
        """Open a new position."""
        # Apply slippage
        execution_price = price * (1 + self.slippage) if direction == 'LONG' else price * (1 - self.slippage)
        
        # Calculate position size
        position_value = self.capital * size
        shares = position_value / execution_price
        
        # Apply commission
        commission_cost = position_value * self.commission
        
        # Update state
        self.position = shares
        self.entry_price = execution_price
        self.capital -= (position_value + commission_cost)
        
        self.logger.debug(f"OPEN {direction}: {shares:.4f} @ ${execution_price:.2f}")
    
    def _close_position(self, price: float):
        """Close current position."""
        if self.position == 0:
            return
        
        # Apply slippage
        execution_price = price * (1 - self.slippage)
        
        # Calculate proceeds
        position_value = self.position * execution_price
        commission_cost = position_value * self.commission
        proceeds = position_value - commission_cost
        
        # Calculate P&L
        pnl = proceeds - (self.position * self.entry_price)
        pnl_pct = pnl / (self.position * self.entry_price)
        
        # Record trade
        self.trades.append({
            'entry_price': self.entry_price,
            'exit_price': execution_price,
            'shares': self.position,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'commission': commission_cost * 2,  # Entry + exit
            'slippage_cost': abs(price - execution_price) * self.position
        })
        
        # Update state
        self.capital += proceeds
        self.position = 0
        self.entry_price = 0
        
        self.logger.debug(f"CLOSE: P&L ${pnl:.2f} ({pnl_pct*100:.2f}%)")
    
    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current total equity."""
        position_value = self.position * current_price if self.position > 0 else 0
        return self.capital + position_value
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        if not self.trades:
            return {'error': 'No trades executed'}
        
        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = trades_df['pnl'].sum()
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Profit factor
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Returns
        returns = equity_df['equity'].pct_change().dropna()
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        
        # Sharpe ratio (annualized, assuming 252 trading days)
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # Maximum drawdown
        equity_series = equity_df['equity']
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_capital': self.capital
        }
    
    def export_results(self, filepath: str, format: str = 'json'):
        """Export backtest results to file."""
        results = {
            'metrics': self.calculate_metrics(),
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        if format == 'json':
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        elif format == 'csv':
            pd.DataFrame(self.trades).to_csv(filepath.replace('.json', '_trades.csv'), index=False)
            pd.DataFrame(self.equity_curve).to_csv(filepath.replace('.json', '_equity.csv'), index=False)
        
        self.logger.info(f"Results exported to {filepath}")
