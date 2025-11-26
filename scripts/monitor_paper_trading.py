"""
Paper Trading Monitor & Auto-Restart Service
Keeps the paper trading bot running 24/7 with automatic restart on crashes.
"""

import subprocess
import time
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'paper_trading_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class PaperTradingMonitor:
    """
    Monitors and auto-restarts the paper trading bot.
    """
    
    def __init__(self, script_path: str, check_interval: int = 60):
        """
        Initialize monitor.
        
        Args:
            script_path: Path to the paper trading script
            check_interval: Health check interval in seconds
        """
        self.script_path = script_path
        self.check_interval = check_interval
        self.process = None
        self.restart_count = 0
        self.last_restart = None
        self.is_running = True
        
    def start_bot(self):
        """Start the paper trading bot."""
        try:
            logger.info("🚀 Starting paper trading bot...")
            
            # Start the bot as a subprocess
            self.process = subprocess.Popen(
                [sys.executable, self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.restart_count += 1
            self.last_restart = datetime.now()
            
            logger.info(f"✅ Paper trading bot started (PID: {self.process.pid})")
            logger.info(f"   Total restarts: {self.restart_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            return False
    
    def check_health(self) -> bool:
        """Check if the bot is still running."""
        if self.process is None:
            return False
        
        # Check if process is still alive
        poll = self.process.poll()
        
        if poll is not None:
            # Process has terminated
            logger.warning(f"⚠️  Bot process terminated with code {poll}")
            
            # Log stderr if available
            try:
                stderr = self.process.stderr.read()
                if stderr:
                    logger.error(f"Bot stderr: {stderr}")
            except:
                pass
            
            return False
        
        return True
    
    def restart_bot(self):
        """Restart the bot after a crash."""
        logger.info("♻️  Restarting paper trading bot...")
        
        # Kill old process if still running
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except:
                try:
                    self.process.kill()
                except:
                    pass
        
        # Wait a bit before restarting
        time.sleep(5)
        
        # Start new instance
        return self.start_bot()
    
    def run(self):
        """Main monitoring loop."""
        logger.info("="*70)
        logger.info("PAPER TRADING MONITORING SERVICE")
        logger.info("="*70)
        logger.info(f"Script: {self.script_path}")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"Started at: {datetime.now()}")
        logger.info("="*70)
        
        # Initial start
        if not self.start_bot():
            logger.error("Failed to start bot initially")
            return
        
        try:
            while self.is_running:
                # Wait for check interval
                time.sleep(self.check_interval)
                
                # Check health
                is_healthy = self.check_health()
                
                if not is_healthy:
                    logger.warning("❌ Bot health check failed!")
                    
                    # Check if we're restarting too frequently
                    if self.last_restart:
                        time_since_restart = (datetime.now() - self.last_restart).total_seconds()
                        
                        if time_since_restart < 120:  # Less than 2 minutes
                            logger.error("⚠️  Bot crashed too quickly after restart!")
                            logger.error("   Waiting 60 seconds before retry...")
                            time.sleep(60)
                    
                    # Restart
                    if not self.restart_bot():
                        logger.error("Failed to restart bot!")
                        logger.error("Waiting 120 seconds before retry...")
                        time.sleep(120)
                        
                        # Try again
                        if not self.restart_bot():
                            logger.critical("Multiple restart failures! Stopping monitor.")
                            break
                else:
                    # Log healthy status periodically
                    uptime = (datetime.now() - self.last_restart).total_seconds() if self.last_restart else 0
                    logger.debug(f"✅ Bot healthy (uptime: {uptime/60:.1f} min)")
        
        except KeyboardInterrupt:
            logger.info("\n🛑 Monitor stopped by user")
        except Exception as e:
            logger.error(f"Monitor error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the monitor and bot."""
        logger.info("Stopping paper trading monitor...")
        self.is_running = False
        
        if self.process:
            try:
                logger.info("Terminating bot process...")
                self.process.terminate()
                self.process.wait(timeout=10)
                logger.info("✅ Bot stopped cleanly")
            except:
                logger.warning("Force killing bot process...")
                try:
                    self.process.kill()
                except:
                    pass
        
        logger.info("="*70)
        logger.info("MONITORING SESSION SUMMARY")
        logger.info("="*70)
        logger.info(f"Total restarts: {self.restart_count}")
        if self.last_restart:
            runtime = (datetime.now() - self.last_restart).total_seconds()
            logger.info(f"Last session uptime: {runtime/60:.1f} minutes")
        logger.info("="*70)


def main():
    """Main entry point."""
    # Path to the paper trading bot script (using improved version)
    bot_script = "scripts/run_paper_trading_improved.py"
    
    if not os.path.exists(bot_script):
        print(f"❌ Error: Bot script not found: {bot_script}")
        print("   Creating it now...")
        # Fallback to original if improved doesn't exist
        bot_script = "scripts/run_paper_trading.py"
        if not os.path.exists(bot_script):
            print(f"❌ Error: No bot script found!")
            print("   Please ensure run_paper_trading.py exists")
            return
    
    print(f"✅ Using bot script: {bot_script}")
    
    # Create and run monitor
    monitor = PaperTradingMonitor(
        script_path=bot_script,
        check_interval=60  # Check every 60 seconds
    )
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nMonitor stopped by user")


if __name__ == "__main__":
    main()
