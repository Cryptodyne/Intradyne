# Intradyne Real-Time Trading System 🚀

## Quick Start

### Option 1: Quick Start (File Mode - No Setup Required)

```bash
# Just run the dashboard
streamlit run src/interface/streamlit_app.py
```

The dashboard will work in file mode, reading from CSV/log files with auto-refresh every 5 seconds.

### Option 2: Full Real-Time Mode (Recommended)

This enables WebSocket streaming, REST API, and live updates.

```bash
# Run the smart startup script
start_realtime_system.bat
```

This will automatically:
- ✅ Start the FastAPI backend on port 8000
- ✅ Start the Streamlit dashboard on port 8501
- ✅ Open your browser to http://localhost:8501

**Services:**
- 📊 **Dashboard**: http://localhost:8501
- 🔌 **API Docs**: http://localhost:8000/docs
- ⚡ **WebSocket**: ws://localhost:8000/ws/trading-stream

## Real-Time Features

### Auto-Refresh
The dashboard automatically refreshes at configurable intervals:
- 🚀 **Real-time (2s)** - High CPU usage, sub-second updates
- ⚡ **Fast (5s)** - Recommended for most users
- 🕐 **Normal (10s)** - Balanced performance
- 🐌 **Slow (30s)** - Low resource usage
- 🛑 **Manual** - No auto-refresh

### Smart Data Loading
The system uses a 3-tier fallback strategy:
1. **Primary**: WebSocket stream (instant updates)
2. **Fallback 1**: REST API polling (5-10s refresh)
3. **Fallback 2**: Local CSV/log files

If the backend is offline, the dashboard seamlessly falls back to file mode.

### Connection Status
The sidebar shows real-time backend status:
- 🟢 **Backend Connected** - API responding, WebSocket available  
- 🔴 **Backend Offline** - Using file mode

## API Endpoints

All endpoints are available at `http://localhost:8000`:

### REST API
- `GET /api/trading/latest` - Latest trades (limit: 100)
- `GET /api/trading/history` - Trade history with pagination
- `GET /api/trading/status` - System status and portfolio summary
- `GET /api/ai/signals/{symbol}` - AI trading signal for symbol
- `GET /api/health` - Health check
- `GET /api/stats` - WebSocket connection statistics

### WebSocket
Connect to `ws://localhost:8000/ws/trading-stream`

**Subscribe to channels:**
```json
{"type": "subscribe", "channel": "trades:BTC/USDT"}
{"type": "subscribe", "channel": "prices:ETH/USDT"}
{"type": "subscribe", "channel": "signals:BTC/USDT"}
```

**Available channels:**
- `trades:{SYMBOL}` - Trade updates for specific symbol
- `prices:{SYMBOL}` - Price updates for specific symbol
- `signals:{SYMBOL}` - AI signals for specific symbol
- `all` - All updates

**Unsubscribe:**
```json
{"type": "unsubscribe", "channel": "trades:BTC/USDT"}
```

**Get stats:**
```json
{"type": "get_stats"}
```

### Server-Sent Events (SSE)
For simple one-way streaming:
```bash
curl -N http://localhost:8000/stream/trading
```

## Configuration

### Real-Time Settings
Edit `config/realtime_config.json`:
```json
{
  "refresh_interval": 5,
  "performance_mode": "auto",
  "websocket": {
    "enabled": true,
    "url": "ws://localhost:8000/ws/trading-stream"
  }
}
```

### AI Trading Settings
Configure via the Settings page in the dashboard or edit `config/ai_trading_config.json`.

## Architecture

```
┌─────────────────────────────────────────────┐
│         Streamlit Dashboard (8501)          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Portfolio │  │ Trading  │  │ Settings │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────┬───────────────────────────┘
                  │
   ┌──────────────┴──────────────┐
   │                             │
   ▼ WebSocket/API              ▼ File Reading
┌─────────────────────────┐  ┌──────────────┐
│  FastAPI Backend (8000) │  │ CSV/Log Files│
│  ┌─────────────────┐    │  └──────────────┘
│  │ WebSocket Mgr   │    │
│  └─────────────────┘    │
│  ┌─────────────────┐    │
│  │ Data Broadcaster│◄───── File Watcher
│  └─────────────────┘    │
│  ┌─────────────────┐    │
│  │  REST API       │    │
│  └─────────────────┘    │
└─────────────────────────┘
```

## Performance

**Expected Metrics:**
- WebSocket latency: <50ms
- REST API response: <100ms
- Support: 1000+ concurrent WebSocket connections
- CPU usage: <10% idle, <30% under load

## Troubleshooting

### Backend not starting
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <process_id> /F

# Restart
python -m uvicorn src.api.api_server:app --host 0.0.0.0 --port 8000
```

### Dashboard not connecting to backend
1. Check if backend is running: http://localhost:8000/api/health
2. Check firewall settings
3. The dashboard will automatically fall back to file mode

### Auto-refresh not working
1. Check refresh interval is not set to "Manual"
2. Verify Streamlit is not frozen
3. Check browser console (F12) for errors

## Development

### Running Backend Only
```bash
python -m uvicorn src.api.api_server:app --host 0.0.0.0 --port 8000 --reload
```

### Running Dashboard Only
```bash
streamlit run src/interface/streamlit_app.py
```

### Testing WebSocket
```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/ws/trading-stream

# Subscribe to channel
> {"type":"subscribe","channel":"trades:BTC/USDT"}
```

### API Documentation
Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Future Enhancements

Planned features (not yet implemented):
- [ ] Redis caching for sub-second response times
- [ ] TimescaleDB for time-series optimization
- [ ] GraphQL endpoint for flexible queries
- [ ] Prometheus metrics + Grafana dashboards
- [ ] JWT authentication
- [ ] Binary protocol (MessagePack) for reduced bandwidth

## License

Private - Intradyne Trading System
