from .base_engine import BaseEngine
import numpy as np

class TrendEngine(BaseEngine):
    """Enhanced trend detection with multiple indicators."""
    
    def __init__(self):
        super().__init__("TrendEngine")

    def analyze(self, data: dict) -> dict:
        closes = data.get('closes', [])
        if len(closes) < 26:  # Need 26 for MACD
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "risk_flags": ["INSUFFICIENT_DATA"],
                "reason_code": "NO_DATA"
            }
        
        # SMA Strategy
        sma_fast = np.mean(closes[-9:])
        sma_slow = np.mean(closes[-20:])
        
        # EMA (Exponential Moving Average)
        ema_12 = self._calculate_ema(closes, 12)
        ema_26 = self._calculate_ema(closes, 26)
        
        # MACD
        macd_line = ema_12 - ema_26
        signal_line = self._calculate_ema([macd_line], 9)
        
        # RSI
        rsi = self._calculate_rsi(closes, 14)
        
        # Combine signals
        signals = []
        
        if sma_fast > sma_slow:
            signals.append(1)
        else:
            signals.append(-1)
        
        if macd_line > signal_line:
            signals.append(1)
        else:
            signals.append(-1)
        
        if rsi < 30:  # Oversold
            signals.append(1)
        elif rsi > 70:  # Overbought
            signals.append(-1)
        else:
            signals.append(0)
        
        # Aggregate
        signal_sum = sum(signals)
        
        if signal_sum >= 2:
            direction = "LONG"
            confidence = min(0.9, 0.6 + (signal_sum / 10))
        elif signal_sum <= -2:
            direction = "SHORT"
            confidence = min(0.9, 0.6 + (abs(signal_sum) / 10))
        else:
            direction = "NEUTRAL"
            confidence = 0.5
        
        return {
            "direction": direction,
            "confidence": confidence,
            "risk_flags": [],
            "reason_code": "MULTI_INDICATOR",
            "indicators": {
                "sma_fast": sma_fast,
                "sma_slow": sma_slow,
                "macd": macd_line,
                "rsi": rsi
            }
        }
    
    def _calculate_ema(self, data, period):
        """Calculate Exponential Moving Average."""
        if len(data) < period:
            return np.mean(data)
        
        multiplier = 2 / (period + 1)
        ema = np.mean(data[:period])  # Start with SMA
        
        for price in data[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, closes, period=14):
        """Calculate Relative Strength Index."""
        if len(closes) < period + 1:
            return 50  # Neutral
        
        deltas = np.diff(closes[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class VolatilityEngine(BaseEngine):
    """Enhanced volatility analysis with Bollinger Bands and ATR."""
    
    def __init__(self):
        super().__init__("VolatilityEngine")

    def analyze(self, data: dict) -> dict:
        closes = data.get('closes', [])
        highs = data.get('highs', closes)
        lows = data.get('lows', closes)
        
        if len(closes) < 20:
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "risk_flags": ["INSUFFICIENT_DATA"],
                "reason_code": "NO_DATA"
            }
        
        # Bollinger Bands
        sma_20 = np.mean(closes[-20:])
        std_20 = np.std(closes[-20:])
        upper_band = sma_20 + (2 * std_20)
        lower_band = sma_20 - (2 * std_20)
        
        current_price = closes[-1]
        
        # ATR (Average True Range)
        atr = self._calculate_atr(highs, lows, closes, period=14)
        
        # Standard Deviation
        std_dev = np.std(closes[-20:])
        mean_price = np.mean(closes[-20:])
        vol_ratio = std_dev / mean_price
        
        # Determine direction based on Bollinger Bands
        direction = "NEUTRAL"
        confidence = 0.5
        risk_flags = []
        
        if current_price > upper_band:
            direction = "SHORT"  # Overbought
            confidence = 0.7
        elif current_price < lower_band:
            direction = "LONG"  # Oversold
            confidence = 0.7
        
        # High volatility warning
        if vol_ratio > 0.03:
            risk_flags.append("HIGH_VOLATILITY")
            confidence *= 0.5
        
        return {
            "direction": direction,
            "confidence": confidence,
            "risk_flags": risk_flags,
            "reason_code": "BOLLINGER_BANDS",
            "indicators": {
                "upper_band": upper_band,
                "lower_band": lower_band,
                "atr": atr,
                "volatility": vol_ratio
            }
        }
    
    def _calculate_atr(self, highs, lows, closes, period=14):
        """Calculate Average True Range."""
        if len(closes) < period + 1:
            return 0
        
        true_ranges = []
        for i in range(1, min(period + 1, len(closes))):
            high_low = highs[-i] - lows[-i]
            high_close = abs(highs[-i] - closes[-i-1])
            low_close = abs(lows[-i] - closes[-i-1])
            true_ranges.append(max(high_low, high_close, low_close))
        
        return np.mean(true_ranges)


class RiskEngine(BaseEngine):
    """Enhanced risk management with VaR and position sizing."""
    
    def __init__(self):
        super().__init__("RiskEngine")

    def analyze(self, data: dict) -> dict:
        closes = data.get('closes', [])
        if len(closes) < 20:
            return {"direction": "NEUTRAL", "confidence": 1.0, "risk_flags": [], "reason_code": "SAFE"}

        # Calculate returns
        returns = np.diff(closes[-20:]) / closes[-21:-1]
        
        # Value at Risk (95% confidence)
        var_95 = np.percentile(returns, 5)
        
        # Check for crash
        last_return = (closes[-1] - closes[-2]) / closes[-2]
        
        risk_flags = []
        confidence = 1.0
        
        if last_return < -0.05:  # 5% drop
            risk_flags.append("CRASH_DETECTED")
            confidence = 0.0
        elif last_return < -0.03:  # 3% drop
            risk_flags.append("HIGH_RISK")
            confidence = 0.5
        
        # Check VaR
        if var_95 < -0.05:
            risk_flags.append("HIGH_VAR")
            confidence *= 0.7
        
        return {
            "direction": "NEUTRAL",
            "confidence": confidence,
            "risk_flags": risk_flags,
            "reason_code": "SAFE" if not risk_flags else "UNSAFE",
            "metrics": {
                "var_95": var_95,
                "last_return": last_return
            }
        }


class MomentumEngine(BaseEngine):
    """Momentum-based trading with RSI and Stochastic."""
    
    def __init__(self):
        super().__init__("MomentumEngine")
    
    def analyze(self, data: dict) -> dict:
        closes = data.get('closes', [])
        highs = data.get('highs', closes)
        lows = data.get('lows', closes)
        
        if len(closes) < 14:
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "risk_flags": ["INSUFFICIENT_DATA"],
                "reason_code": "NO_DATA"
            }
        
        # RSI
        rsi = self._calculate_rsi(closes, 14)
        
        # Stochastic Oscillator
        stoch_k = self._calculate_stochastic(highs, lows, closes, 14)
        
        # Determine direction
        signals = []
        
        if rsi < 30:  # Oversold
            signals.append(1)
        elif rsi > 70:  # Overbought
            signals.append(-1)
        
        if stoch_k < 20:  # Oversold
            signals.append(1)
        elif stoch_k > 80:  # Overbought
            signals.append(-1)
        
        signal_sum = sum(signals)
        
        if signal_sum >= 1:
            direction = "LONG"
            confidence = 0.7
        elif signal_sum <= -1:
            direction = "SHORT"
            confidence = 0.7
        else:
            direction = "NEUTRAL"
            confidence = 0.5
        
        return {
            "direction": direction,
            "confidence": confidence,
            "risk_flags": [],
            "reason_code": "MOMENTUM",
            "indicators": {
                "rsi": rsi,
                "stochastic": stoch_k
            }
        }
    
    def _calculate_rsi(self, closes, period=14):
        """Calculate RSI."""
        if len(closes) < period + 1:
            return 50
        
        deltas = np.diff(closes[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_stochastic(self, highs, lows, closes, period=14):
        """Calculate Stochastic Oscillator %K."""
        if len(closes) < period:
            return 50
        
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]
        current_close = closes[-1]
        
        highest_high = max(recent_highs)
        lowest_low = min(recent_lows)
        
        if highest_high == lowest_low:
            return 50
        
        stoch_k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
        
        return stoch_k


class MeanReversionEngine(BaseEngine):
    """Mean reversion strategy using Z-score."""
    
    def __init__(self):
        super().__init__("MeanReversionEngine")
    
    def analyze(self, data: dict) -> dict:
        closes = data.get('closes', [])
        
        if len(closes) < 20:
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "risk_flags": ["INSUFFICIENT_DATA"],
                "reason_code": "NO_DATA"
            }
        
        # Calculate Z-score
        mean = np.mean(closes[-20:])
        std = np.std(closes[-20:])
        current_price = closes[-1]
        
        if std == 0:
            z_score = 0
        else:
            z_score = (current_price - mean) / std
        
        # Mean reversion logic
        if z_score > 2:  # Price too high
            direction = "SHORT"
            confidence = min(0.9, 0.6 + abs(z_score) * 0.1)
        elif z_score < -2:  # Price too low
            direction = "LONG"
            confidence = min(0.9, 0.6 + abs(z_score) * 0.1)
        else:
            direction = "NEUTRAL"
            confidence = 0.5
        
        return {
            "direction": direction,
            "confidence": confidence,
            "risk_flags": [],
            "reason_code": "MEAN_REVERSION",
            "indicators": {
                "z_score": z_score,
                "mean": mean,
                "std": std
            }
        }


class VolumeEngine(BaseEngine):
    """Volume-based analysis with OBV and VWAP."""
    
    def __init__(self):
        super().__init__("VolumeEngine")
    
    def analyze(self, data: dict) -> dict:
        closes = data.get('closes', [])
        volumes = data.get('volumes', [])
        highs = data.get('highs', closes)
        lows = data.get('lows', closes)
        
        if len(closes) < 20 or len(volumes) < 20:
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "risk_flags": ["INSUFFICIENT_DATA"],
                "reason_code": "NO_DATA"
            }
        
        # On-Balance Volume (OBV)
        obv = self._calculate_obv(closes, volumes)
        
        # VWAP (Volume Weighted Average Price)
        vwap = self._calculate_vwap(highs, lows, closes, volumes)
        
        current_price = closes[-1]
        
        # Determine direction
        direction = "NEUTRAL"
        confidence = 0.5
        
        if current_price > vwap and obv[-1] > obv[-5]:  # Price above VWAP and OBV rising
            direction = "LONG"
            confidence = 0.7
        elif current_price < vwap and obv[-1] < obv[-5]:  # Price below VWAP and OBV falling
            direction = "SHORT"
            confidence = 0.7
        
        return {
            "direction": direction,
            "confidence": confidence,
            "risk_flags": [],
            "reason_code": "VOLUME_ANALYSIS",
            "indicators": {
                "obv": obv[-1],
                "vwap": vwap
            }
        }
    
    def _calculate_obv(self, closes, volumes):
        """Calculate On-Balance Volume."""
        obv = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        return obv
    
    def _calculate_vwap(self, highs, lows, closes, volumes):
        """Calculate Volume Weighted Average Price."""
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        vwap = sum(tp * v for tp, v in zip(typical_prices, volumes)) / sum(volumes)
        return vwap
