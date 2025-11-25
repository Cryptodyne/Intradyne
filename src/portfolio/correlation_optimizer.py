"""
Correlation-Based Portfolio Optimizer
Optimize portfolio allocation considering asset correlations
"""

import numpy as np
import pandas as pd
from typing import Dict, List
import logging

class CorrelationOptimizer:
    """
    Optimize portfolio allocation based on asset correlations.
    Reduces portfolio risk through diversification.
    """
    
    def __init__(self, correlation_threshold: float = 0.7,
                 max_correlation_exposure: float = 0.5):
        """
        Initialize correlation optimizer.
        
        Args:
            correlation_threshold: Threshold for high correlation
            max_correlation_exposure: Max exposure to correlated assets
        """
        self.correlation_threshold = correlation_threshold
        self.max_correlation_exposure = max_correlation_exposure
        self.logger = logging.getLogger("CorrelationOptimizer")
        
        self.correlation_matrix = None
        self.correlation_history = []
    
    def calculate_correlation_matrix(self, returns_data: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Calculate correlation matrix from returns.
        
        Args:
            returns_data: Dictionary of {symbol: returns_series}
        
        Returns:
            Correlation matrix
        """
        # Create DataFrame from returns
        df = pd.DataFrame(returns_data)
        
        # Calculate correlation
        corr_matrix = df.corr()
        
        self.correlation_matrix = corr_matrix
        
        return corr_matrix
    
    def find_high_correlations(self, corr_matrix: pd.DataFrame = None,
                               threshold: float = None) -> List[tuple]:
        """
        Find highly correlated asset pairs.
        
        Args:
            corr_matrix: Correlation matrix
            threshold: Correlation threshold
        
        Returns:
            List of (asset1, asset2, correlation) tuples
        """
        if corr_matrix is None:
            corr_matrix = self.correlation_matrix
        
        if threshold is None:
            threshold = self.correlation_threshold
        
        high_corr_pairs = []
        
        for i in range(len(corr_matrix)):
            for j in range(i + 1, len(corr_matrix)):
                corr = corr_matrix.iloc[i, j]
                
                if abs(corr) >= threshold:
                    asset1 = corr_matrix.index[i]
                    asset2 = corr_matrix.columns[j]
                    high_corr_pairs.append((asset1, asset2, corr))
        
        return high_corr_pairs
    
    def calculate_correlation_penalty(self, symbol: str,
                                     existing_positions: Dict[str, float],
                                     corr_matrix: pd.DataFrame = None) -> float:
        """
        Calculate penalty for adding correlated position.
        
        Args:
            symbol: Symbol to add
            existing_positions: Current positions {symbol: size}
            corr_matrix: Correlation matrix
        
        Returns:
            Penalty factor (0 to 1)
        """
        if corr_matrix is None:
            corr_matrix = self.correlation_matrix
        
        if corr_matrix is None or symbol not in corr_matrix.index:
            return 0.0
        
        total_correlation = 0
        total_weight = 0
        
        for existing_symbol, size in existing_positions.items():
            if existing_symbol in corr_matrix.columns and existing_symbol != symbol:
                corr = abs(corr_matrix.loc[symbol, existing_symbol])
                
                if corr > self.correlation_threshold:
                    # Weight by position size
                    total_correlation += corr * size
                    total_weight += size
        
        if total_weight == 0:
            return 0.0
        
        avg_correlation = total_correlation / total_weight
        
        # Convert to penalty (0 to max_correlation_exposure)
        penalty = min(avg_correlation, self.max_correlation_exposure)
        
        return penalty
    
    def optimize_positions(self, proposed_positions: Dict[str, float],
                          corr_matrix: pd.DataFrame = None) -> Dict[str, float]:
        """
        Optimize position sizes considering correlations.
        
        Args:
            proposed_positions: Proposed positions {symbol: size}
            corr_matrix: Correlation matrix
        
        Returns:
            Optimized positions
        """
        if corr_matrix is None:
            corr_matrix = self.correlation_matrix
        
        optimized = {}
        
        for symbol, size in proposed_positions.items():
            # Calculate penalty
            penalty = self.calculate_correlation_penalty(
                symbol, optimized, corr_matrix
            )
            
            # Adjust size
            adjusted_size = size * (1 - penalty)
            optimized[symbol] = adjusted_size
            
            self.logger.debug(f"{symbol}: penalty={penalty:.1%}, adjusted={adjusted_size:.4f}")
        
        return optimized
    
    def calculate_portfolio_risk(self, positions: Dict[str, float],
                                volatilities: Dict[str, float],
                                corr_matrix: pd.DataFrame = None) -> float:
        """
        Calculate portfolio risk considering correlations.
        
        Args:
            positions: Position sizes {symbol: size}
            volatilities: Asset volatilities {symbol: vol}
            corr_matrix: Correlation matrix
        
        Returns:
            Portfolio volatility
        """
        if corr_matrix is None:
            corr_matrix = self.correlation_matrix
        
        # Get symbols in order
        symbols = list(positions.keys())
        
        # Create weight vector
        weights = np.array([positions[s] for s in symbols])
        
        # Create volatility vector
        vols = np.array([volatilities.get(s, 0.02) for s in symbols])
        
        # Get correlation submatrix
        corr_sub = corr_matrix.loc[symbols, symbols].values
        
        # Portfolio variance
        portfolio_var = weights.T @ (np.outer(vols, vols) * corr_sub) @ weights
        
        # Portfolio volatility
        portfolio_vol = np.sqrt(portfolio_var)
        
        return portfolio_vol
    
    def calculate_diversification_ratio(self, positions: Dict[str, float],
                                       volatilities: Dict[str, float],
                                       corr_matrix: pd.DataFrame = None) -> float:
        """
        Calculate diversification ratio.
        Higher is better (more diversified).
        
        Args:
            positions: Position sizes
            volatilities: Asset volatilities
            corr_matrix: Correlation matrix
        
        Returns:
            Diversification ratio
        """
        # Weighted average volatility
        total_weight = sum(positions.values())
        weighted_vol = sum(positions[s] * volatilities.get(s, 0.02) 
                          for s in positions) / total_weight
        
        # Portfolio volatility
        portfolio_vol = self.calculate_portfolio_risk(positions, volatilities, corr_matrix)
        
        # Diversification ratio
        div_ratio = weighted_vol / portfolio_vol if portfolio_vol > 0 else 1.0
        
        return div_ratio
    
    def print_correlation_analysis(self, corr_matrix: pd.DataFrame = None):
        """Print correlation analysis"""
        if corr_matrix is None:
            corr_matrix = self.correlation_matrix
        
        print(f"\n{'='*70}")
        print("CORRELATION ANALYSIS")
        print(f"{'='*70}")
        
        # Correlation matrix
        print(f"\nCorrelation Matrix:")
        print(corr_matrix.round(2))
        
        # High correlations
        high_corr = self.find_high_correlations(corr_matrix)
        
        print(f"\nHigh Correlations (>{self.correlation_threshold}):")
        if high_corr:
            for asset1, asset2, corr in high_corr:
                print(f"  {asset1} - {asset2}: {corr:+.2f}")
        else:
            print("  None found ✅")
        
        print(f"{'='*70}")
