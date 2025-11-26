"""
FastAPI Backend Server for Real-Time Trading Data
Provides WebSocket streaming, REST API endpoints, and SSE support.
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import asyncio
import logging

# Local imports
from src.api.websocket_manager import manager as ws_manager
from src.api.data_broadcaster import get_broadcaster

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Intradyne Real-Time Trading API",
    description="WebSocket and REST API for real-time trading data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000", "*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize broadcaster
broadcaster = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global broadcaster
    logger.info("🚀 Starting Intradyne Real-Time API...")
    
    # Initialize broadcaster
    broadcaster = get_broadcaster(ws_manager)
    await broadcaster.start()
    
    logger.info("✅ API Server ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down API server...")
    if broadcaster:
        broadcaster.stop()


# ==================== WebSocket Endpoints ====================

@app.websocket("/ws/trading-stream")
async def websocket_endpoint(websocket: WebSocket, client_id: Optional[str] = None):
    """
    Main WebSocket endpoint for real-time trading data.
    
    Clients can subscribe to channels:
    - trades:SYMBOL - Trade updates for specific symbol
    - prices:SYMBOL - Price updates for specific symbol
    - signals:SYMBOL - AI signals for specific symbol
    - all - All updates
    """
    # Accept connection
    connected = await ws_manager.connect(websocket, client_id)
    if not connected:
        return
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Intradyne trading stream",
            "timestamp": time.time(),
            "available_channels": [
                "trades:BTC/USDT",
                "trades:ETH/USDT",
                "prices:BTC/USDT",
                "prices:ETH/USDT",
                "signals:BTC/USDT",
                "signals:ETH/USDT",
                "all"
            ]
        })
        
        # Message handling loop
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "subscribe":
                # Subscribe to channel
                channel = data.get("channel")
                if channel:
                    await ws_manager.subscribe(websocket, channel)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel,
                        "timestamp": time.time()
                    })
            
            elif message_type == "unsubscribe":
                # Unsubscribe from channel
                channel = data.get("channel")
                if channel:
                    await ws_manager.unsubscribe(websocket, channel)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channel": channel,
                        "timestamp": time.time()
                    })
            
            elif message_type == "pong":
                # Update ping time
                ws_manager.update_ping(websocket)
            
            elif message_type == "get_stats":
                # Send connection statistics
                stats = ws_manager.get_stats()
                await websocket.send_json({
                    "type": "stats",
                    "data": stats,
                    "timestamp": time.time()
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)


# ==================== REST API Endpoints ====================

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "service": "Intradyne Real-Time Trading API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "websocket": "/ws/trading-stream",
            "docs": "/docs",
            "health": "/api/health",
            "trading": "/api/trading/*",
            "ai": "/api/ai/*"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "connections": len(ws_manager.active_connections),
        "uptime": "N/A"  # TODO: Calculate uptime
    }


@app.get("/api/trading/latest")
@limiter.limit("100/minute")
async def get_latest_trades(request: Request, limit: int = 10):
    """
    Get latest trades.
    
    Args:
        limit: Number of trades to return (max 100)
    """
    try:
        import pandas as pd
        csv_path = 'reports/rag_paper_trades.csv'
        
        if not os.path.exists(csv_path):
            return {"trades": [], "count": 0}
        
        df = pd.read_csv(csv_path)
        latest = df.tail(min(limit, 100)).to_dict('records')
        
        return {
            "trades": latest,
            "count": len(latest),
            "timestamp": time.time()
        }
    
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trading/history")
@limiter.limit("50/minute")
async def get_trade_history(
    request: Request,
    symbol: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get trade history with optional filtering.
    
    Args:
        symbol: Filter by symbol (e.g., BTC/USDT)
        limit: Number of trades (max 200)
        offset: Offset for pagination
    """
    try:
        import pandas as pd
        csv_path = 'reports/rag_paper_trades.csv'
        
        if not os.path.exists(csv_path):
            return {"trades": [], "count": 0, "total": 0}
        
        df = pd.read_csv(csv_path)
        
        # Filter by symbol if provided
        if symbol:
            df = df[df['symbol'] == symbol]
        
        total = len(df)
        
        # Apply pagination
        df = df.iloc[offset:offset + min(limit, 200)]
        trades = df.to_dict('records')
        
        return {
            "trades": trades,
            "count": len(trades),
            "total": total,
            "offset": offset,
            "symbol": symbol,
            "timestamp": time.time()
        }
    
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trading/status")
@limiter.limit("100/minute")
async def get_trading_status(request: Request):
    """Get current trading system status."""
    try:
        import pandas as pd
        
        # Load trades
        csv_path = 'reports/rag_paper_trades.csv'
        trade_count = 0
        symbols = []
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            trade_count = len(df)
            symbols = df['symbol'].unique().tolist()
        
        # Load AI config
        ai_enabled = False
        config_path = 'config/ai_trading_config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                ai_enabled = config.get('enabled', False)
        
        return {
            "status": "online",
            "ai_enabled": ai_enabled,
            "total_trades": trade_count,
            "active_symbols": symbols,
            "websocket_connections": len(ws_manager.active_connections),
            "timestamp": time.time()
        }
    
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/signals/{symbol}")
@limiter.limit("60/minute")
async def get_ai_signal(request: Request, symbol: str):
    """
    Get current AI trading signal for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTC/USDT)
    """
    try:
        from src.trading.ai_decision_engine import SignalGenerator
        
        # Load AI config
        config_path = 'config/ai_trading_config.json'
        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail="AI config not found")
        
        with open(config_path, 'r') as f:
            ai_config = json.load(f)
        
        if not ai_config.get('enabled', False):
            return {
                "enabled": False,
                "message": "AI trading is disabled"
            }
        
        # Create signal generator
        engine_config = {
            'momentum_weight': ai_config.get('momentum_weight', 70) / 100,
            'sentiment_weight': ai_config.get('sentiment_weight', 30) / 100,
            'max_position_size': ai_config.get('max_position_size', 500),
            'stop_loss_pct': ai_config.get('stop_loss_pct', 5) / 100,
            'take_profit_pct': ai_config.get('take_profit_pct', 10) / 100
        }
        
        engine = SignalGenerator(engine_config)
        
        # Get current price (mock for now)
        import pandas as pd
        csv_path = 'reports/rag_paper_trades.csv'
        current_price = 0
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            symbol_trades = df[df['symbol'] == symbol]
            if not symbol_trades.empty:
                current_price = float(symbol_trades.iloc[-1]['price'])
        
        if current_price == 0:
            raise HTTPException(status_code=404, detail=f"No price data for {symbol}")
        
        # Generate signal
        signal = engine.get_recommendation(
            symbol=symbol,
            current_price=current_price,
            momentum=0.002  # Mock momentum
        )
        
        return {
            "symbol": symbol,
            "signal": signal,
            "timestamp": time.time()
        }
    
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_connection_stats():
    """Get WebSocket connection statistics."""
    return ws_manager.get_stats()


# ==================== Server-Sent Events ====================

async def event_generator():
    """Generate server-sent events."""
    while True:
        # Send periodic updates
        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
        await asyncio.sleep(5)


@app.get("/stream/trading")
async def sse_stream(request: Request):
    """
    Server-Sent Events endpoint for one-way data streaming.
    Alternative to WebSocket for simple clients.
    """
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
