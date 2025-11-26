    def reset_daily_stats(self):
        """Reset daily statistics at start of new trading day."""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trade_count = 0
            self.daily_loss_count = 0
            self.trading_enabled = True
            self.last_reset_date = today
            logging.info("Daily stats reset for new trading day")
    
    def check_daily_loss_limit(self) -> Dict:
        """
        Check if daily loss limit has been reached.
        
        Returns:
            {'allowed': bool, 'reason': str}
        """
        self.reset_daily_stats()
        
        if not self.trading_enabled:
            return {
                'allowed': False,
                'reason': 'Trading disabled due to daily loss limit'
            }
        
        # Check loss limit
        daily_loss_limit = self.config.get('daily_loss_limit', 500.0)
        if self.daily_pnl < -daily_loss_limit:
            self.trading_enabled = False
            logging.warning(f"🛑 Daily loss limit reached: ${self.daily_pnl:.2f}")
            return {
                'allowed': False,
                'reason': f'Daily loss limit exceeded (${self.daily_pnl:.2f})'
            }
        
        # Check max daily losses
        max_daily_losses = self.config.get('max_daily_losses', 3)
        if self.daily_loss_count >= max_daily_losses:
            self.trading_enabled = False
            logging.warning(f"🛑 Max daily losses reached: {self.daily_loss_count}")
            return {
                'allowed': False,
                'reason': f'Maximum daily losses reached ({self.daily_loss_count})'
            }
        
        return {'allowed': True, 'reason': ''}
    
    def record_trade_result(self, pnl: float):
        """
        Record trade result for daily loss tracking.
        
        Args:
            pnl: Profit/loss of the trade in USD
        """
        self.daily_pnl += pnl
        self.daily_trade_count += 1
        
        if pnl < 0:
            self.daily_loss_count += 1
        
        logging.info(f"Daily Stats - P&L: ${self.daily_pnl:.2f}, Losses: {self.daily_loss_count}, Trades: {self.daily_trade_count}")
    
    def calculate_enhanced_momentum(self, price_data: pd.DataFrame) -> float:
        """
        Calculate multi-period momentum for stronger signal.
        
        Args:
            price_data: DataFrame with price history
            
        Returns:
            Enhanced momentum score
        """
        if len(price_data) < 24:
            # Fallback to simple momentum
            return (price_data['close'].iloc[-1] - price_data['close'].iloc[-2]) / price_data['close'].iloc[-2]
        
        current_price = price_data['close'].iloc[-1]
        
        # Multi-period momentum
        mom_1h = (current_price - price_data['close'].iloc[-2]) / price_data['close'].iloc[-2]
        mom_4h = (current_price - price_data['close'].iloc[-5]) / price_data['close'].iloc[-5] if len(price_data) >= 5 else mom_1h
        mom_24h = (current_price - price_data['close'].iloc[-25]) / price_data['close'].iloc[-25] if len(price_data) >= 25 else mom_4h
        
        # Weighted average (recent periods weighted more)
        enhanced_momentum = (mom_1h * 0.5) + (mom_4h * 0.3) + (mom_24h * 0.2)
        
        return enhanced_momentum
    
    def get_higher_timeframe_trend(self, price_data: pd.DataFrame) -> str:
        """
        Determine higher timeframe trend direction.
        
        Args:
            price_data: DataFrame with price history
            
        Returns:
            'UP', 'DOWN', or 'SIDEWAYS'
        """
        if len(price_data) < 10:
            return 'SIDEWAYS'
        
        # Use simple moving averages on higher timeframe
        # Approximate 4H by using every 4th candle if 1H data
        closes = price_data['close']
        
        # Short and long term averages
        sma_short = closes.iloc[-5:].mean()  # Last 5 periods
        sma_long = closes.iloc[-20:].mean() if len(closes) >= 20 else closes.mean()
        
        diff_pct = (sma_short - sma_long) / sma_long
        
        if diff_pct > 0.01:  # 1% above
            return 'UP'
        elif diff_pct < -0.01:  # 1% below
            return 'DOWN'
        else:
            return 'SIDEWAYS'


# Add to end of file before if __name__ == "__main__"
