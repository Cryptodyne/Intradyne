import logging
import json
import os
from datetime import datetime
from typing import Optional
from .rag_engine import RAGEngine

from ..engines.core_engines import TrendEngine, VolatilityEngine, RiskEngine

class Coordinator:
    """
    Layer 3-6 Orchestrator.
    Manages the workflow pipeline: Objective -> Inputs -> Ensemble -> Decision -> Execution.
    """
    def __init__(self, use_live_data: bool = False, exchange: str = 'binance'):
        """
        Initialize the Coordinator.
        
        Args:
            use_live_data: Whether to use live market data (default: False for mock data)
            exchange: Exchange to use for live data (default: 'binance')
        """
        self.rag = RAGEngine()
        self.rag.load_knowledge_base()
        
        # Initialize Engines
        self.trend_engine = TrendEngine()
        self.volatility_engine = VolatilityEngine()
        self.risk_engine = RiskEngine()
        
        # Initialize Market Data Fetcher (optional)
        self.market_fetcher = None
        if use_live_data:
            try:
                from ..data.market_data import MarketDataFetcher
                self.market_fetcher = MarketDataFetcher(exchange_id=exchange)
                self.logger = self._setup_logger()
                self.logger.info(f"Live market data enabled (Exchange: {exchange})")
            except Exception as e:
                self.logger = self._setup_logger()
                self.logger.error(f"Failed to initialize market data fetcher: {e}")
                self.logger.warning("Falling back to mock data mode")
                self.market_fetcher = None
        else:
            self.logger = self._setup_logger()
            self.logger.info("Using mock data mode")
        
        self.state = "IDLE"

    def _setup_logger(self):
        logger = logging.getLogger("INTRADYNE_CORE")
        logger.setLevel(logging.INFO)
        # Ensure log directory exists
        os.makedirs("data/logs", exist_ok=True)
        handler = logging.FileHandler("data/logs/system.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def run_pipeline_with_symbol(self, symbol: str, timeframe: str = '5m', limit: int = 50):
        """
        Fetch live market data and run the pipeline.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (default: '5m')
            limit: Number of candles (default: 50)
            
        Returns:
            Pipeline result dictionary
        """
        if self.market_fetcher is None:
            raise RuntimeError("Live market data not enabled. Initialize with use_live_data=True")
        
        try:
            # Fetch market data
            market_data = self.market_fetcher.format_for_engines(symbol, timeframe, limit)
            
            # Validate data quality
            ohlcv = self.market_fetcher.fetch_ohlcv(symbol, timeframe, limit)
            is_valid, checks = self.market_fetcher.validate_data_quality(ohlcv)
            
            if not is_valid:
                self.logger.warning(f"Data quality issues for {symbol}: {checks}")
                # Continue anyway but log the warning
            
            # Run pipeline with fetched data
            return self.run_pipeline(market_data)
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            raise

    def run_pipeline(self, market_data: dict):
        """
        Executes the 8-step workflow pipeline.
        
        Args:
            market_data: Dictionary with 'symbol', 'closes', 'volume'
            
        Returns:
            Log entry dictionary with decision and details
        """
        self.state = "PROCESSING"
        
        # Step 1: Parse Objective & Context (RAG)
        # Query RAG for relevant trading rules
        symbol = market_data.get('symbol', 'UNKNOWN')
        context = self.rag.query_context(f"trading rules for {symbol}")
        
        # Step 2: Collect Inputs (Passed in via market_data)
        
        # Step 3: Hybrid Ensemble Inference
        ensemble_decision = self._query_engines(market_data)
        
        # Step 4: Decision Assembly
        score = ensemble_decision['score']
        compliance = ensemble_decision['compliance']
        
        decision = "HOLD"
        if score >= 0.65 and compliance >= 0.90:
            decision = "EXECUTE"
            # Step 5: Mode Selection (Simplified)
            # Step 6: Trade Construction (Simplified)
            # Step 7: Execution (Log only for now)
            self.logger.info(f"TRADE EXECUTED: {ensemble_decision} | Symbol: {symbol}")
        else:
            self.logger.info(f"TRADE REJECTED: Score {score}, Compliance {compliance} | Symbol: {symbol}")

        # Step 8: Logging
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "market_data": market_data,
            "ensemble": ensemble_decision,
            "decision": decision,
            "context_used": len(context)
        }
        
        # Write to a JSON log for the dashboard to read easily
        with open("data/logs/latest_trade.json", "w") as f:
            json.dump(log_entry, f, indent=2)

        self.state = "IDLE"
        return log_entry

    def _query_engines(self, data):
        """
        Query all trading engines and aggregate results.
        
        Args:
            data: Market data dictionary
            
        Returns:
            Aggregated decision with score and details
        """
        # Call all engines
        trend = self.trend_engine.analyze(data)
        volatility = self.volatility_engine.analyze(data)
        risk = self.risk_engine.analyze(data)
        
        # Simple weighted aggregation
        # Trend (40%), Volatility (30%), Risk (30%) - Example weights
        
        # Convert "direction" to score (Long=1, Neutral=0.5, Short=0) - Simplified
        def get_score(d):
            return 1.0 if d['direction'] == 'LONG' else (0.0 if d['direction'] == 'SHORT' else 0.5)
            
        trend_score = get_score(trend)
        vol_score = get_score(volatility)
        
        # Risk is a multiplier (0 if unsafe, 1 if safe)
        risk_mult = 1.0 if risk['reason_code'] == 'SAFE' else 0.0
        
        final_score = (trend_score * 0.4 + vol_score * 0.3 + 0.3) * risk_mult # Base 0.3 for others
        
        return {
            "score": round(final_score, 2),
            "compliance": 1.0, # Placeholder - could integrate RAG compliance check here
            "details": {
                "trend": trend,
                "volatility": volatility,
                "risk": risk
            }
        }

