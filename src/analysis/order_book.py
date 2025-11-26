import numpy as np
import pandas as pd

class OrderBookAnalyzer:
    """
    Analyzes order book depth to detect imbalances, walls, and liquidity pressure.
    """
    
    def __init__(self, depth_levels=20):
        self.depth_levels = depth_levels

    def calculate_imbalance(self, order_book):
        """
        Calculates the volume imbalance between bids and asks.
        Returns a value between -1 (total sell pressure) and 1 (total buy pressure).
        """
        bids = order_book.get('bids', [])[:self.depth_levels]
        asks = order_book.get('asks', [])[:self.depth_levels]
        
        if not bids or not asks:
            return 0.0
            
        bid_vol = sum(b[1] for b in bids)
        ask_vol = sum(a[1] for a in asks)
        
        if bid_vol + ask_vol == 0:
            return 0.0
            
        return (bid_vol - ask_vol) / (bid_vol + ask_vol)

    def detect_walls(self, order_book, threshold_multiplier=3.0):
        """
        Identifies significant buy/sell walls.
        Returns a dict with 'buy_walls' and 'sell_walls' lists of (price, volume).
        """
        bids = order_book.get('bids', [])[:self.depth_levels]
        asks = order_book.get('asks', [])[:self.depth_levels]
        
        if not bids or not asks:
            return {'buy_walls': [], 'sell_walls': []}
            
        # Calculate average volume per level
        all_vols = [b[1] for b in bids] + [a[1] for a in asks]
        avg_vol = np.mean(all_vols) if all_vols else 0
        threshold = avg_vol * threshold_multiplier
        
        buy_walls = [(b[0], b[1]) for b in bids if b[1] > threshold]
        sell_walls = [(a[0], a[1]) for a in asks if a[1] > threshold]
        
        return {
            'buy_walls': buy_walls,
            'sell_walls': sell_walls,
            'threshold': threshold
        }

    def get_micro_price(self, order_book):
        """
        Calculates the volume-weighted average price (micro-price).
        This is often a better predictor of short-term price than the mid-price.
        """
        bids = order_book.get('bids', [])[:self.depth_levels]
        asks = order_book.get('asks', [])[:self.depth_levels]
        
        if not bids or not asks:
            return None
            
        # Weighted average of top bid and ask
        # Simple micro-price formula: (Bid_Vol * Ask_Px + Ask_Vol * Bid_Px) / (Bid_Vol + Ask_Vol)
        # Using just the top level for standard micro-price, or weighted across depth
        
        # Let's use weighted average across depth for a more robust metric
        total_vol_bids = sum(b[1] for b in bids)
        total_prod_bids = sum(b[0] * b[1] for b in bids)
        
        total_vol_asks = sum(a[1] for a in asks)
        total_prod_asks = sum(a[0] * a[1] for a in asks)
        
        if total_vol_bids + total_vol_asks == 0:
            return None
            
        # This is essentially VWAP of the order book
        return (total_prod_bids + total_prod_asks) / (total_vol_bids + total_vol_asks)

    def get_spread_analysis(self, order_book):
        """
        Analyzes the bid-ask spread.
        """
        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])
        
        if not bids or not asks:
            return None
            
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        
        spread = best_ask - best_bid
        spread_pct = (spread / best_bid) * 100
        
        return {
            'spread': spread,
            'spread_pct': spread_pct,
            'best_bid': best_bid,
            'best_ask': best_ask
        }
