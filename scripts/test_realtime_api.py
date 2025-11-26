"""
Simple test script for Intradyne Real-Time API
Tests all endpoints and WebSocket functionality.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api():
    """Test all API endpoints."""
    print("🧪 Testing Intradyne Real-Time API...\n")
    
    # Test 1: Root endpoint
    print("[ ] Test 1: Root endpoint")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root: {data['service']} v{data['version']}")
        else:
            print(f"❌ Root failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Root error: {e}")
    
    # Test 2: Health check
    print("\n[/] Test 2: Health check")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health: {data['status']}, Connections: {data['connections']}")
        else:
            print(f"❌ Health failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health error: {e}")
    
    # Test 3: Latest trades
    print("\n[/] Test 3: Latest trades")
    try:
        response = requests.get(f"{BASE_URL}/api/trading/latest", params={"limit": 5})
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Latest trades: {data['count']} trades found")
            if data['trades']:
                latest = data['trades'][-1]
                print(f"   Last trade: {latest.get('side')} {latest.get('quantity')} {latest.get('symbol')} @ ${latest.get('price')}")
        else:
            print(f"❌ Trades failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Trades error: {e}")
    
    # Test 4: Trading status
    print("\n[/] Test 4: Trading status")
    try:
        response = requests.get(f"{BASE_URL}/api/trading/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"   AI Enabled: {data['ai_enabled']}")
            print(f"   Total Trades: {data['total_trades']}")
            print(f"   Active Symbols: {data['active_symbols']}")
        else:
            print(f"❌ Status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Status error: {e}")
    
    # Test 5: AI Signal
    print("\n[/] Test 5: AI Signal")
    try:
        response = requests.get(f"{BASE_URL}/api/ai/signals/BTC/USDT")
        if response.status_code == 200:
            data = response.json()
            if 'signal' in data:
                signal = data['signal']
                print(f"✅ AI Signal for BTC/USDT:")
                print(f"   Action: {signal['action']}")
                print(f"   Confidence: {signal['confidence']:.0%}")
                print(f"   Reasoning: {signal['reasoning'][:60]}...")
            else:
                print(f"⚠️  AI is disabled")
        else:
            print(f"❌ Signal failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Signal error: {e}")
    
    # Test 6: Connection stats
    print("\n[/] Test 6: WebSocket stats")
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ WebSocket Stats:")
            print(f"   Total Connections: {data['total_connections']}")
            print(f"   Total Channels: {data['total_channels']}")
            print(f"   Messages Sent: {data['total_messages_sent']}")
        else:
            print(f"❌ Stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats error: {e}")
    
    print("\n✅ All tests completed!")
    print(f"\n📊 Dashboard: http://localhost:8501")
    print(f"🔌 API Docs: {BASE_URL}/docs")
    print(f"⚡ WebSocket: ws://localhost:8000/ws/trading-stream")


if __name__ == "__main__":
    test_api()
