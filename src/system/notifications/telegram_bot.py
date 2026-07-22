"""
Interactive Telegram Bot for Intradyne
Listens for commands and provides real-time trading information.

Run: python src/notifications/telegram_bot.py
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path (3 levels up: notifications -> system -> src -> Intradyne)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, PROJECT_ROOT)

# Reconfigure stdout to use UTF-8 on Windows to prevent UnicodeEncodeError with emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Credentials
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8387457203:AAE1bs0RKhfywDQ12OB4qq1zbEN6D_Xt-N8")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1067921171")
ALLOWED_USERS = [int(CHAT_ID)] if CHAT_ID else []

# Trading state (shared with trading engine)
trading_state = {
    'paused': False,
    'pause_reason': None,
    'paused_at': None
}


class IntradyneTelegramBot:
    """
    Interactive Telegram bot for trading management.
    
    Commands:
        /start, /help - Show help
        /status - Trading status & health
        /balance - Current P&L  
        /trades - Recent trades
        /sentiment - Market sentiment
        /pause - Pause trading
        /resume - Resume trading
    """
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    
    def __init__(self):
        self.token = BOT_TOKEN
        self.api_url = self.BASE_URL.format(token=self.token)
        self.last_update_id = 0
        self.running = False
        
        # Command handlers
        self.commands = {
            'start': self.cmd_help,
            'help': self.cmd_help,
            'menu': self.cmd_menu,
            'status': self.cmd_status,
            'balance': self.cmd_balance,
            'trades': self.cmd_trades,
            'daily': self.cmd_daily,
            'weekly': self.cmd_weekly,
            'performance': self.cmd_performance,
            'sentiment': self.cmd_sentiment,
            'news': self.cmd_news,
            'portfolio': self.cmd_portfolio,
            'pause': self.cmd_pause,
            'resume': self.cmd_resume,
            'health': self.cmd_health,
            'settings': self.cmd_settings,
            'app': self.cmd_app,
            'positions': self.cmd_positions,
            'setkeys': self.cmd_setkeys,
            'start_engine': self.cmd_start_engine,
            'stop_engine': self.cmd_stop_engine,
            'toggle_mode': self.cmd_toggle_mode,
            'reset_equity': self.cmd_reset_equity,
        }
    
    def send_message(self, chat_id: int, text: str, 
                     parse_mode: str = "Markdown",
                     reply_markup: dict = None) -> bool:
        """Send message to chat."""
        try:
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
            }
            if reply_markup:
                payload['reply_markup'] = json.dumps(reply_markup)
            
            with httpx.Client(timeout=10) as client:
                r = client.post(f"{self.api_url}/sendMessage", json=payload)
                return r.json().get('ok', False)
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False
    
    def get_updates(self, offset: int = 0) -> list:
        """Get new messages."""
        try:
            with httpx.Client(timeout=30) as client:
                r = client.get(
                    f"{self.api_url}/getUpdates",
                    params={'offset': offset, 'timeout': 20}
                )
                data = r.json()
                return data.get('result', [])
        except Exception as e:
            logger.debug(f"Failed to get Telegram updates: {e}")
            return []
    
    # ==================== COMMAND HANDLERS ====================
    
    def cmd_help(self, chat_id: int, args: list = None) -> None:
        """Show available commands."""
        text = """
🤖 *Intradyne Trading Bot* v2.5

📊 *Trading*
/status - System status & health
/balance - Current P&L and equity
/positions - Show active open positions
/trades - Recent trade history
/pause ⏸️ /resume ▶️ - Control trading
/start_engine 🚀 - Start background engine
/stop_engine 🛑 - Stop background engine
/setkeys - Set API keys (Secured via atomic write)

📈 *Reports*
/daily - Today's trade summary
/weekly - Weekly performance report
/performance - Detailed stats & metrics

🧠 *Analysis*
/sentiment - Market sentiment & Fear/Greed
/news - Latest crypto news
/portfolio - Optimal MPT allocation

⚙️ *System*
/health - System health check
/settings - Current configuration
/menu - Quick action buttons

🔔 *Auto-Alerts:*
• Trade executions
• Stop loss / Take profit
• Drawdown warnings
• Daily summaries (23:55)
"""
        keyboard = {
            'keyboard': [
                [{'text': '🟢 Positions'}, {'text': '📋 Trades'}, {'text': '💰 Balance'}],
                [{'text': '📊 Status'}, {'text': '🏥 Health'}, {'text': '🎭 Sentiment'}],
                [{'text': '⏸️ Pause'}, {'text': '▶️ Resume'}],
                [{'text': '🚀 Start Engine'}, {'text': '🛑 Stop Engine'}]
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
        self.send_message(chat_id, text, reply_markup=keyboard)
    
    def cmd_menu(self, chat_id: int, args: list = None) -> None:
        """Show quick action menu with buttons."""
        text = "📱 *Quick Actions*\n\nTap a button below:"
        
        # Inline keyboard
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '🟢 Positions', 'callback_data': 'positions'},
                    {'text': '📋 Trades', 'callback_data': 'trades'},
                    {'text': '📈 Daily', 'callback_data': 'daily'}
                ],
                [
                    {'text': '💰 Balance', 'callback_data': 'balance'},
                    {'text': '📊 Status', 'callback_data': 'status'},
                    {'text': '⚙️ Settings', 'callback_data': 'settings'}
                ],
                [
                    {'text': '🧠 Sentiment', 'callback_data': 'sentiment'},
                    {'text': '📰 News', 'callback_data': 'news'},
                    {'text': '🏥 Health', 'callback_data': 'health'}
                ],
                [
                    {'text': '⏸️ Pause', 'callback_data': 'pause'},
                    {'text': '▶️ Resume', 'callback_data': 'resume'}
                ],
                [
                    {'text': '🚀 Start Engine', 'callback_data': 'start_engine'},
                    {'text': '🛑 Stop Engine', 'callback_data': 'stop_engine'}
                ]
            ]
        }
        
        self.send_message(chat_id, text, reply_markup=keyboard)
            
    def cmd_positions(self, chat_id: int, args: list = None) -> None:
        """Get currently active positions."""
        try:
            live_state = {}
            if os.path.exists("data/live_state.json"):
                try:
                    with open("data/live_state.json", "r") as f:
                        live_state = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to read live_state.json: {e}")
            
            positions = live_state.get("positions", [])
            
            if not positions:
                self.send_message(chat_id, "📭 No active positions open")
                return
            
            text = "🟢 *Active Open Positions*\n\n"
            for pos in positions:
                symbol = pos.get('symbol', 'UNKNOWN')
                side = pos.get('side', 'BUY')
                entry_price = pos.get('entry_price', 0.0)
                current_price = pos.get('current_price', 0.0)
                qty = pos.get('quantity', 0.0)
                pnl = pos.get('unrealized_pnl', 0.0)
                pnl_pct = pos.get('unrealized_pnl_pct', 0.0) * 100
                sl = pos.get('stop_loss', 0.0)
                tp = pos.get('take_profit', 0.0)
                
                pos_val = qty * current_price
                side_emoji = "🟢" if side == 'BUY' else "🔴"
                pnl_emoji = "📈" if pnl >= 0 else "📉"
                
                text += f"{side_emoji} *{symbol}* ({side})\n"
                text += f"   Size: `{qty:.4f}` (${pos_val:,.2f})\n"
                text += f"   Entry: `${entry_price:.4f}` | Current: `${current_price:.4f}`\n"
                text += f"   SL: `${sl:.4f}` | TP: `${tp:.4f}`\n"
                text += f"   Unrealized P&L: {pnl_emoji} `${pnl:+.2f}` ({pnl_pct:+.2f}%)\n\n"
                
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_status(self, chat_id: int, args: list = None) -> None:
        """Get trading status."""
        try:
            is_paused = os.path.exists("data/trader.paused")
            status_emoji = "⏸️" if is_paused else "🟢"
            
            live_state = {}
            if os.path.exists("data/live_state.json"):
                try:
                    with open("data/live_state.json", "r") as f:
                        live_state = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to read live_state.json: {e}")
            
            status_str = "PAUSED" if is_paused else live_state.get("status", "ONLINE")
            balance = live_state.get("balance", 10000.0)
            equity = live_state.get("equity", 10000.0)
            unrealized_pnl = live_state.get("unrealized_pnl", 0.0)
            active_positions = len(live_state.get("positions", []))
            
            last_update = "N/A"
            if "last_update" in live_state:
                last_update = datetime.fromtimestamp(live_state["last_update"]).strftime('%Y-%m-%d %H:%M:%S')
                
            text = f"""
{status_emoji} *Trading Status*

● Status: `{status_str}`
● Active Positions: `{active_positions}`
● Cash Balance: `${balance:,.2f}`
● Portfolio Equity: `${equity:,.2f}`
● Unrealized P&L: `${unrealized_pnl:+.2f}`
● Last Update: `{last_update}`

{"⏸️ *TRADING PAUSED VIA TELEGRAM*" if is_paused else "▶️ Trading active"}
"""
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_balance(self, chat_id: int, args: list = None) -> None:
        """Get current balance and P&L."""
        try:
            live_state = {}
            if os.path.exists("data/live_state.json"):
                try:
                    with open("data/live_state.json", "r") as f:
                        live_state = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to read live_state.json: {e}")
            
            balance = live_state.get("balance", 10000.0)
            equity = live_state.get("equity", 10000.0)
            realized_pnl = live_state.get("realized_pnl", 0.0)
            unrealized_pnl = live_state.get("unrealized_pnl", 0.0)
            drawdown = live_state.get("max_drawdown", 0.0) * 100
            
            total_pnl = realized_pnl + unrealized_pnl
            pnl_emoji = "📈" if total_pnl >= 0 else "📉"
            
            text = f"""
💰 *Balance & P&L Summary*

● Cash Balance: `${balance:,.2f}`
● Total Equity: `${equity:,.2f}`

{pnl_emoji} *Performance Overview*
● Unrealized P&L: `${unrealized_pnl:+.2f}`
● Realized P&L: `${realized_pnl:+.2f}`
● Max Drawdown: `{drawdown:.2f}%`
● Total P&L: `${total_pnl:+.2f}`
"""
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_trades(self, chat_id: int, args: list = None) -> None:
        """Get recent trades."""
        try:
            live_state = {}
            if os.path.exists("data/live_state.json"):
                try:
                    with open("data/live_state.json", "r") as f:
                        live_state = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to read live_state.json: {e}")
            
            recent = live_state.get("recent_trades", [])
            
            if not recent:
                self.send_message(chat_id, "📭 No recent completed trades found")
                return
            
            # Show last 5 trades, newest first
            trades = recent[-5:]
            trades.reverse()
            
            text = "📋 *Recent Completed Trades*\n\n"
            for t in trades:
                side = t.get('side', 'BUY')
                outcome = t.get('outcome', 'LOSS')
                emoji = "🟢" if outcome == "WIN" else "🔴"
                pnl = t.get('pnl', 0.0)
                pnl_pct = t.get('pnl_pct', 0.0) * 100
                symbol = t.get('symbol', 'UNKNOWN')
                entry_price = t.get('entry_price', 0.0)
                exit_price = t.get('exit_price', 0.0)
                reason = t.get('exit_reason', 'STOP_LOSS')
                
                text += f"{emoji} *{symbol}* ({side})\n"
                text += f"   Entry: `${entry_price:.4f}` | Exit: `${exit_price:.4f}`\n"
                text += f"   PnL: `${pnl:+.2f}` ({pnl_pct:+.2f}%) | Reason: `{reason}`\n\n"
            
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def _load_recent_trades(self) -> list:
        """Load recent trades from data/live_state.json."""
        state_file = os.path.join(PROJECT_ROOT, "data", "live_state.json")
        if not os.path.exists(state_file):
            return []
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            return state.get('recent_trades', [])
        except (json.JSONDecodeError, IOError):
            return []

    def cmd_daily(self, chat_id: int, args: list = None) -> None:
        """Get daily trade summary from live_state.json."""
        try:
            from datetime import date, timedelta

            all_trades = self._load_recent_trades()
            if not all_trades:
                self.send_message(chat_id, "📭 No trade data in live state")
                return

            today_str = date.today().strftime('%Y-%m-%d')
            yesterday_str = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

            today_trades = [t for t in all_trades if t.get('exit_time', '').startswith(today_str)]
            if today_trades:
                day_label = "Today"
                trades = today_trades
            else:
                trades = [t for t in all_trades if t.get('exit_time', '').startswith(yesterday_str)]
                day_label = "Yesterday"

            if not trades:
                self.send_message(chat_id, "📭 No completed trades today or yesterday")
                return

            wins = [t for t in trades if t.get('pnl', 0) > 0]
            losses = [t for t in trades if t.get('pnl', 0) <= 0]
            total_pnl = sum(t.get('pnl', 0) for t in trades)
            win_rate = len(wins) / len(trades) * 100 if trades else 0

            best_trade = max(trades, key=lambda x: x.get('pnl', 0)) if trades else None
            worst_trade = min(trades, key=lambda x: x.get('pnl', 0)) if trades else None

            # Symbol breakdown
            symbol_pnl = {}
            for t in trades:
                sym = t.get('symbol', 'Unknown')
                symbol_pnl[sym] = symbol_pnl.get(sym, 0) + t.get('pnl', 0)

            text = f"""📊 *{day_label}'s Trade Summary*

📈 *Overview*
• Total Trades: {len(trades)}
• Winning: {len(wins)} | Losing: {len(losses)}
• Win Rate: {win_rate:.1f}%
• Total P&L: ${total_pnl:+.4f}

"""

            if symbol_pnl:
                text += "💹 *By Asset*\n"
                for sym, pnl in sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True):
                    emoji = "🟢" if pnl > 0 else "🔴"
                    text += f"{emoji} {sym.replace('/USDT', '')}: ${pnl:+.4f}\n"
                text += "\n"

            if best_trade:
                text += f"🏆 Best: {best_trade.get('symbol', '?')} ${best_trade.get('pnl', 0):+.4f}\n"
            if worst_trade:
                text += f"📉 Worst: {worst_trade.get('symbol', '?')} ${worst_trade.get('pnl', 0):+.4f}\n"

            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_weekly(self, chat_id: int, args: list = None) -> None:
        """Get weekly trade summary from live_state.json."""
        try:
            from datetime import date, timedelta

            all_trades = self._load_recent_trades()
            if not all_trades:
                self.send_message(chat_id, "📭 No trade data in live state")
                return

            # Filter last 7 days
            cutoff = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
            week_trades = [t for t in all_trades if t.get('exit_time', '') >= cutoff]

            if not week_trades:
                self.send_message(chat_id, "📭 No trades in the last 7 days")
                return

            wins = [t for t in week_trades if t.get('pnl', 0) > 0]
            total_pnl = sum(t.get('pnl', 0) for t in week_trades)
            win_rate = len(wins) / len(week_trades) * 100

            # Daily breakdown
            daily_pnls = {}
            for t in week_trades:
                day = t.get('exit_time', '')[:10]
                daily_pnls[day] = daily_pnls.get(day, 0) + t.get('pnl', 0)

            text = f"""📆 *Weekly Summary (7 Days)*

📊 *Totals*
• Trades: {len(week_trades)}
• Win Rate: {win_rate:.1f}%
• Total P&L: ${total_pnl:+.4f}
• Avg/Day: ${total_pnl/7:+.4f}

📅 *Daily Breakdown*
"""
            for day, pnl in sorted(daily_pnls.items(), reverse=True):
                emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                text += f"{emoji} {day}: ${pnl:+.4f}\n"

            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_performance(self, chat_id: int, args: list = None) -> None:
        """Get detailed performance metrics from live_state.json."""
        try:
            all_trades = self._load_recent_trades()
            if not all_trades:
                self.send_message(chat_id, "📭 No trade data available")
                return

            # Also load summary stats from live_state
            state_file = os.path.join(PROJECT_ROOT, "data", "live_state.json")
            with open(state_file, 'r') as f:
                state = json.load(f)

            wins = [t for t in all_trades if t.get('pnl', 0) > 0]
            losses = [t for t in all_trades if t.get('pnl', 0) <= 0]

            total_pnl = sum(t.get('pnl', 0) for t in all_trades)
            avg_win = sum(t.get('pnl', 0) for t in wins) / len(wins) if wins else 0
            avg_loss = sum(t.get('pnl', 0) for t in losses) / len(losses) if losses else 0
            win_rate = len(wins) / len(all_trades) * 100

            total_win_pnl = sum(t.get('pnl', 0) for t in wins)
            total_loss_pnl = abs(sum(t.get('pnl', 0) for t in losses))
            profit_factor = total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else 999

            best = max(all_trades, key=lambda x: x.get('pnl', 0))
            worst = min(all_trades, key=lambda x: x.get('pnl', 0))

            # Engine-level stats
            engine_total = state.get('total_trades', len(all_trades))
            engine_wr = state.get('win_rate', win_rate / 100)
            max_dd = state.get('max_drawdown', 0)
            realized = state.get('realized_pnl', total_pnl)

            text = f"""📈 *Performance Metrics*

📊 *Overview*
• Total Trades: {engine_total}
• Win Rate: {engine_wr*100:.1f}%
• Profit Factor: {profit_factor:.2f}
• Max Drawdown: {max_dd*100:.2f}%

💰 *P&L*
• Realized: ${realized:+.4f}
• Avg Win: ${avg_win:+.4f}
• Avg Loss: ${avg_loss:+.4f}

🎯 *Extremes (Recent {len(all_trades)} trades)*
• 🏆 Best: {best.get('symbol','?')} ${best.get('pnl',0):+.4f}
• 📉 Worst: {worst.get('symbol','?')} ${worst.get('pnl',0):+.4f}

📐 *Risk Metrics*
• Wins: {len(wins)} | Losses: {len(losses)}
• Gross Profit: ${total_win_pnl:+.4f}
• Gross Loss: ${total_loss_pnl:.4f}
"""
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_settings(self, chat_id: int, args: list = None) -> None:
        """Show API key configuration instructions."""
        try:
            env_path = ".env"
            has_api_key = False
            has_secret = False
            
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "BITGET_API_KEY=" in content:
                        # Ensure it's not just an empty assignment like BITGET_API_KEY=
                        import re
                        has_api_key = bool(re.search(r'BITGET_API_KEY=\S+', content))
                    if "BITGET_SECRET_KEY=" in content:
                        import re
                        has_secret = bool(re.search(r'BITGET_SECRET_KEY=\S+', content))
            
            status_api = "✅ Configured" if has_api_key else "❌ Missing"
            status_sec = "✅ Configured" if has_secret else "❌ Missing"
            
            text = f"""⚙️ *System Settings*

*API Configuration Status:*
• API Key: {status_api}
• Secret Key: {status_sec}

_To update keys: `/setkeys <API_KEY> <API_SECRET>`_

Use the buttons below to manage your engine:
"""
            
            # Read current mode
            current_mode = "paper"
            config_path = "config/trading_params.yaml"
            if os.path.exists(config_path):
                import yaml
                try:
                    with open(config_path, "r") as f:
                        config = yaml.safe_load(f)
                        current_mode = config.get("engine", {}).get("mode", "paper").lower()
                except:
                    pass
                    
            mode_toggle_text = "🟢 Switch to LIVE" if current_mode == "paper" else "🟡 Switch to PAPER"
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': mode_toggle_text, 'callback_data': 'toggle_mode'}],
                    [{'text': '🔄 Reset Paper Equity ($10k)', 'callback_data': 'reset_equity'}]
                ]
            }
            
            self.send_message(chat_id, text, reply_markup=keyboard)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_sentiment(self, chat_id: int, args: list = None) -> None:
        """Get market sentiment from engine collected data."""
        try:
            live_state = {}
            if os.path.exists("data/live_state.json"):
                try:
                    with open("data/live_state.json", "r") as f:
                        live_state = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to read live_state.json: {e}")
            
            mc = live_state.get("market_condition", {})
            active_symbols = live_state.get("active_symbols", 0)
            
            if not mc:
                self.send_message(chat_id, "📭 Market condition data not yet available from the engine. Ensure the engine is running.")
                return
            
            regime = mc.get("current_regime", "Unknown")
            favorable_pct = mc.get("favorable_pct", 0) * 100
            
            # Map regime to emoji
            if "bull" in regime and "low_vol" in regime:
                emoji = "🚀"
            elif "bull" in regime:
                emoji = "📈"
            elif "bear" in regime and "high_vol" in regime:
                emoji = "💥"
            elif "bear" in regime:
                emoji = "📉"
            elif "sideways" in regime:
                emoji = "🦀"
            else:
                emoji = "❓"
                
            text = f"""
🎭 *Internal Market Condition*

{emoji} **Current Regime**: `{regime}`
✅ **Favorable Time**: `{favorable_pct:.1f}%`
📊 **Active Symbols Tracking**: `{active_symbols}`

📈 *Regime Distribution (Recent History):*
"""
            pcts = mc.get("regime_percentages", {})
            for r, pct in sorted(pcts.items(), key=lambda x: x[1], reverse=True):
                text += f"• `{r}`: {pct*100:.1f}%\n"

            text += "\n_Data is generated natively by the Intradyne Regime Detector._"

            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_news(self, chat_id: int, args: list = None) -> None:
        """Get latest crypto news from CryptoPanic."""
        try:
            from src.data.news_fetcher import get_news_fetcher
            fetcher = get_news_fetcher()
            
            # Get symbol from args or default to BTC
            symbol = args[0].upper() if args else "BTC"
            
            news = fetcher.fetch_cryptopanic_news(symbol=symbol, limit=5)
            
            if not news:
                self.send_message(chat_id, f"📭 No news found for {symbol}\n\n_CryptoPanic API may be rate-limited_")
                return
            
            text = f"📰 *Latest {symbol} News*\n\n"
            for i, article in enumerate(news, 1):
                sentiment_emoji = "🟢" if article.get('sentiment') == 'bullish' else "🔴" if article.get('sentiment') == 'bearish' else "⚪"
                title = article.get('title', 'No title')[:60]
                if len(article.get('title', '')) > 60:
                    title += "..."
                source = article.get('source', 'Unknown')
                text += f"{sentiment_emoji} {i}. {title}\n   _via {source}_\n\n"
            
            text += f"💡 _Use /news ETH for Ethereum news_"
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_portfolio(self, chat_id: int, args: list = None) -> None:
        """Get optimal portfolio allocation."""
        try:
            from src.trading.portfolio_optimizer import get_portfolio_optimizer
            
            optimizer = get_portfolio_optimizer()
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
            
            result = optimizer.optimize_portfolio(symbols, method='max_sharpe', days=30)
            
            text = f"""
📊 *Optimal Portfolio (MPT)*

📈 Expected Return: {result.expected_return*100:.1f}%
📉 Volatility: {result.volatility*100:.1f}%
⭐ Sharpe Ratio: {result.sharpe_ratio:.2f}

💰 *Recommended Allocation:*
"""
            for symbol, weight in result.weights.items():
                pct = weight * 100
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                text += f"`{symbol}` {pct:.0f}%\n"
            
            text += f"\n_Based on 30-day data, Max Sharpe method_"
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_health(self, chat_id: int, args: list = None) -> None:
        """Get system health."""
        try:
            from src.analytics.monitoring.health_monitor import get_health_monitor
            monitor = get_health_monitor()
            health = monitor.get_full_health()
            
            score = health['score']
            if score >= 80:
                emoji = "🟢"
            elif score >= 50:
                emoji = "🟡"
            else:
                emoji = "🔴"
            
            text = f"""
🏥 *System Health*

{emoji} Score: {score}/100 ({health['status'].upper()})
⏱️ Uptime: {health['uptime_seconds'] // 3600}h {(health['uptime_seconds'] % 3600) // 60}m

"""
            # Add alerts
            if health.get('alerts'):
                text += "⚠️ *Alerts:*\n"
                for alert in health['alerts']:
                    a_emoji = "🚨" if alert['type'] == 'critical' else "⚠️"
                    text += f"{a_emoji} {alert['message']}\n"
            else:
                text += "✅ No active alerts"
            
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_pause(self, chat_id: int, args: list = None) -> None:
        """Pause trading."""
        try:
            trading_state['paused'] = True
            trading_state['pause_reason'] = 'Manual pause via Telegram'
            trading_state['paused_at'] = datetime.now().isoformat()

            # Write pause flag file
            os.makedirs("data", exist_ok=True)
            with open("data/trader.paused", "w") as f:
                f.write(f"PAUSED_AT: {trading_state['paused_at']}")
            
            # Also try to update live_state.json status field
            if os.path.exists("data/live_state.json"):
                try:
                    with open("data/live_state.json", "r") as f:
                        live_state = json.load(f)
                    live_state["status"] = "PAUSED"
                    # Write atomically
                    with open("data/live_state.json.tmp", "w") as f:
                        json.dump(live_state, f, indent=2)
                    os.replace("data/live_state.json.tmp", "data/live_state.json")
                except Exception as e:
                    logger.error(f"Failed to update state file status: {e}")

            text = """
⏸️ *Trading PAUSED*

All new trade signals are suspended.
Existing positions remain open and will continue to be monitored for stop-loss and take-profit exits.
Use /resume to continue trading.
"""
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
    
    def cmd_resume(self, chat_id: int, args: list = None) -> None:
        """Resume trading."""
        try:
            trading_state['paused'] = False
            trading_state['pause_reason'] = None
            trading_state['paused_at'] = None

            # Remove pause flag file
            if os.path.exists("data/trader.paused"):
                os.remove("data/trader.paused")
            
            # Also try to update live_state.json status field
            if os.path.exists("data/live_state.json"):
                try:
                    with open("data/live_state.json", "r") as f:
                        live_state = json.load(f)
                    live_state["status"] = "ONLINE"
                    # Write atomically
                    with open("data/live_state.json.tmp", "w") as f:
                        json.dump(live_state, f, indent=2)
                    os.replace("data/live_state.json.tmp", "data/live_state.json")
                except Exception as e:
                    logger.error(f"Failed to update state file status: {e}")

            text = """
▶️ *Trading RESUMED*

Bot will now evaluate strategies and execute new trades based on signals.
"""
            self.send_message(chat_id, text)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")
            
    def cmd_app(self, chat_id: int, args: list = None) -> None:
        """Launch Telegram Mini App."""
        try:
            url = os.getenv("TELEGRAM_MINIAPP_URL", "http://localhost:8000/miniapp")
            text = "📱 *Intradyne Telegram Mini App*\n\nTap the button below to launch the interactive trading dashboard:"
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '📊 Launch Dashboard', 'web_app': {'url': url}}
                    ]
                ]
            }
            self.send_message(chat_id, text, reply_markup=keyboard)
        except Exception as e:
            self.send_message(chat_id, f"❌ Error: {e}")

    def cmd_start_engine(self, chat_id: int, args: list = None) -> None:
        """Start the background trading engine."""
        try:
            import psutil
            import subprocess
            # Check if main.py is already running
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'python' in proc.info.get('name', '').lower() and 'src/engine/main.py' in ' '.join(cmdline).replace('\\', '/'):
                    self.send_message(chat_id, f"⚠️ Engine is already running (PID: {proc.info['pid']})")
                    return
            
            # Start the engine as a detached process
            env = os.environ.copy()
            # If using venv, ensure python uses it
            python_exe = ".venv\\Scripts\\python.exe" if os.path.exists(".venv\\Scripts\\python.exe") else "python"
            
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                [python_exe, "src/engine/main.py"],
                creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=env
            )
            self.send_message(chat_id, "🚀 *Engine Starting...* (Background process spawned)")
            
            # Auto-resume just in case
            if os.path.exists("data/trader.paused"):
                os.remove("data/trader.paused")
        except Exception as e:
            self.send_message(chat_id, f"❌ Failed to start engine: {e}")

    def cmd_stop_engine(self, chat_id: int, args: list = None) -> None:
        """Gracefully stop the background trading engine."""
        try:
            with open("data/trader.shutdown", "w") as f:
                f.write(f"SHUTDOWN_TRIGGERED_AT: {datetime.now().isoformat()}")
            self.send_message(chat_id, "🛑 *Shutdown signal sent.* Engine will finish current loop and exit.")
        except Exception as e:
            self.send_message(chat_id, f"❌ Error triggering shutdown: {e}")

    def cmd_setkeys(self, chat_id: int, args: list = None) -> None:
        """Set API keys via Atomic Write."""
        if not args or len(args) != 2:
            self.send_message(chat_id, "⚠️ *Usage:* /setkeys <API_KEY> <API_SECRET>\n\n_Note: Keys will be securely atomic-written to .env_")
            return
            
        api_key, api_secret = args
        env_path = ".env"
        tmp_path = ".env.tmp"
        
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    
            # Update or append
            key_found = False
            secret_found = False
            for i, line in enumerate(lines):
                if line.startswith("BITGET_API_KEY="):
                    lines[i] = f"BITGET_API_KEY={api_key}\n"
                    key_found = True
                elif line.startswith("BITGET_SECRET_KEY="):
                    lines[i] = f"BITGET_SECRET_KEY={api_secret}\n"
                    secret_found = True
                    
            if not key_found:
                lines.append(f"BITGET_API_KEY={api_key}\n")
            if not secret_found:
                lines.append(f"BITGET_SECRET_KEY={api_secret}\n")
                
            # Protocol 3: Atomic Write
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
                f.flush()
                os.fsync(f.fileno())
                
            os.replace(tmp_path, env_path)
            
            self.send_message(chat_id, "✅ *API Keys Successfully Saved*\n\nEngine credentials updated via atomic write. If the engine is running, you must /stop_engine and /start_engine to reload them.")
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            self.send_message(chat_id, f"❌ Failed to save keys: {e}")
            
    def cmd_toggle_mode(self, chat_id: int, args: list = None) -> None:
        """Toggle between LIVE and PAPER trading modes."""
        try:
            config_path = "config/trading_params.yaml"
            if not os.path.exists(config_path):
                self.send_message(chat_id, "❌ Error: config/trading_params.yaml not found.")
                return
                
            with open(config_path, "r") as f:
                lines = f.readlines()
                
            new_mode = "paper"
            for i, line in enumerate(lines):
                if line.strip().startswith("mode:") and "paper" in line.lower():
                    lines[i] = line.replace("paper", "live", 1).replace("PAPER", "LIVE", 1)
                    new_mode = "live"
                    break
                elif line.strip().startswith("mode:") and "live" in line.lower():
                    lines[i] = line.replace("live", "paper", 1).replace("LIVE", "PAPER", 1)
                    new_mode = "paper"
                    break
                    
            with open(config_path, "w") as f:
                f.writelines(lines)
                
            emoji = "🟢" if new_mode == "live" else "🟡"
            self.send_message(chat_id, f"{emoji} *Trading mode switched to {new_mode.upper()}*\n\n⚠️ You must /stop_engine and /start_engine for the change to take effect.")
        except Exception as e:
            self.send_message(chat_id, f"❌ Failed to toggle mode: {e}")

    def cmd_reset_equity(self, chat_id: int, args: list = None) -> None:
        """Reset paper trading equity to $10,000."""
        try:
            # 0. Shut down engine gracefully so it doesn't overwrite our reset from its RAM
            import time
            with open("data/shutdown.signal", "w") as f:
                f.write("RESET")
            time.sleep(3)
            
            # 1. Archive database instead of wiping to preserve history
            db_path = "data/trade_history.db"
            if os.path.exists(db_path):
                import shutil
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_path = f"data/trade_history_archive_{timestamp}.db"
                shutil.move(db_path, archive_path)
                
            # 2. Reset live_state.json
            state_path = "data/live_state.json"
            if os.path.exists(state_path):
                with open(state_path, "r") as f:
                    state = json.load(f)
                
                state['balance'] = 10000.0
                state['equity'] = 10000.0
                state['initial_balance'] = 10000.0
                state['peak_equity'] = 10000.0
                state['max_drawdown'] = 0.0
                state['realized_pnl'] = 0.0
                state['unrealized_pnl'] = 0.0  # Added
                state['total_trades'] = 0
                state['winning_trades'] = 0
                state['recent_trades'] = []
                state['positions'] = {}  # Add this to clear positions on reset
                
                with open(state_path, "w") as f:
                    json.dump(state, f, indent=2)
                    
            self.send_message(chat_id, "✅ *Paper Equity Reset to $10,000*\n\nDatabase wiped and JSON state reset. Please /start_engine to begin a fresh session.")
        except Exception as e:
            self.send_message(chat_id, f"❌ Failed to reset equity: {e}")

    # ==================== MAIN LOOP ====================
    
    def process_update(self, update: dict) -> None:
        """Process a single update."""
        # Handle callback queries (inline button presses) FIRST
        callback = update.get('callback_query', {})
        if callback:
            self.handle_callback(callback)
            return

        message = update.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        user_id = message.get('from', {}).get('id')
        text = message.get('text', '')
        
        if not chat_id or not text:
            return
        
        # Security: Only respond to allowed users
        if ALLOWED_USERS and user_id not in ALLOWED_USERS:
            logger.warning(f"Unauthorized user: {user_id}")
            return
        
        # Map persistent keyboard buttons to command handlers
        button_map = {
            '📊 status': 'status',
            '💰 balance': 'balance',
            '🟢 positions': 'positions',
            '📋 trades': 'trades',
            '⏸️ pause': 'pause',
            '▶️ resume': 'resume',
            '🚀 start engine': 'start_engine',
            '🛑 stop engine': 'stop_engine',
            '🏥 health': 'health',
            '🎭 sentiment': 'sentiment'
        }
        
        clean_text = text.strip().lower()
        if clean_text in button_map:
            command = button_map[clean_text]
            handler = self.commands.get(command)
            if handler:
                handler(chat_id, [])
                return
        
        # Parse command
        if text.startswith('/'):
            parts = text[1:].split()
            command = parts[0].lower().split('@')[0]  # Remove bot mention
            args = parts[1:] if len(parts) > 1 else []
            
            handler = self.commands.get(command)
            if handler:
                handler(chat_id, args)
            else:
                self.send_message(chat_id, f"❓ Unknown command: /{command}\nUse /help for available commands")
        
        # Handle callback queries (inline button presses)
        callback = update.get('callback_query', {})
        if callback:
            self.handle_callback(callback)
    
    def handle_callback(self, callback: dict) -> None:
        """Handle inline keyboard button presses."""
        try:
            chat_id = callback.get('message', {}).get('chat', {}).get('id')
            callback_id = callback.get('id')
            data = callback.get('data', '')
            
            # Answer callback to remove loading state
            with httpx.Client(timeout=10) as client:
                client.post(f"{self.api_url}/answerCallbackQuery", 
                           json={'callback_query_id': callback_id})
            
            # Execute the corresponding command
            handler = self.commands.get(data)
            if handler and chat_id:
                handler(chat_id, [])
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    def run(self) -> None:
        """Start polling for updates."""
        print("🤖 Intradyne Telegram Bot Started!")
        print(f"📱 Listening for commands from user {CHAT_ID}")
        print("=" * 50)
        print("Commands: /status /balance /trades /daily /sentiment /pause /resume /help")
        print("\nPress Ctrl+C to stop\n")
        
        self.running = True
        last_daily_sent = None
        
        while self.running:
            try:
                updates = self.get_updates(self.last_update_id + 1)
                
                for update in updates:
                    self.last_update_id = update['update_id']
                    self.process_update(update)
                
                # Check for scheduled daily summary (send at midnight)
                from datetime import date
                import time
                now = datetime.now()
                today = date.today()
                
                # Send daily summary once per day around midnight (23:59)
                if now.hour == 23 and now.minute >= 55 and last_daily_sent != today:
                    self.send_scheduled_daily_summary()
                    last_daily_sent = today
                    
            except KeyboardInterrupt:
                print("\n👋 Bot stopped")
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                import time
                time.sleep(5)
    
    def send_scheduled_daily_summary(self):
        """Send automatic daily summary."""
        try:
            # Use cmd_daily to generate the summary
            self.cmd_daily(int(CHAT_ID), None)
            print("📱 Scheduled daily summary sent")
        except Exception as e:
            logger.error(f"Scheduled daily summary error: {e}")


def get_trading_state() -> Dict[str, Any]:
    """Get current trading state for external access."""
    return trading_state.copy()


def is_trading_paused() -> bool:
    """Check if trading is paused."""
    return trading_state['paused']


def enforce_single_instance(port: int = 49999):
    """Ensure only one instance of the Telegram bot runs at any time by binding a local socket lock."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
    except socket.error:
        print(f"⚠️ Intradyne Telegram Bot is already running (Port {port} locked). Exiting duplicate instance.")
        sys.exit(0)
    return s


# CLI entry point
if __name__ == "__main__":
    _instance_lock = enforce_single_instance(49999)
    logging.basicConfig(level=logging.INFO)
    bot = IntradyneTelegramBot()
    bot.run()
