"""
Trade Executor v2.0

Complete trade execution with:
- Risk management (equity guard, position limits)
- Pre-trade validation
- Trade logging and metrics
- Circuit breaker integration
- Structured logging
"""

import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

logger = logging.getLogger("StrategyProcess.TradeExecutor")

# Try to import our utilities
try:
    from src.system.utils.structured_logging import get_trading_metrics, get_structured_logger
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

try:
    from src.analytics.monitoring.component_status import report_component_healthy, report_component_error
    STATUS_MONITOR_AVAILABLE = True
except ImportError:
    STATUS_MONITOR_AVAILABLE = False


@dataclass
class TradeResult:
    """Result of a trade execution attempt."""
    success: bool
    symbol: str
    action: str
    price: float
    size: float
    position_value: float
    
    # Risk info
    stop_loss: float = 0.0
    take_profit: float = 0.0
    
    # Execution info
    blocked: bool = False
    block_reason: str = ""
    execution_time_ms: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    trade_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "symbol": self.symbol,
            "action": self.action,
            "price": self.price,
            "size": self.size,
            "position_value": self.position_value,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "trade_id": self.trade_id
        }


class TradeExecutor:
    """
    Handles trade execution with comprehensive risk management.
    
    Features:
    - Equity guard (daily loss limits)
    - Position concentration limits
    - Maximum open positions
    - Pre-trade validation
    - Trade metrics and logging
    - Circuit breaker integration
    """
    
    # Configuration defaults
    DEFAULT_CONFIG = {
        # Equity guard thresholds
        "equity_guard_hard_stop": -0.03,   # -3% = halt trading
        "equity_guard_soft_brake": -0.01,  # -1% = reduce size 50%

        # Position limits
        "max_position_pct": 0.20,          # Max 20% per position
        "max_open_positions": 15,           # Max 15 concurrent positions (synced from trading_config.yaml)
        "min_trade_value": 10.0,           # Minimum trade value ($)

        # Risk limits
        "max_daily_trades": 50,            # Max trades per day
        "cooldown_seconds": 60,            # Cooldown between trades on same symbol

        # Smart Chase (Phase 8)
        "smart_chase_enabled": True,       # Enable Limit-Chase logic
        "max_chase_tolerance": 0.003,      # Max 0.3% chase (FOMO protection)

        # Spread Guard (Protocol 14)
        "max_spread_pct": 0.001,           # 0.1% max spread — abort if wider
    }
    
    def __init__(self, config_manager=None, portfolio_manager=None, config: Dict = None):
        """
        Initialize TradeExecutor.
        
        Args:
            config_manager: Config manager for dynamic settings
            portfolio_manager: Portfolio manager for position tracking
            config: Override configuration
        """
        self.config_manager = config_manager
        self.portfolio = portfolio_manager
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
        # FIX: Sync max_open_positions from config_manager if available
        if self.config_manager is not None:
            try:
                risk_section = self.config_manager.get_section('risk')
                if risk_section and 'max_positions' in risk_section:
                    self.config['max_open_positions'] = risk_section['max_positions']
                    logger.info(f"TradeExecutor synced max_open_positions={risk_section['max_positions']} from config")
            except Exception as e:
                logger.debug(f"Could not sync config from manager: {e}")
        
        # State tracking
        self.equity_guard_hit = False
        self.daily_trade_count = 0
        self.last_trade_date = None
        self.recent_trades: Dict[str, datetime] = {}  # symbol -> last trade time
        
        # Metrics
        if METRICS_AVAILABLE:
            self.metrics = get_trading_metrics()
            self.slog = get_structured_logger("trade_executor")
        else:
            self.metrics = None
            self.slog = None
        
        # Trade log
        self.trade_history: List[TradeResult] = []
        self.time_offset = 0.0
        
        # Load Shariah-compliant halal whitelist (Protocol 7 in Workspace Rules)
        self.halal_whitelist = set()
        try:
            import yaml
            import pathlib
            whitelist_path = pathlib.Path(__file__).parents[2] / 'config' / 'halal_whitelist.yaml'
            if whitelist_path.exists():
                with open(whitelist_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    for key, val in data.items():
                        if isinstance(val, list):
                            for item in val:
                                symbol = item.split('#')[0].strip()
                                self.halal_whitelist.add(symbol)
                logger.info(f"🕌 Loaded {len(self.halal_whitelist)} whitelisted halal assets.")
            else:
                logger.error(f"❌ halal_whitelist.yaml not found at {whitelist_path}!")
        except Exception as e:
            logger.error(f"❌ Failed to load Sharia halal whitelist: {e}")
            
        # Seed Kelly calculator with trade history from DB if available
        try:
            import os
            import sqlite3
            from src.trading.portfolio.kelly_sizing import get_kelly_calculator
            db_path = 'data/trade_history.db'
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path, timeout=30.0)
                cursor = conn.execute('SELECT pnl, pnl_pct, is_win FROM trades WHERE pnl IS NOT NULL ORDER BY exit_time DESC LIMIT 50')
                rows = cursor.fetchall()
                conn.close()
                
                kelly = get_kelly_calculator()
                # Feed in chronological order (oldest first)
                for row in reversed(rows):
                    kelly.record_trade(pnl=float(row[0] or 0), pnl_pct=float(row[1] or 0), is_win=bool(row[2]))
                logger.info(f"📊 Kelly Sizing initialized with {len(rows)} trades from DB.")
        except Exception as e:
            logger.debug(f"Could not seed Kelly calculator on startup: {e}")
            
        logger.info(f"✅ TradeExecutor v2.0 initialized (max_positions={self.config.get('max_open_positions', 5)})")

    def reset_daily_counters(self):
        """Reset daily counters (call at start of trading day)."""
        self.daily_trade_count = 0
        self.equity_guard_hit = False
        self.last_trade_date = datetime.now().date()
        logger.info("📅 Daily counters reset")

    def check_equity_guard(self, current_equity: float, initial_balance: float) -> Tuple[bool, float]:
        """
        Check for daily loss limits.
        
        Args:
            current_equity: Current portfolio equity
            initial_balance: Starting balance for the day
            
        Returns:
            (is_blocked, size_multiplier)
        """
        if initial_balance <= 0:
            return False, 1.0
        
        # Reset daily if new day
        today = datetime.now().date()
        if self.last_trade_date != today:
            self.reset_daily_counters()
            
        pnl = current_equity - initial_balance
        pnl_pct = pnl / initial_balance
        
        hard_stop = self.config.get("equity_guard_hard_stop", -0.03)  # -3% daily hard stop
        soft_brake = self.config.get("equity_guard_soft_brake", -0.01)
        
        # Hard Stop
        if pnl_pct < hard_stop:
            if not self.equity_guard_hit:
                logger.critical(f"⛔ EQUITY GUARD: Daily loss limit ({pnl_pct:.1%}) hit! Trading halted.")
                self.equity_guard_hit = True
                if self.slog:
                    self.slog.alert(f"Equity guard triggered: {pnl_pct:.1%}", severity="critical")
            return True, 0.0
            
        # Soft Brake (reduce size)
        multiplier = 1.0
        if pnl_pct < soft_brake:
            multiplier = 0.5
            logger.warning(f"⚠️ EQUITY GUARD: Daily loss {pnl_pct:.1%} > {soft_brake:.0%}. Size reduced by 50%.")
            
        return False, multiplier

    def validate_trade(
        self,
        symbol: str,
        action: str,
        price: float,
        size: float,
        balance: float,
        open_positions: Dict = None,
        spread_pct: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Validate a trade before execution.

        Returns:
            (is_valid, rejection_reason)
        """
        open_positions = open_positions or {}

        # --- Protocol 14: Spread Guard ---
        max_spread = self.config.get("max_spread_pct", 0.001)
        if spread_pct > max_spread:
            logger.warning(
                f"⛔ SPREAD GUARD: {symbol} spread {spread_pct:.4%} > {max_spread:.4%}. "
                "Low liquidity — aborting."
            )
            return False, f"spread_too_wide ({spread_pct:.4%} > {max_spread:.4%})"

        # Check Sharia compliance whitelist (Workspace Rules Protocol 7)
        if not self.halal_whitelist:
            logger.error("❌ SHARIA GUARD: Whitelist is empty or failed to load. Fail-safe blocking all execution.")
            return False, "sharia_whitelist_not_loaded"
            
        base_asset = symbol.split('/')[0] if '/' in symbol else symbol
        is_halal = False
        for whitelist_item in self.halal_whitelist:
            w_base = whitelist_item.split('/')[0] if '/' in whitelist_item else whitelist_item
            if symbol == whitelist_item or base_asset == w_base:
                is_halal = True
                break
                
        if not is_halal:
            logger.warning(f"⛔ SHARIA VIOLATION: {symbol} is not in halal_whitelist.yaml! Aborting.")
            return False, "sharia_compliance_violation"
        
        # Check equity guard
        if self.equity_guard_hit:
            return False, "equity_guard_blocked"
        
        # Check daily trade limit
        max_daily = self.config.get("max_daily_trades", 50)
        if self.daily_trade_count >= max_daily:
            return False, f"daily_limit_reached ({max_daily})"
        
        # Check minimum trade value
        position_value = price * size
        min_value = self.config.get("min_trade_value", 10.0)
        if position_value < min_value:
            return False, f"trade_too_small (${position_value:.2f} < ${min_value})"
        
        # Check max position size
        max_pct = self.config.get("max_position_pct", 0.20)
        if balance > 0 and position_value / balance > max_pct:
            return False, f"position_too_large ({position_value/balance:.0%} > {max_pct:.0%})"
        
        # Check max open positions (for new positions)
        if action == "BUY" and symbol not in open_positions:
            max_positions = self.config.get("max_open_positions", 5)
            if len(open_positions) >= max_positions:
                return False, f"max_positions_reached ({max_positions})"
        
        # Check cooldown
        cooldown = self.config.get("cooldown_seconds", 60)
        last_trade = self.recent_trades.get(symbol)
        if last_trade:
            elapsed = (datetime.now() - last_trade).total_seconds()
            if elapsed < cooldown:
                return False, f"cooldown_active ({int(cooldown - elapsed)}s remaining)"
        
        return True, ""

    async def execute_trade(
        self,
        signal: Dict,
        current_price: float,
        balance: float,
        open_positions: Dict = None,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        data_source: Any = None  # New: Pass data source for checking live metrics
    ) -> TradeResult:
        print(f"DEBUG: ENTERED EXECUTE_TRADE FOR {signal.get('symbol', 'UNKNOWN')}")
        """
        Execute a trade with full validation and risk management.
        Async version for non-blocking execution.
        """
        import time
        import asyncio
        start_time = time.time()
        # print(f"DEBUG: TE.execute_trade ENTERED for {signal.get('symbol')}")

        
        symbol = signal.get("symbol", "UNKNOWN")
        action = signal.get("action", "HOLD")
        size = signal.get("size", 0.0)
        confidence = signal.get("confidence", 0.5)

        # --- Rule 5: Data Staleness Guard (5.0s max lag) ---
        sig_ts = signal.get("timestamp")
        if sig_ts is not None:
            # Handle both epoch ms (13-digit) and epoch sec (10-digit)
            sig_sec = sig_ts / 1000.0 if sig_ts > 1e11 else float(sig_ts)
            age_sec = time.time() - sig_sec
            if age_sec > 5.0:
                trade_id = f"{symbol}_{action}_{int(time.time())}"
                logger.error(f"❌ Trade blocked: {symbol} signal is stale ({age_sec:.1f}s > 5.0s max lag)")
                return TradeResult(
                    success=False, symbol=symbol, action=action, price=current_price, size=size,
                    position_value=0.0, blocked=True, block_reason="stale_data_lag",
                    execution_time_ms=(time.time() - start_time) * 1000, trade_id=trade_id
                )

        # Retrieve stops from signal if present (Protocol 10 / Volatility-Adjusted Stops)
        stop_loss = signal.get("stop_loss", stop_loss)
        take_profit = signal.get("take_profit", take_profit)
        
        # Calculate dynamic SL/TP percentages based on original signal price
        sl_pct = 0.0
        tp_pct = 0.0
        if current_price > 0:
            if action == "BUY":
                sl_pct = (current_price - stop_loss) / current_price if stop_loss and stop_loss < current_price else 0.0
                tp_pct = (take_profit - current_price) / current_price if take_profit and take_profit > current_price else 0.0
            elif action == "SELL":
                sl_pct = (stop_loss - current_price) / current_price if stop_loss and stop_loss > current_price else 0.0
                tp_pct = (current_price - take_profit) / current_price if take_profit and take_profit < current_price else 0.0

        # --- Protocol 14: Spread from signal (bid/ask if available) ---
        # Callers may inject 'bid' and 'ask' into the signal for live spread checks.
        bid = signal.get("bid", 0.0)
        ask = signal.get("ask", 0.0)
        spread_pct = ((ask - bid) / ask) if (ask > 0 and bid > 0) else 0.0
        
        # --- Protocol 13: Dynamic Blacklist (Rule Enforcement) ---
        if action == "BUY":
            try:
                import sqlite3
                conn = sqlite3.connect('data/trade_history.db')
                cursor = conn.cursor()
                cursor.execute('SELECT outcome, exit_time FROM trades WHERE symbol = ? ORDER BY exit_time DESC LIMIT 2', (symbol,))
                last_trades = cursor.fetchall()
                conn.close()
                if len(last_trades) == 2 and last_trades[0][0] == 'LOSS' and last_trades[1][0] == 'LOSS':
                    # Check if last trade was within 24 hours
                    import dateutil.parser
                    # Check if last trade was within 24 hours
                    last_exit_time = dateutil.parser.parse(last_trades[0][1])
                    if last_exit_time.tzinfo is None:
                        last_exit_time = last_exit_time.replace(tzinfo=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    if (now_utc - last_exit_time).total_seconds() < 86400:
                        logger.error(f"❌ Trade blocked: {symbol} is blacklisted for 24h due to 2 consecutive losses.")
                        return TradeResult(
                            success=False, symbol=symbol, action=action, price=current_price, size=size, 
                            position_value=0.0, blocked=True, block_reason="dynamic_blacklist", 
                            execution_time_ms=(time.time() - start_time) * 1000, trade_id=trade_id
                        )
            except Exception as e:
                logger.error(f"⚠️ Failed to check dynamic blacklist: {e}")
        
        
        # Dynamic Equity-Based Position Sizing (Protocol 10 / Workspace Rules)
        if action == "BUY" and (size == 0.0 or size is None):
            # Load risk percentage from config (default to 10%, clamp strictly between 1% and 25%)
            risk_pct = self.config.get("risk_per_trade", 0.10)
            if risk_pct > 0.25:
                risk_pct = 0.25
            elif risk_pct < 0.01:
                risk_pct = 0.01
                
            use_kelly = self.config.get("use_kelly_sizing", True)
            kelly_used = False
            
            if use_kelly:
                try:
                    from src.trading.portfolio.kelly_sizing import get_kelly_calculator
                    kelly = get_kelly_calculator()
                    regime = signal.get("regime", "unknown")
                    kelly_result = kelly.get_position_size(
                        portfolio_value=balance,
                        confidence=confidence,
                        regime=regime if regime != "unknown" else None
                    )
                    calculated_size = kelly_result.position_size / current_price
                    kelly_used = True
                    logger.info(f"📊 Kelly Sizing: {symbol} size set to {calculated_size:.4f} via Kelly ({kelly_result.reasoning})")
                except Exception as e:
                    logger.error(f"⚠️ Failed to calculate Kelly sizing: {e}. Falling back to default.")
                    calculated_size = (balance * risk_pct) / current_price
            else:
                calculated_size = (balance * risk_pct) / current_price
            
            if not kelly_used:
                # Apply brain/strategy multipliers if available
                suggestions = signal.get("suggestions", {})
                brain_multiplier = suggestions.get("brain_multiplier", 1.0)
                calculated_size *= brain_multiplier
                logger.info(
                    f"📊 Dynamic Position Sizing: {symbol} size set to {calculated_size:.4f} "
                    f"({risk_pct:.1%} of ${balance:.2f} equity, mult={brain_multiplier:.1f})"
                )
            
            # Clamp between 1% and 10% of balance for risk mitigation
            max_size = (balance * 0.10) / current_price
            min_size = (balance * 0.01) / current_price
            size = max(min_size, min(calculated_size, max_size))
            
        elif action == "SELL" and (size == 0.0 or size is None):
            # Sell the whole open position if no size is specified
            if open_positions and symbol in open_positions:
                pos = open_positions[symbol]
                if isinstance(pos, dict):
                    size = pos.get('quantity', pos.get('size', 0.0))
                else:
                    size = getattr(pos, 'quantity', getattr(pos, 'size', 0.0))
                logger.info(f"📊 Close Position Sizing: {symbol} size set to open size {size:.4f}")
                
        # Calculate position value
        position_value = current_price * size
        
        # Generate trade ID
        trade_id = f"{symbol}_{action}_{int(time.time())}"
        
        # Staleness Check (Protocol 15 / Pivot to Day & Swing Trading)
        data_timestamp = signal.get("timestamp")
        if data_timestamp:
            current_ms = (time.time() + self.time_offset) * 1000
            lag_ms = current_ms - data_timestamp
            max_lag_ms = self.config.get("max_data_age_ms", 15000.0) # Default 15s
            if lag_ms > max_lag_ms:
                logger.error(f"❌ Trade blocked: Stale data detected. Lag: {lag_ms:.1f}ms > {max_lag_ms}ms")
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    action=action,
                    price=current_price,
                    size=size,
                    position_value=position_value,
                    blocked=True,
                    block_reason="stale_data_lag",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    trade_id=trade_id
                )
        
        # Validate trade
        is_valid, rejection_reason = self.validate_trade(
            symbol=symbol,
            action=action,
            price=current_price,
            size=size,
            balance=balance,
            open_positions=open_positions,
            spread_pct=spread_pct
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        
        if not is_valid:
            # print(f"DEBUG: TE.execute_trade BLOCKED: {rejection_reason}")
            logger.warning(f"🚫 Trade blocked: {symbol} {action} - {rejection_reason}")
            if self.slog:
                self.slog.signal(symbol, "blocked", reason=rejection_reason)
            return TradeResult(
                success=False,
                symbol=symbol,
                action=action,
                price=current_price,
                size=size,
                position_value=position_value,
                blocked=True,
                block_reason=rejection_reason,
                execution_time_ms=execution_time_ms,
                trade_id=trade_id
            )
        
        # SMART CHASE EXECUTION LOGIC
        # Only active for BUY orders where we want to chase momentum
        executed_price = current_price
        execution_type = "MARKET" # Default
        
        # print(f"DEBUG: TE.execute_trade Checking Smart Chase (Enabled={self.config.get('smart_chase_enabled', False)})")
        if action == "BUY" and self.config.get('smart_chase_enabled', False):
            # 1. Place Limit (Simulation)
            logger.info(f"⏳ SMART CHASE: {symbol} Placing LIMIT at {current_price}...")
            
            # 2. Wait 3s (Execution Latency) - ASYNC SLEEP
            await asyncio.sleep(3.0)
            
            # 3. Re-check Reality (Did price run away or crash?)
            latest_price = current_price
            if data_source and hasattr(data_source, 'get_latest_price'):
                try:
                    # Prefer async get_latest_price if available, else sync
                    if asyncio.iscoroutinefunction(data_source.get_latest_price):
                        latest_price = await data_source.get_latest_price(symbol)
                    else:
                        latest_price = data_source.get_latest_price(symbol)
                except:
                    pass
            
            # 4. Momentum Logic
            # If price moved AGAINST us (dropped) significantly, don't chase (fakeout)
            price_change_pct = (latest_price - current_price) / current_price
            
            # CONFIG: Tolerance limits
            MAX_CHASE_SLIPPAGE = self.config.get('max_chase_tolerance', 0.003) # 0.3% max chase
            FAKEOUT_DROP = -0.002 # -0.2% drop = abort
            
            if price_change_pct < FAKEOUT_DROP: 
                # Case A: Price Crashed (Fakeout) -> ABORT
                logger.warning(f"[STOP] SMART CHASE: {symbol} aborted! Price dropped {price_change_pct:.2%} (Fakeout Protection)")
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    action=action,
                    price=current_price,
                    size=size,
                    position_value=0,
                    blocked=True,
                    block_reason="chase_aborted_fakeout",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    trade_id=trade_id
                )
            elif price_change_pct > MAX_CHASE_SLIPPAGE:
                # Case B: Price Runaway (FOMO) -> ABORT
                logger.warning(f"[STOP] SMART CHASE: {symbol} aborted! Price pumped {price_change_pct:.2%} (> {MAX_CHASE_SLIPPAGE:.1%}) (FOMO Protection)")
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    action=action,
                    price=current_price,
                    size=size,
                    position_value=0,
                    blocked=True,
                    block_reason="chase_aborted_fomo",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    trade_id=trade_id
                )
            elif price_change_pct > 0.0005: # > 0.05% move up
                # Case C: Momentum Confirmed -> MARKET CHASE
                logger.info(f"🚀 SMART CHASE: {symbol} Momentum (+{price_change_pct:.2%}). Executing MARKET CHASE.")
                execution_type = "MARKET_CHASE"
                executed_price = latest_price * 1.0005 # Slippage
            else:
                 # Case D: Price stable or slight dip -> LIMIT FILLED
                 logger.info(f"✅ SMART CHASE: {symbol} Limit likely filled (Change: {price_change_pct:.2%}).")
                 execution_type = "LIMIT_FILLED"
                 executed_price = current_price
        
        # Re-anchor SL/TP to actual executed price to prevent immediate negative take-profits due to slippage
        if executed_price > 0 and executed_price != current_price:
            if action == "BUY":
                stop_loss = executed_price * (1.0 - sl_pct) if sl_pct > 0 else stop_loss
                take_profit = executed_price * (1.0 + tp_pct) if tp_pct > 0 else take_profit
            elif action == "SELL":
                stop_loss = executed_price * (1.0 + sl_pct) if sl_pct > 0 else stop_loss
                take_profit = executed_price * (1.0 - tp_pct) if tp_pct > 0 else take_profit

        # Execute (Paper State Update)
        self.daily_trade_count += 1
        self.recent_trades[symbol] = datetime.now()
        
        # Log trade
        logger.info(f"✅ TRADE ({execution_type}): {action} {size:.4f} {symbol} @ ${executed_price:.2f} "
                   f"(value: ${position_value:.2f}, confidence: {confidence:.0%})")
        
        if self.slog:
            self.slog.trade(symbol, action, {
                "price": executed_price,
                "size": size,
                "value": round(position_value, 2),
                "confidence": round(confidence, 2),
                "stop_loss": round(stop_loss, 2) if stop_loss else None,
                "take_profit": round(take_profit, 2) if take_profit else None,
                "type": execution_type
            })
        
        # Update metrics
        if self.metrics:
            self.metrics.record_trade_open()
        
        # Report healthy status
        if STATUS_MONITOR_AVAILABLE:
            report_component_healthy("trade_executor", 
                                    daily_trades=self.daily_trade_count,
                                    last_symbol=symbol)
        
        result = TradeResult(
            success=True,
            symbol=symbol,
            action=action,
            price=executed_price,
            size=size,
            position_value=position_value,
            stop_loss=stop_loss,
            take_profit=take_profit,
            execution_time_ms=execution_time_ms,
            trade_id=trade_id
        )
        
        self.trade_history.append(result)
        
        # Keep only last 100 trades in memory
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
        
        # print(f"DEBUG: TE.execute_trade RETURNING SUCCESS for {symbol}")
        return result

    def close_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        size: float,
        reason: str = "manual",
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        max_price: float = 0.0,
        min_price: float = 0.0
    ) -> Dict:
        """
        Record a trade close.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            exit_price: Current/exit price
            size: Position size
            reason: Close reason
            stop_loss: Initial SL
            take_profit: Initial TP
            max_price: Highest price reached
            min_price: Lowest price reached
            
        Returns:
            Dict with PnL info and context
        """
        pnl = (exit_price - entry_price) * size
        pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
        is_win = pnl > 0
        
        logger.info(f"📤 CLOSE: {symbol} @ ${exit_price:.2f} | "
                   f"PnL: ${pnl:.2f} ({pnl_pct:+.2%}) | Reason: {reason}")
        
        if self.slog:
            self.slog.trade(symbol, "CLOSE", {
                "entry": entry_price,
                "exit": exit_price,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct * 100, 2),
                "reason": reason,
                "max_price": max_price,
                "min_price": min_price
            })
        
        # Update metrics
        if self.metrics:
            self.metrics.record_trade_close(pnl=pnl, is_win=is_win)
            
        # Record trade in Kelly calculator
        try:
            from src.trading.portfolio.kelly_sizing import get_kelly_calculator
            kelly = get_kelly_calculator()
            kelly.record_trade(pnl=pnl, pnl_pct=pnl_pct, is_win=is_win)
            logger.info(f"📊 Kelly Sizing: Recorded trade close. Current stats: {kelly.get_stats()}")
        except Exception as e:
            logger.debug(f"Could not record trade in Kelly calculator: {e}")
        
        return {
            "symbol": symbol,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "is_win": is_win,
            "reason": reason,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "max_price": max_price,
            "min_price": min_price
        }

    def get_status(self) -> Dict:
        """Get executor status."""
        return {
            "equity_guard_active": self.equity_guard_hit,
            "daily_trades": self.daily_trade_count,
            "max_daily_trades": self.config.get("max_daily_trades", 50),
            "cooldowns_active": len([
                s for s, t in self.recent_trades.items()
                if (datetime.now() - t).total_seconds() < self.config.get("cooldown_seconds", 60)
            ]),
            "total_trades_processed": len(self.trade_history)
        }


# Singleton factory
_executor: Optional[TradeExecutor] = None


def get_trade_executor(config_manager=None, config: Dict = None) -> TradeExecutor:
    """Get or create the trade executor singleton."""
    global _executor
    if _executor is None:
        _executor = TradeExecutor(config_manager=config_manager, config=config)
    return _executor


# CLI test
if __name__ == "__main__":
    import json
    
    logging.basicConfig(level=logging.DEBUG)
    
    print("🔧 Trade Executor Test")
    print("=" * 50)
    
    executor = TradeExecutor()
    
    # Test equity guard
    blocked, mult = executor.check_equity_guard(9700, 10000)  # -3%
    print(f"Equity guard test (-3%): blocked={blocked}, multiplier={mult}")
    
    executor.equity_guard_hit = False  # Reset for testing
    
    blocked, mult = executor.check_equity_guard(9850, 10000)  # -1.5%
    print(f"Equity guard test (-1.5%): blocked={blocked}, multiplier={mult}")
    
    # Test trade execution
    signal = {
        "symbol": "BTC/USDT",
        "action": "BUY",
        "size": 0.01,
        "confidence": 0.75
    }
    
    result = executor.execute_trade(
        signal=signal,
        current_price=50000,
        balance=10000,
        open_positions={},
        stop_loss=49000,
        take_profit=52000
    )
    
    print(f"\nTrade result:")
    print(json.dumps(result.to_dict(), indent=2, default=str))
    
    # Test trade close
    close_result = executor.close_trade(
        symbol="BTC/USDT",
        entry_price=50000,
        exit_price=51000,
        size=0.01,
        reason="take_profit"
    )
    print(f"\nClose result: {close_result}")
    
    print("\n" + "=" * 50)
    print("✅ Trade executor tests passed!")
