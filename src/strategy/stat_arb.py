import numpy as np
import pandas as pd
from typing import Tuple, Optional

# Try to import statsmodels, handle if missing
try:
    from statsmodels.tsa.stattools import coint
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

class StatArbStrategy:
    """
    Statistical Arbitrage Strategy based on Cointegration (Pairs Trading).
    """
    
    def __init__(self, lookback: int = 60, z_threshold: float = 2.0, exit_z_threshold: float = 0.5):
        self.lookback = lookback
        self.z_threshold = z_threshold
        self.exit_z_threshold = exit_z_threshold
        self.hedge_ratio = None
        self.spread_mean = None
        self.spread_std = None

    def test_cointegration(self, series_a: pd.Series, series_b: pd.Series) -> Tuple[float, float, bool]:
        """
        Tests for cointegration between two price series using Engle-Granger test.
        Returns: (score, p_value, is_cointegrated)
        """
        if not STATSMODELS_AVAILABLE:
            print("Warning: statsmodels not installed. Using mock cointegration test.")
            # Mock logic: if correlation is extremely high, assume cointegrated for demo
            corr = series_a.corr(series_b)
            return (0.0, 0.01 if corr > 0.9 else 0.5, corr > 0.9)
            
        # Ensure equal length
        min_len = min(len(series_a), len(series_b))
        series_a = series_a.iloc[-min_len:]
        series_b = series_b.iloc[-min_len:]
        
        score, p_value, _ = coint(series_a, series_b)
        is_cointegrated = p_value < 0.05
        
        return score, p_value, is_cointegrated

    def calculate_spread(self, series_a: pd.Series, series_b: pd.Series) -> pd.Series:
        """
        Calculates the spread: Spread = Y - (beta * X + alpha)
        """
        if not STATSMODELS_AVAILABLE:
            # Simple ratio spread for fallback
            return series_a / series_b
            
        # Linear regression to find hedge ratio (beta)
        X = sm.add_constant(series_b)
        model = sm.OLS(series_a, X).fit()
        
        self.hedge_ratio = model.params[1]
        alpha = model.params[0]
        
        spread = series_a - (self.hedge_ratio * series_b + alpha)
        return spread

    def get_signal(self, current_spread_val: float) -> str:
        """
        Generates trading signal based on Z-score of the spread.
        """
        if self.spread_mean is None or self.spread_std is None:
            return 'NEUTRAL'
            
        z_score = (current_spread_val - self.spread_mean) / self.spread_std
        
        if z_score > self.z_threshold:
            return 'SHORT_SPREAD' # Spread is too high, expect reversion (Short A, Long B)
        elif z_score < -self.z_threshold:
            return 'LONG_SPREAD' # Spread is too low, expect reversion (Long A, Short B)
        elif abs(z_score) < self.exit_z_threshold:
            return 'EXIT' # Spread has reverted to mean
            
        return 'HOLD'

    def update_statistics(self, spread_series: pd.Series):
        """
        Updates rolling mean and std of the spread.
        """
        self.spread_mean = spread_series.mean()
        self.spread_std = spread_series.std()
