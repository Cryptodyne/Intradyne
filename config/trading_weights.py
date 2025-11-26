# Weight Configuration for RAG-Enhanced Trading
"""Easily adjust momentum vs sentiment weights.

Current: 70% Momentum + 30% Sentiment
Modify the weights below and restart trading.
"""

# ============================================================================
# TRADING SIGNAL WEIGHTS
# ============================================================================

# Momentum weight (technical analysis)
MOMENTUM_WEIGHT = 0.7  # 70%

# Sentiment weight (RAG AI analysis)  
SENTIMENT_WEIGHT = 0.3  # 30%

# Must sum to 1.0
assert MOMENTUM_WEIGHT + SENTIMENT_WEIGHT == 1.0, "Weights must sum to 1.0"

# ============================================================================
# TRADING THRESHOLDS
# ============================================================================

# Buy threshold (combined signal must exceed this)
BUY_THRESHOLD = 0.3  # Lower = more trades

# Sell threshold (combined signal must be below this)
SELL_THRESHOLD = -0.3  # Lower = more trades

# ============================================================================
# POSITION SIZING
# ============================================================================

# Maximum position as % of capital
MAX_POSITION_PCT = 0.2  # 20% of capital per trade

# Maximum position in USD
MAX_POSITION_USD = 1000  # $1,000 max per trade

# ============================================================================
# COMMON CONFIGURATIONS
# ============================================================================

# Balanced (current)
# MOMENTUM_WEIGHT = 0.7
# SENTIMENT_WEIGHT = 0.3

# Sentiment-focused (trust AI more)
# MOMENTUM_WEIGHT = 0.5
# SENTIMENT_WEIGHT = 0.5

# Momentum-focused (traditional technical)
# MOMENTUM_WEIGHT = 0.8
# SENTIMENT_WEIGHT = 0.2

# Pure sentiment (experimental)
# MOMENTUM_WEIGHT = 0.3
# SENTIMENT_WEIGHT = 0.7

# ============================================================================
# USAGE
# ============================================================================
# 1. Modify weights above
# 2. Save this file
# 3. Restart: python scripts/run_rag_paper_trading_config.py
# ============================================================================

def get_config():
    """Get current configuration."""
    return {
        'momentum_weight': MOMENTUM_WEIGHT,
        'sentiment_weight': SENTIMENT_WEIGHT,
        'buy_threshold': BUY_THRESHOLD,
        'sell_threshold': SELL_THRESHOLD,
        'max_position_pct': MAX_POSITION_PCT,
        'max_position_usd': MAX_POSITION_USD,
    }


def print_config():
    """Print current configuration."""
    config = get_config()
    print("\n" + "="*70)
    print("📊 RAG-Enhanced Trading Configuration")
    print("="*70)
    print(f"\n🎯 Signal Weights:")
    print(f"   Momentum: {config['momentum_weight']*100:.0f}%")
    print(f"   Sentiment: {config['sentiment_weight']*100:.0f}%")
    print(f"\n📈 Thresholds:")
    print(f"   Buy Signal: {config['buy_threshold']:+.2f}")
    print(f"   Sell Signal: {config['sell_threshold']:+.2f}")
    print(f"\n💰 Position Limits:")
    print(f"   Max % of Capital: {config['max_position_pct']*100:.0f}%")
    print(f"   Max USD: ${config['max_position_usd']:,.0f}")
    print("="*70 + "\n")


if __name__ == "__main__":
    print_config()
