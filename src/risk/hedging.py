import numpy as np
import math
from scipy.stats import norm

class TailRiskHedger:
    """
    Manages tail risk hedging using simulated protective put options.
    """
    
    def __init__(self, portfolio_value, risk_threshold=0.05, hedge_ratio=0.5):
        self.portfolio_value = portfolio_value
        self.risk_threshold = risk_threshold # Drop % to trigger hedge
        self.hedge_ratio = hedge_ratio # % of portfolio to cover
        self.active_hedge = None

    def detect_tail_risk(self, market_data):
        """
        Detects conditions for tail risk (high volatility or rapid drawdown).
        """
        if len(market_data) < 20:
            return False
            
        closes = market_data['close'].values
        
        # 1. Check for rapid drawdown (last 24h)
        current_price = closes[-1]
        price_24h_ago = closes[-24] if len(closes) >= 24 else closes[0]
        drawdown = (current_price - price_24h_ago) / price_24h_ago
        
        if drawdown < -self.risk_threshold:
            return True
            
        # 2. Check for extreme volatility (ATR spike)
        # Simplified: if current range is 3x average range
        highs = market_data['high'].values
        lows = market_data['low'].values
        ranges = highs - lows
        avg_range = np.mean(ranges[-20:])
        current_range = ranges[-1]
        
        if current_range > avg_range * 3.0:
            return True
            
        return False

    def calculate_option_premium(self, S, K, T, r, sigma):
        """
        Black-Scholes pricing for a Put Option.
        S: Spot price
        K: Strike price
        T: Time to maturity (years)
        r: Risk-free rate
        sigma: Volatility (annualized)
        """
        if T <= 0 or sigma <= 0:
            return max(K - S, 0)
            
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        put_price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return put_price

    def execute_hedge(self, current_price, volatility):
        """
        Simulates buying protective puts.
        """
        if self.active_hedge:
            return None # Already hedged
            
        # Strike price: 5% OTM (Out of The Money)
        strike_price = current_price * 0.95
        
        # Time to expiry: 1 month (1/12 years)
        time_to_expiry = 1/12
        
        # Risk-free rate: 4%
        risk_free_rate = 0.04
        
        # Calculate premium per option
        premium = self.calculate_option_premium(
            current_price, strike_price, time_to_expiry, risk_free_rate, volatility
        )
        
        # Calculate number of contracts needed
        # We want to cover hedge_ratio * portfolio_value
        value_to_hedge = self.portfolio_value * self.hedge_ratio
        contracts = value_to_hedge / current_price
        
        total_cost = premium * contracts
        
        self.active_hedge = {
            'entry_price': current_price,
            'strike_price': strike_price,
            'contracts': contracts,
            'premium_paid': total_cost,
            'expiry': time_to_expiry,
            'volatility': volatility
        }
        
        return self.active_hedge

    def update_hedge_value(self, current_price, time_passed=0):
        """
        Calculates current value of the hedge.
        """
        if not self.active_hedge:
            return 0.0
            
        # Update time to expiry
        T = self.active_hedge['expiry'] - time_passed
        if T <= 0:
            # Expired
            payoff = max(self.active_hedge['strike_price'] - current_price, 0)
            return payoff * self.active_hedge['contracts']
            
        # Recalculate option value
        current_option_value = self.calculate_option_premium(
            current_price,
            self.active_hedge['strike_price'],
            T,
            0.04,
            self.active_hedge['volatility'] # Assuming constant vol for simplicity
        )
        
        total_value = current_option_value * self.active_hedge['contracts']
        return total_value

    def close_hedge(self, current_price):
        """
        Closes the hedge and returns P&L.
        """
        if not self.active_hedge:
            return 0.0
            
        final_value = self.update_hedge_value(current_price)
        pnl = final_value - self.active_hedge['premium_paid']
        
        self.active_hedge = None
        return pnl
