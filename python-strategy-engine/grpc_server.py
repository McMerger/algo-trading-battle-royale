"""
gRPC server for SignalOps Strategy Engine.
Listens for strategy evaluation requests and returns trading signals.

This server runs continuously, waiting for the Go execution engine
to request strategy evaluations via gRPC.
"""
import grpc
from concurrent import futures
import time
import logging
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grpc_generated import execution_pb2, execution_pb2_grpc
from agents.graham_defensive import GrahamDefensiveStrategy
from market_data.multi_source_feed import MultiSourceDataFeed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategyEngineService(execution_pb2_grpc.ExecutionServiceServicer):
    """gRPC service for strategy evaluation."""

    def __init__(self):
        """Initialize the strategy engine with multi-source data feed."""
        try:
            # Initialize multi-source data feed (uses real APIs)
            self.feed = MultiSourceDataFeed(use_mock=False)
            
            # Initialize Graham Defensive strategy
            self.strategy = GrahamDefensiveStrategy("GrahamDefensive")
            
            logger.info("Strategy Engine initialized successfully")
            logger.info(f"Strategy: {self.strategy.name}")
            logger.info("Multi-source feed: Polymarket, Yahoo Finance, DeFiLlama")
        except Exception as e:
            logger.error(f"Failed to initialize Strategy Engine: {e}")
            raise

    def SubmitOrder(self, request, context):
        """
        Handle order submission requests from Go execution engine.
        
        This method evaluates the strategy and returns a trading signal.
        """
        try:
            logger.info(f"Received order request for {request.symbol}")
            
            # For now, we'll return a simple response
            # In full implementation, this would trigger strategy evaluation
            return execution_pb2.OrderResponse(
                order_id=request.order_id,
                status="PENDING",
                message=f"Order received for {request.symbol}",
                exchange_order_id="",
                executed_price=0.0,
                executed_quantity=0.0,
                fees=0.0,
                timestamp=int(time.time())
            )
        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return execution_pb2.OrderResponse()

    def GetMarketData(self, request, context):
        """
        Get current market data and strategy evaluation for a symbol.
        
        This is the main entry point for strategy evaluation.
        """
        try:
            logger.info(f"Evaluating strategy for {request.symbol}")
            
            # Get multi-source unified data
            unified = self.feed.get_unified_data(
                symbol=request.symbol,
                market_data={'price': 100},  # Placeholder - will be replaced with real data
                event_config={
                    'recession': 'will-the-us-enter-a-recession-in-2025',
                    'btc_100k': 'will-bitcoin-be-above-100000-on-january-1-2025'
                }
            )
            
            # Generate trading signal
            signal = self.strategy.generate_signal({'unified': unified})
            
            if signal:
                logger.info(f"Signal generated: {signal.action} with confidence {signal.confidence:.2f}")
                logger.info(f"Reason: {signal.reason}")
                
                # Return market data response with signal
                return execution_pb2.MarketDataResponse(
                    symbol=request.symbol,
                    price=signal.price,
                    bid=signal.price * 0.999,  # Mock bid/ask spread
                    ask=signal.price * 1.001,
                    volume=1000000.0,
                    timestamp=int(signal.timestamp),
                    # Additional metadata can be added here
                    high_24h=signal.price * 1.05,
                    low_24h=signal.price * 0.95,
                    change_24h=0.02
                )
            else:
                logger.info("No signal generated")
                return execution_pb2.MarketDataResponse(
                    symbol=request.symbol,
                    price=100.0,
                    bid=99.9,
                    ask=100.1,
                    volume=1000000.0,
                    timestamp=int(time.time()),
                    high_24h=105.0,
                    low_24h=95.0,
                    change_24h=0.0
                )
                
        except Exception as e:
            logger.error(f"Market data request failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return execution_pb2.MarketDataResponse()

    def GetOrderStatus(self, request, context):
        """Get order status (stub implementation)."""
        logger.info(f"Order status requested for {request.order_id}")
        
        return execution_pb2.OrderStatusResponse(
            order_id=request.order_id,
            status="FILLED",
            filled_quantity=0.0,
            average_price=0.0,
            timestamp=int(time.time())
        )

    def GetBalance(self, request, context):
        """Get account balance (stub implementation)."""
        logger.info(f"Balance requested for exchange: {request.exchange}")
        
        # Return mock balance
        return execution_pb2.BalanceResponse(
            total_balance=10000.0,
            available_balance=10000.0,
            timestamp=int(time.time())
        )


def serve():
    """Start the gRPC server."""
    # Create gRPC server with thread pool
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add our service to the server
    execution_pb2_grpc.add_ExecutionServiceServicer_to_server(
        StrategyEngineService(), server
    )
    
    # Listen on port 50051
    server.add_insecure_port('[::]:50051')
    
    # Start the server
    server.start()
    logger.info("=" * 60)
    logger.info("SignalOps Strategy Engine gRPC Server")
    logger.info("=" * 60)
    logger.info("Server listening on port 50051")
    logger.info("Ready to receive strategy evaluation requests")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    try:
        # Keep server alive
        while True:
            time.sleep(86400)  # Sleep for 1 day
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)
        logger.info("Server stopped")


if __name__ == '__main__':
    serve()
