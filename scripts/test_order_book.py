import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis import OrderBookAnalyzer

def test_order_book_analysis():
    print("="*70)
    print("TESTING ORDER BOOK ANALYZER")
    print("="*70)
    
    analyzer = OrderBookAnalyzer(depth_levels=10)
    
    # 1. Mock Balanced Order Book
    print("\n1. Testing Balanced Order Book")
    balanced_ob = {
        'bids': [[100-i, 1.0] for i in range(10)],  # 100, 99, 98... vol 1.0
        'asks': [[101+i, 1.0] for i in range(10)]   # 101, 102, 103... vol 1.0
    }
    
    imbalance = analyzer.calculate_imbalance(balanced_ob)
    print(f"Imbalance (Expected 0.0): {imbalance:.2f}")
    
    # 2. Mock Buy Pressure (High Bid Volume)
    print("\n2. Testing Buy Pressure")
    buy_pressure_ob = {
        'bids': [[100-i, 5.0] for i in range(10)],  # Vol 5.0
        'asks': [[101+i, 1.0] for i in range(10)]   # Vol 1.0
    }
    
    imbalance = analyzer.calculate_imbalance(buy_pressure_ob)
    print(f"Imbalance (Expected > 0): {imbalance:.2f}")
    
    # 3. Testing Wall Detection
    print("\n3. Testing Wall Detection")
    wall_ob = {
        'bids': [[100, 1.0], [99, 1.0], [98, 10.0], [97, 1.0]], # Wall at 98
        'asks': [[101, 1.0], [102, 1.0], [103, 1.0], [104, 15.0]] # Wall at 104
    }
    
    walls = analyzer.detect_walls(wall_ob, threshold_multiplier=2.0)
    print(f"Threshold: {walls['threshold']:.2f}")
    print(f"Buy Walls: {walls['buy_walls']}")
    print(f"Sell Walls: {walls['sell_walls']}")
    
    # 4. Testing Micro Price
    print("\n4. Testing Micro Price")
    micro_price = analyzer.get_micro_price(buy_pressure_ob)
    mid_price = (100 + 101) / 2
    print(f"Mid Price: {mid_price}")
    print(f"Micro Price: {micro_price:.4f}")
    print(f"Micro Price vs Mid: {'Higher' if micro_price > mid_price else 'Lower'}")
    
    print("\n" + "="*70)
    print("✅ Order Book Analysis Tests Complete")
    print("="*70)

if __name__ == "__main__":
    test_order_book_analysis()
