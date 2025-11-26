"""
Enhanced Paper Trading Bot Runner with Improved AI
Integrates technical indicators and better risk management.
"""

import sys
import os
import json
import logging
from datetime import datetime
import pandas as pd

# Add project root
sys.path.insert(0, os.path.abspath('.'))

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/paper_trading.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_ai_config():
    """Load AI config from file."""
    config_path = 'config/ai_trading_config.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def create_strategy_with_improved_ai():
    """Create trading strategy using improved AI engine."""
    from src.trading.ai_decision_engine import SignalGenerator
    
    config = load_ai_config()
    
    # Convert percentages to decimals
    engine_config = {
        'buy_threshold': config.get('buy_threshold', 0.6) / 100,
        'sell_threshold': config.get('sell_threshold', 0.4) / 100,
        'stop_loss_pct': config.get('stop_loss_pct', 3.0) / 100,
        'take_profit_pct': config.get('take_profit_pct', 8.0) / 100,
        'confidence_threshold': config.get('confidence_threshold', 75) / 100,
        'max_position_size': config.get('max_position_size', 500.0),
        'min_hold_time_minutes': config.get('min_hold_time_minutes', 30),
        'use_technical_indicators': config.get('use_technical_indicators', True),
        'rsi_overbought': config.get('rsi_overbought', 70),
        'rsi_oversold': config.get('rsi_oversold', 30),
        'min_volume_ratio': config.get('min_volume_ratio', 1.2)
    }
    
    signal_gen = SignalGenerator(engine_config)
    
    logger.info("✅ AI Engine loaded with improved config:")
    logger.info(f"   Buy: >{engine_config['buy_threshold']*100:.1f}%, SL: {engine_config['stop_loss_pct']*100:.1f}%, Hold: {engine_config['min_hold_time_minutes']}min")
    
    def strategy(data: pd.DataFrame, index: int):
        """Strategy function."""
        if len(data) < 50:
            return 'HOLD'
        
        current_price = data['close'].iloc[index]
        prev_price = data['close'].iloc[index-1]
        momentum = (current_price - prev_price) / prev_price
        
        price_data = data.iloc[:index+1].copy()
        if 'timestamp' not in price_data.columns:
            price_data['timestamp'] = pd.date_range(end=datetime.now(), periods=len(price_data), freq='1H')
        if 'open' not in price_data.columns:
            price_data['open'] = price_data['close']
        
        signal = signal_gen.get_recommendation(
            symbol='BTC/USDT',
            current_price=current_price,
            momentum=momentum,
            price_data=price_data
        )
        
        return signal['action']
    
    return strategy


def main():
    """Start paper trading."""
    print("="*70)
    print("🤖 INTRADYNE PAPER TRADING - IMPROVED AI")
    print("="*70)
    print(f"Started: {datetime.now()}")
    print("="*70)
    
    strategy = create_strategy_with_improved_ai()
    
    from src.trading.paper_trader import PaperTrader
    
    trader = PaperTrader(initial_capital=10000.0, strategy_func=strategy)
    
    logger.info("Connecting to Bitget...")
    trader.connect_exchange('bitget')
    
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    logger.info(f"Trading: {symbols} | Interval: 60s")
    logger.info("Press Ctrl+C to stop")
    print("="*70)
    
    trader.run_trading_loop(symbols=symbols, interval=60)


if __name__ == "__main__":
    main()
