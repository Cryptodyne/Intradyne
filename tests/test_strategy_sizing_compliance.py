import pytest
import pandas as pd
from unittest.mock import MagicMock, AsyncMock
from src.trading.trade_executor import TradeExecutor

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_dynamic_order_sizing_buy():
    # Setup executor
    executor = TradeExecutor()
    executor.halal_whitelist = {"BTC/USDT"}
    
    # Enable a 5% risk per trade config & disable Kelly sizing for fixed pct test
    executor.config["use_kelly_sizing"] = False
    executor.config["risk_per_trade"] = 0.05
    executor.config["max_position_pct"] = 0.20 # 20%
    
    signal = {
        'symbol': 'BTC/USDT',
        'action': 'BUY',
        'confidence': 0.8
    }
    
    # Mock validate_trade to always pass
    executor.validate_trade = MagicMock(return_value=(True, ""))
    
    # Current Price = 50000.0, balance = 10000.0
    # Expected size = (10000.0 * 0.05) / 50000.0 = 500 / 50000.0 = 0.01 BTC
    result = await executor.execute_trade(
        signal=signal,
        current_price=50000.0,
        balance=10000.0
    )
    
    assert result.success is True
    assert result.size == 0.01
    assert result.position_value == 500.0

@pytest.mark.anyio
async def test_dynamic_order_sizing_buy_clamping():
    executor = TradeExecutor()
    executor.halal_whitelist = {"BTC/USDT"}
    executor.validate_trade = MagicMock(return_value=(True, ""))
    executor.config["use_kelly_sizing"] = False
    
    # 1. Test case: Risk percentage is set to 25% (should clamp to 10% maximum)
    executor.config["risk_per_trade"] = 0.25
    signal = {
        'symbol': 'BTC/USDT',
        'action': 'BUY',
        'confidence': 0.8
    }
    
    # balance = 10000.0, price = 50000.0
    # size should clamp to 10% of balance = 1000 USDT -> 0.02 BTC
    result = await executor.execute_trade(
        signal=signal,
        current_price=50000.0,
        balance=10000.0
    )
    assert result.size == 0.02
    
    # 2. Test case: Risk percentage is set to 0.1% (should clamp to 1% minimum)
    executor.config["risk_per_trade"] = 0.001
    result = await executor.execute_trade(
        signal=signal,
        current_price=50000.0,
        balance=10000.0
    )
    # size should clamp to 1% of balance = 100 USDT -> 0.002 BTC
    assert result.size == 0.002

@pytest.mark.anyio
async def test_dynamic_order_sizing_sell_defaults_to_open_position():
    executor = TradeExecutor()
    executor.halal_whitelist = {"BTC/USDT"}
    executor.validate_trade = MagicMock(return_value=(True, ""))
    
    signal = {
        'symbol': 'BTC/USDT',
        'action': 'SELL',
        'confidence': 0.8
    }
    
    open_positions = {
        'BTC/USDT': {
            'entry_price': 50000.0,
            'size': 0.15  # open position size
        }
    }
    
    result = await executor.execute_trade(
        signal=signal,
        current_price=51000.0,
        balance=10000.0,
        open_positions=open_positions
    )
    
    assert result.success is True
    assert result.size == 0.15
    assert result.position_value == 51000.0 * 0.15

@pytest.mark.anyio
async def test_volatility_adjusted_stops_calculation(mocker):
    # Test volatility-adjusted ATR-based stops calculation in strategy_process helper
    from src.engine.strategy_process import StrategyEngine
    
    engine = StrategyEngine("mock_shm")
    engine.balance = 10000.0
    
    # Mock candle manager and AdaptiveStrategy
    engine.candle_manager = MagicMock()
    engine.strategy = MagicMock()
    
    # Setup history data frame containing 15 candles
    # ATR is calculated on the last 15 candles
    mock_history = pd.DataFrame({
        'high': [100.0] * 15,
        'low': [90.0] * 15,
        'close': [95.0] * 15
    })
    engine.candle_manager.get_history = MagicMock(return_value=mock_history)
    
    # Setup mock signal
    mock_signal = {
        'symbol': 'BTC/USDT',
        'action': 'BUY',
        'confidence': 0.8
    }
    engine.strategy.analyze = MagicMock(return_value=mock_signal)
    
    # Mock TradeExecutor execution
    engine.executor = MagicMock()
    engine.executor.execute_trade = AsyncMock()
    
    await engine._run_strategy_logic('BTC/USDT', current_price=100.0, current_timestamp=1234567890.0)
    
    # Verify signal has stop_loss and take_profit computed
    called_signal = engine.executor.execute_trade.call_args[1]['signal']
    assert 'stop_loss' in called_signal
    assert 'take_profit' in called_signal
    
    # For high=100, low=90, close=95, true range = 10. ATR = 10.
    # ATR_pct = 10 / 100 = 10%.
    # sl_pct = max(1.5%, 3 * 10%) = 30%. SL price = 100 * (1 - 30%) = 70.0.
    # tp_pct = max(1%, 1.5 * 10%) = 15%. TP price = 100 * (1 + 15%) = 115.0.
    assert called_signal['stop_loss'] == pytest.approx(70.0)
    assert called_signal['take_profit'] == pytest.approx(115.0)
