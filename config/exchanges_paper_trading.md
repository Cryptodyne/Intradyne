# Exchange Configuration for Paper Trading

## Supported Exchanges

The paper trading system supports multiple exchanges via CCXT:

### 1. Bitget (Primary)
- **Exchange ID**: `bitget`
- **Features**: Spot trading, futures
- **Public Data**: Yes (no API keys needed)
- **Rate Limits**: Standard

**Usage**:
```python
trader.connect_exchange('bitget')
```

### 2. Binance (Fallback)
- **Exchange ID**: `binance`
- **Features**: Spot trading, futures, margin
- **Public Data**: Yes
- **Rate Limits**: High

**Usage**:
```python
trader.connect_exchange('binance')
```

### 3. Other Supported Exchanges
- **OKX**: `okx`
- **Bybit**: `bybit`
- **KuCoin**: `kucoin`
- **Coinbase**: `coinbase`
- **Kraken**: `kraken`

---

## Configuration

### Default Settings

```yaml
exchange:
  name: bitget
  symbols:
    - BTC/USDT
    - ETH/USDT
  update_interval: 60  # seconds
  
trading:
  initial_capital: 10000
  position_size: 0.1  # 10% per trade
  
risk:
  max_positions: 5
  stop_loss: 0.03     # 3%
  take_profit: 0.10   # 10%
  daily_loss_limit: 0.05  # 5%
```

---

## API Keys (Optional)

For public data (prices, orderbook), **no API keys needed**.

For private features (account info, trading), add to `.env`:

```env
BITGET_API_KEY=your_api_key
BITGET_SECRET=your_secret
BITGET_PASSWORD=your_password
```

---

## Rate Limits

| Exchange | Public | Private |
|----------|--------|---------|
| Bitget   | 20/s   | 10/s    |
| Binance  | 50/s   | 20/s    |
| OKX      | 20/s   | 10/s    |

Paper trading uses public endpoints only.

---

## Troubleshooting

### Connection Failed
1. Check internet connection
2. Verify exchange is operational
3. Try fallback exchange

### Rate Limit Exceeded
1. Increase update interval
2. Reduce number of symbols
3. Use different exchange

### Symbol Not Found
1. Check symbol format (BTC/USDT not BTCUSDT)
2. Verify symbol exists on exchange
3. Use exchange's symbol list

---

## Quick Start Scripts

### Bitget
```bash
python scripts/run_bitget_paper_trading.py
```

### Binance
```bash
python scripts/run_paper_trading.py
```

### Custom Exchange
```python
from src.trading.paper_trader import PaperTrader

trader = PaperTrader(initial_capital=10000)
trader.connect_exchange('okx')  # or any CCXT exchange
trader.run_trading_loop(['BTC/USDT'])
```
