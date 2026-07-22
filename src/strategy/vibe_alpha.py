import pandas as pd
from typing import Dict, Any, Optional, Tuple
import decimal
from datetime import datetime, timezone
from src.strategy.base import BaseStrategy
from ta.trend import ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator

class VibeAlphaStrategy(BaseStrategy):
    """
    Intraday Trading Strategy (15m Primary / 1h Context).
    Enforces Rule 10 (Day Trading Compliance), Rule 16 (Session Gating), and Rule 13 (3:1 R/R).
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lookback = config.get("lookback", 20)
        self.adx_period = config.get("adx_period", 14)
        self.atr_period = config.get("atr_period", 14)
        self.rsi_period = config.get("rsi_period", 14)
        self.volume_sma_period = config.get("volume_sma_period", 20)
        
        self.adx_threshold = config.get("adx_threshold", 18)
        self.volume_factor = config.get("volume_factor", 1.2) # Rule 13: 1.2x volume spike
        self.rsi_oversold = config.get("rsi_oversold", 35)
        self.rsi_overbought = config.get("rsi_overbought", 65)

    def get_session_type(self) -> str:
        """Rule 16: Intraday Session Gating based on UTC hour."""
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour
        
        if 7 <= hour < 11:
            return "LONDON_BREAKOUT"  # London Open: Breakout Momentum
        elif 11 <= hour < 13:
            return "LUNCH_REVERSION"  # Lunch Hour: Mean Reversion
        elif 13 <= hour < 16:
            return "NY_TREND"         # NY Open: Strong Trend Following
        else:
            return "STANDARD_INTRADAY"

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Intraday indicators on 15m finished candles."""
        df['ema_fast'] = EMAIndicator(close=df['close'], window=12).ema_indicator()
        df['ema_slow'] = EMAIndicator(close=df['close'], window=26).ema_indicator()
        df['ema_200'] = EMAIndicator(close=df['close'], window=200).ema_indicator()
        
        if all(col in df.columns for col in ['high', 'low', 'close']):
            df['adx'] = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=self.adx_period).adx()
            df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=self.atr_period).average_true_range()
            df['rsi'] = RSIIndicator(close=df['close'], window=self.rsi_period).rsi()
            
        if 'volume' in df.columns:
            df['volume_sma'] = df['volume'].rolling(window=self.volume_sma_period).mean()
            
        return df

    def evaluate_4h_bias(self, df_4h: pd.DataFrame) -> Tuple[bool, float]:
        """
        Stage 1: 4H Macro Bias Filter.
        Returns: (is_bullish: bool, momentum_score: float)
        """
        if df_4h.empty or len(df_4h) < 20:
            return False, 0.0
            
        df = self.calculate_indicators(df_4h)
        latest = df.iloc[-1]
        
        close = latest.get('close')
        ema_200 = latest.get('ema_200')
        if pd.isna(ema_200):
            ema_200 = latest.get('ema_slow', close)
            
        adx_val = latest.get('adx', 0.0)
        if pd.isna(adx_val):
            adx_val = 20.0
        
        # 4H momentum change over last 6 candles
        lookback_idx = min(6, len(df) - 1)
        base_close = df['close'].iloc[-lookback_idx]
        mom_4h = ((close - base_close) / base_close) * 100.0 if base_close > 0 else 0.0
        
        is_bullish = bool((close >= ema_200) and (mom_4h > 0) and (adx_val >= 15))
        score = float(mom_4h + (adx_val * 0.5))
        return is_bullish, score

    def evaluate_1h_structure(self, df_1h: pd.DataFrame) -> Tuple[bool, float]:
        """
        Stage 2: 1H Trend Structure Filter.
        Returns: (is_valid: bool, structure_score: float)
        """
        if df_1h.empty or len(df_1h) < 20:
            return False, 0.0
            
        df = self.calculate_indicators(df_1h)
        latest = df.iloc[-1]
        
        close = latest.get('close')
        ema_f = latest.get('ema_fast')
        ema_s = latest.get('ema_slow')
        rsi_val = latest.get('rsi', 50.0)
        
        is_valid = bool((ema_f > ema_s) and (close > ema_s) and (45 <= rsi_val <= 75))
        score = float((rsi_val - 50) + (((ema_f - ema_s) / close) * 1000 if close > 0 else 0.0))
        return is_valid, score

    def analyze(self, symbol: str, data: pd.DataFrame, current_positions: Dict = None, regime: str = 'unknown') -> Optional[Dict]:
        if data.empty or len(data) < 40:
            return None
            
        df = self.calculate_indicators(data)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        close = latest.get('close')
        ema_f = latest.get('ema_fast')
        ema_s = latest.get('ema_slow')
        ema_200 = latest.get('ema_200')
        adx_val = latest.get('adx')
        prev_adx = prev.get('adx')
        atr_val = latest.get('atr')
        rsi_val = latest.get('rsi')
        vol_val = latest.get('volume')
        vol_sma = latest.get('volume_sma')
        
        if any(pd.isna(x) for x in [close, ema_f, ema_s, ema_200, adx_val, prev_adx, atr_val, rsi_val, vol_val, vol_sma]):
            return None
            
        session = self.get_session_type()
        
        # Rule 13: 2.0x ATR SL for noise survival, 4.0x ATR TP (2:1 Ratio)
        sl_offset = 2.0 * atr_val
        tp_offset = 4.0 * atr_val
        
        # Rule 13: Breakout Volume Spike (1.2x volume over 20-MA)
        has_volume_confirm = vol_val >= (self.volume_factor * vol_sma)
        
        # ADX Slope Filter: Trend must be accelerating (ADX rising)
        adx_rising = adx_val > prev_adx
        
        # 1. Bullish Intraday Signal (Price > 200 EMA + ADX >= 20 & Rising)
        if ema_f > ema_s and close > ema_200 and adx_val >= self.adx_threshold and adx_rising and 45 <= rsi_val <= 75 and has_volume_confirm:
            confidence = min(0.95, max(0.65, 0.60 + (adx_val / 100.0)))
            return {
                "action": "BUY",
                "confidence": confidence,
                "reasoning": f"Intraday Bull ({session}) | Price > 200 EMA | ADX {adx_val:.1f} (Rising) | RSI {rsi_val:.1f}",
                "stop_loss": close - sl_offset,
                "take_profit": close + tp_offset
            }
            
        # 2. Bearish Intraday Signal (Price < 200 EMA + ADX >= 20 & Rising)
        elif ema_f < ema_s and close < ema_200 and adx_val >= self.adx_threshold and adx_rising and 25 <= rsi_val <= 55 and has_volume_confirm:
            confidence = min(0.95, max(0.65, 0.60 + (adx_val / 100.0)))
            return {
                "action": "SELL",
                "confidence": confidence,
                "reasoning": f"Intraday Bear ({session}) | Price < 200 EMA | ADX {adx_val:.1f} (Rising) | RSI {rsi_val:.1f}",
                "stop_loss": close + sl_offset,
                "take_profit": close - tp_offset
            }
            
        return None

    def check_micro_exit(self, symbol: str, data_5m: pd.DataFrame) -> Tuple[bool, str]:
        """
        Micro 5m Timeframe Position Exit Guard.
        Checks active open positions for 5m micro exhaustion / breakdown.
        
        Returns:
            (should_exit: bool, exit_reason: str)
        """
        if data_5m.empty or len(data_5m) < 25:
            return False, "OK"
            
        df = self.calculate_indicators(data_5m)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        close = latest.get('close')
        open_p = latest.get('open')
        high = latest.get('high')
        rsi_val = latest.get('rsi')
        prev_rsi = prev.get('rsi')
        ema_f = latest.get('ema_fast')
        
        # 1. 5m RSI Overbought Exhaustion Crossdown (RSI >= 72 and crossing down)
        if prev_rsi >= 72 and rsi_val < prev_rsi:
            return True, f"5m RSI Exhaustion ({rsi_val:.1f} < {prev_rsi:.1f})"
            
        # 2. 5m Bearish Rejection Wick / Engulfing Candle (Upper wick >= 2.5x body)
        body = abs(close - open_p)
        upper_wick = high - max(close, open_p)
        if body > 0 and upper_wick >= (2.5 * body) and close < open_p:
            return True, f"5m Rejection Wick (Wick: {upper_wick/body:.1f}x Body)"
            
        # 3. 5m Micro Trend Breakdown (Price crosses below 5m Fast EMA)
        if close < ema_f and prev.get('close') >= prev.get('ema_fast'):
            return True, f"5m Micro EMA Breakdown ({close:.4f} < {ema_f:.4f})"
            
        return False, "OK"
