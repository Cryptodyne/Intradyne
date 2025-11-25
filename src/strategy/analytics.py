import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

class PerformanceAnalytics:
    """
    Advanced performance analytics for trading strategies.
    Calculates risk-adjusted metrics, drawdowns, and generates reports.
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize analytics.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        self.risk_free_rate = risk_free_rate
        self.logger = logging.getLogger("PerformanceAnalytics")
    
    def calculate_sharpe_ratio(self, returns: List[float], 
                              periods_per_year: int = 252) -> float:
        """
        Calculate Sharpe Ratio (risk-adjusted return).
        
        Args:
            returns: List of period returns
            periods_per_year: Trading periods per year (252 for daily)
            
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (self.risk_free_rate / periods_per_year)
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(periods_per_year)
        return float(sharpe)
    
    def calculate_sortino_ratio(self, returns: List[float],
                                periods_per_year: int = 252) -> float:
        """
        Calculate Sortino Ratio (downside risk-adjusted return).
        
        Args:
            returns: List of period returns
            periods_per_year: Trading periods per year
            
        Returns:
            Sortino ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (self.risk_free_rate / periods_per_year)
        
        # Downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return np.inf
        
        downside_std = np.std(downside_returns)
        
        if downside_std == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / downside_std * np.sqrt(periods_per_year)
        return float(sortino)
    
    def calculate_calmar_ratio(self, total_return: float, 
                               max_drawdown: float,
                               years: float = 1.0) -> float:
        """
        Calculate Calmar Ratio (return / max drawdown).
        
        Args:
            total_return: Total return
            max_drawdown: Maximum drawdown (negative value)
            years: Number of years
            
        Returns:
            Calmar ratio
        """
        if max_drawdown == 0:
            return 0.0
        
        annualized_return = (1 + total_return) ** (1 / years) - 1
        calmar = annualized_return / abs(max_drawdown)
        
        return float(calmar)
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Dict[str, Any]:
        """
        Calculate maximum drawdown and related metrics.
        
        Args:
            equity_curve: List of equity values
            
        Returns:
            Dictionary with drawdown metrics
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'drawdown_duration': 0,
                'recovery_time': 0
            }
        
        equity = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        
        max_dd = np.min(drawdown)
        max_dd_idx = np.argmin(drawdown)
        
        # Find peak before max drawdown
        peak_idx = np.argmax(equity[:max_dd_idx+1]) if max_dd_idx > 0 else 0
        
        # Find recovery (if any)
        recovery_idx = None
        peak_value = equity[peak_idx]
        for i in range(max_dd_idx + 1, len(equity)):
            if equity[i] >= peak_value:
                recovery_idx = i
                break
        
        drawdown_duration = max_dd_idx - peak_idx
        recovery_time = (recovery_idx - max_dd_idx) if recovery_idx else len(equity) - max_dd_idx
        
        return {
            'max_drawdown': float(max_dd),
            'max_drawdown_pct': float(max_dd * 100),
            'drawdown_duration': int(drawdown_duration),
            'recovery_time': int(recovery_time),
            'peak_idx': int(peak_idx),
            'trough_idx': int(max_dd_idx),
            'recovered': recovery_idx is not None
        }
    
    def calculate_win_rate(self, trades: List[Dict]) -> Dict[str, Any]:
        """
        Calculate win rate and related metrics.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Dictionary with win rate metrics
        """
        if not trades:
            return {
                'win_rate': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0
            }
        
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        
        return {
            'win_rate': len(winning_trades) / len(trades),
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }
    
    def calculate_profit_factor(self, trades: List[Dict]) -> float:
        """
        Calculate profit factor (gross profit / gross loss).
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Profit factor
        """
        if not trades:
            return 0.0
        
        gross_profit = sum(t['pnl'] for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t.get('pnl', 0) < 0))
        
        if gross_loss == 0:
            return np.inf if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def calculate_expectancy(self, trades: List[Dict]) -> float:
        """
        Calculate expectancy (average profit per trade).
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Expectancy
        """
        if not trades:
            return 0.0
        
        return sum(t.get('pnl', 0) for t in trades) / len(trades)
    
    def analyze_trades(self, trades: List[Dict]) -> Dict[str, Any]:
        """
        Comprehensive trade analysis.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Dictionary with trade analysis
        """
        if not trades:
            return {'error': 'No trades to analyze'}
        
        trades_df = pd.DataFrame(trades)
        
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades),
            'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
            'largest_win': trades_df['pnl'].max(),
            'largest_loss': trades_df['pnl'].min(),
            'avg_trade': trades_df['pnl'].mean(),
            'profit_factor': self.calculate_profit_factor(trades),
            'expectancy': self.calculate_expectancy(trades)
        }
    
    def generate_report(self, backtest_results: Dict[str, Any],
                       format: str = 'text') -> str:
        """
        Generate comprehensive performance report.
        
        Args:
            backtest_results: Results from backtester
            format: 'text' or 'html'
            
        Returns:
            Formatted report string
        """
        metrics = backtest_results.get('metrics', {})
        trades = backtest_results.get('trades', [])
        equity_curve = backtest_results.get('equity_curve', [])
        
        if format == 'text':
            return self._generate_text_report(metrics, trades, equity_curve)
        elif format == 'html':
            return self._generate_html_report(metrics, trades, equity_curve)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _generate_text_report(self, metrics: Dict, trades: List, 
                             equity_curve: List) -> str:
        """Generate text report."""
        report = []
        report.append("=" * 60)
        report.append("BACKTEST PERFORMANCE REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 60)
        report.append(f"Total Return: {metrics.get('total_return', 0)*100:.2f}%")
        report.append(f"Final Capital: ${metrics.get('final_capital', 0):,.2f}")
        report.append(f"Total Trades: {metrics.get('total_trades', 0)}")
        report.append("")
        
        # Risk-Adjusted Metrics
        report.append("RISK-ADJUSTED METRICS")
        report.append("-" * 60)
        report.append(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.4f}")
        
        # Calculate additional metrics
        if equity_curve:
            equity_values = [e['equity'] for e in equity_curve]
            returns = np.diff(equity_values) / equity_values[:-1]
            sortino = self.calculate_sortino_ratio(returns.tolist())
            report.append(f"Sortino Ratio: {sortino:.4f}")
            
            calmar = self.calculate_calmar_ratio(
                metrics.get('total_return', 0),
                metrics.get('max_drawdown', 0)
            )
            report.append(f"Calmar Ratio: {calmar:.4f}")
        
        report.append("")
        
        # Trade Statistics
        report.append("TRADE STATISTICS")
        report.append("-" * 60)
        report.append(f"Win Rate: {metrics.get('win_rate', 0)*100:.1f}%")
        report.append(f"Winning Trades: {metrics.get('winning_trades', 0)}")
        report.append(f"Losing Trades: {metrics.get('losing_trades', 0)}")
        report.append(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        report.append(f"Avg Win: ${metrics.get('avg_win', 0):,.2f}")
        report.append(f"Avg Loss: ${metrics.get('avg_loss', 0):,.2f}")
        report.append("")
        
        # Risk Metrics
        report.append("RISK METRICS")
        report.append("-" * 60)
        report.append(f"Max Drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
        
        if equity_curve:
            equity_values = [e['equity'] for e in equity_curve]
            dd_metrics = self.calculate_max_drawdown(equity_values)
            report.append(f"Drawdown Duration: {dd_metrics['drawdown_duration']} periods")
            report.append(f"Recovery Time: {dd_metrics['recovery_time']} periods")
            report.append(f"Recovered: {'Yes' if dd_metrics['recovered'] else 'No'}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def _generate_html_report(self, metrics: Dict, trades: List,
                             equity_curve: List) -> str:
        """Generate HTML report."""
        html = f"""
        <html>
        <head>
            <title>Backtest Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>Backtest Performance Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Summary</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Return</td><td class="{'positive' if metrics.get('total_return', 0) > 0 else 'negative'}">{metrics.get('total_return', 0)*100:.2f}%</td></tr>
                <tr><td>Final Capital</td><td>${metrics.get('final_capital', 0):,.2f}</td></tr>
                <tr><td>Total Trades</td><td>{metrics.get('total_trades', 0)}</td></tr>
            </table>
            
            <h2>Risk-Adjusted Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Sharpe Ratio</td><td>{metrics.get('sharpe_ratio', 0):.4f}</td></tr>
                <tr><td>Max Drawdown</td><td class="negative">{metrics.get('max_drawdown', 0)*100:.2f}%</td></tr>
            </table>
            
            <h2>Trade Statistics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Win Rate</td><td>{metrics.get('win_rate', 0)*100:.1f}%</td></tr>
                <tr><td>Profit Factor</td><td>{metrics.get('profit_factor', 0):.2f}</td></tr>
                <tr><td>Avg Win</td><td class="positive">${metrics.get('avg_win', 0):,.2f}</td></tr>
                <tr><td>Avg Loss</td><td class="negative">${metrics.get('avg_loss', 0):,.2f}</td></tr>
            </table>
        </body>
        </html>
        """
        return html
    
    def export_report(self, backtest_results: Dict[str, Any],
                     filepath: str, format: str = 'text'):
        """
        Export report to file.
        
        Args:
            backtest_results: Results from backtester
            filepath: Output file path
            format: 'text' or 'html'
        """
        report = self.generate_report(backtest_results, format)
        
        with open(filepath, 'w') as f:
            f.write(report)
        
        self.logger.info(f"Report exported to {filepath}")
