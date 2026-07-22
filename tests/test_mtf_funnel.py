import pytest
import pandas as pd
from src.strategy.vibe_alpha import VibeAlphaStrategy

@pytest.fixture
def strategy():
    return VibeAlphaStrategy({
        "lookback": 20,
        "adx_period": 14,
        "atr_period": 14,
        "rsi_period": 14,
        "adx_threshold": 18
    })

def test_evaluate_4h_bias_bullish(strategy):
    # Construct 210 4H candles with upward trend (close > ema_200)
    prices = [100.0 + (i * 0.5) for i in range(210)]
    df_4h = pd.DataFrame({
        'open': prices,
        'high': [p + 1.0 for p in prices],
        'low': [p - 1.0 for p in prices],
        'close': prices,
        'volume': [1000.0] * 210
    })
    
    is_bullish, score = strategy.evaluate_4h_bias(df_4h)
    assert is_bullish is True
    assert score > 0

def test_evaluate_4h_bias_bearish(strategy):
    # Construct 210 4H candles with downward trend
    prices = [300.0 - (i * 0.5) for i in range(210)]
    df_4h = pd.DataFrame({
        'open': prices,
        'high': [p + 1.0 for p in prices],
        'low': [p - 1.0 for p in prices],
        'close': prices,
        'volume': [1000.0] * 210
    })
    
    is_bullish, score = strategy.evaluate_4h_bias(df_4h)
    assert is_bullish is False

def test_evaluate_1h_structure_valid(strategy):
    # Construct 210 1H candles with healthy trend (EMA fast > EMA slow and RSI in 45-75 range)
    base = 100.0
    prices = [base + (i * 0.1 if i % 4 != 0 else -i * 0.05) for i in range(210)]
    df_1h = pd.DataFrame({
        'open': prices,
        'high': [p + 0.5 for p in prices],
        'low': [p - 0.5 for p in prices],
        'close': prices,
        'volume': [5000.0] * 210
    })
    
    is_valid, score = strategy.evaluate_1h_structure(df_1h)
    assert is_valid is True
