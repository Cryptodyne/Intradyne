import sys
import os
import time
import random
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.coordinator import Coordinator

def generate_mock_data():
    # Generate random price walk
    closes = [100.0]
    for _ in range(50):
        change = random.uniform(-0.02, 0.02)
        closes.append(closes[-1] * (1 + change))
    
    return {
        "symbol": "BTC/USDT",
        "closes": closes,
        "volume": 1000000
    }

def main():
    print("Initializing Coordinator...")
    coordinator = Coordinator()
    print("Coordinator initialized.")
    
    print("Starting pipeline loop (Press Ctrl+C to stop)...")
    try:
        while True:
            data = generate_mock_data()
            result = coordinator.run_pipeline(data)
            print(f"[{result['timestamp']}] Decision: {result['decision']} | Score: {result['ensemble']['score']}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping pipeline.")

if __name__ == "__main__":
    main()
