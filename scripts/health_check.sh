#!/bin/bash
# Health check script for Docker

# Check if Python is running
if ! pgrep -f python > /dev/null; then
    echo "❌ Python process not running"
    exit 1
fi

# Check if we can import main modules
python3 -c "
import sys
try:
    from src.trading.paper_trader import PaperTrader
    from src.strategy.backtester import Backtester
    print('✅ Modules OK')
    sys.exit(0)
except Exception as e:
    print(f'❌ Module import failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

# Check data directory
if [ ! -d "/app/data" ]; then
    echo "❌ Data directory missing"
    exit 1
fi

echo "✅ Health check passed"
exit 0
