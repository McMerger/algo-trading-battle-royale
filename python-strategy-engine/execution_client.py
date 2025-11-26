"""
Python gRPC client for Go Execution Engine

Provides a simple interface for strategies to submit orders and get market data
from the Go execution engine which handles real exchange connectivity.
"""

import grpc
import json
import requests
from typing import Dict, Optional
from datetime import datetime
import os


class ExecutionClient:
    """
    Client for communicating with Go Execution Engine.

    Falls back to REST if gRPC is not available.
    """

    def __init__(self, grpc_url: Optional[str] = None, http_url: Optional[str] = None):
        """
        Initialize execution client.

        Args:
            grpc_url: Go gRPC server address (default: localhost:50050)
            http_url: Go HTTP server address (default: http://localhost:8080)
        """
        self.grpc_url = grpc_url or os.getenv('GO_EXECUTION_GRPC_URL', 'localhost:50050')
        self.http_url = http_url or os.getenv('GO_EXECUTION_URL', 'http://localhost:8080')
        self.use_grpc = False  # Start with HTTP fallback

        # Try to establish gRPC connection
        try:
            self.grpc_channel = grpc.insecure_channel(self.grpc_url)
            # Test connection with timeout
            grpc.channel_ready_future(self.grpc_channel).result(timeout=2)
            self.use_grpc = True
            print(f"✓ Connected to Go execution engine via gRPC: {self.grpc_url}")
        except Exception as e:
            print(f"gRPC not available, using HTTP fallback: {e}")
            self.grpc_channel = None

    def submit_order(self,
                     order_id: str,
                     strategy_name: str,
                     symbol: str,
                     side: str,
                     quantity: float,
                     price: float = 0.0,
                     order_type: str = "MARKET",
                     exchange: str = "binance") -> Dict:
        """
        Submit a trading order to the execution engine.

        Args:
            order_id: Unique order identifier
            strategy_name: Name of strategy placing order
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Order size
            price: Limit price (0 for market orders)
            order_type: 'MARKET' or 'LIMIT'
            exchange: Target exchange (default: 'binance')

        Returns:
            Dict with order result
        """
        order_request = {
            'order_id': order_id,
            'strategy_name': strategy_name,
            'symbol': symbol,
            'side': side.upper(),
            'quantity': quantity,
            'price': price,
            'order_type': order_type.upper(),
            'exchange': exchange,
            'timestamp': datetime.now().isoformat()
        }

        if self.use_grpc:
            return self._submit_order_grpc(order_request)
        else:
            return self._submit_order_http(order_request)

    def get_market_data(self, symbol: str, exchange: str = "binance") -> Dict:
        """
        Get current market data for a symbol.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            exchange: Exchange name (default: 'binance')

        Returns:
            Dict with price, bid, ask, volume, etc.
        """
        if self.use_grpc:
            return self._get_market_data_grpc(symbol, exchange)
        else:
            return self._get_market_data_http(symbol, exchange)

    def get_balance(self, exchange: str = "binance") -> Dict:
        """
        Get account balance.

        Args:
            exchange: Exchange name (default: 'binance')

        Returns:
            Dict with balance information
        """
        if self.use_grpc:
            return self._get_balance_grpc(exchange)
        else:
            return self._get_balance_http(exchange)

    def _submit_order_http(self, order: Dict) -> Dict:
        """Submit order via HTTP REST API."""
        try:
            url = f"{self.http_url}/api/v1/orders"
            response = requests.post(url, json=order, timeout=10)

            if response.ok:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }

    def _get_market_data_http(self, symbol: str, exchange: str) -> Dict:
        """Get market data via HTTP."""
        try:
            url = f"{self.http_url}/api/v1/market/{exchange}/{symbol}"
            response = requests.get(url, timeout=10)

            if response.ok:
                return response.json()
            else:
                return {
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'error': f'Request failed: {str(e)}'
            }

    def _get_balance_http(self, exchange: str) -> Dict:
        """Get balance via HTTP."""
        try:
            url = f"{self.http_url}/api/v1/balance/{exchange}"
            response = requests.get(url, timeout=10)

            if response.ok:
                return response.json()
            else:
                return {
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'error': f'Request failed: {str(e)}'
            }

    def _submit_order_grpc(self, order: Dict) -> Dict:
        """Submit order via gRPC."""
        try:
            from grpc_generated import execution_pb2, execution_pb2_grpc
            
            # Create gRPC stub
            stub = execution_pb2_grpc.ExecutionServiceStub(self.grpc_channel)
            
            # Create request
            request = execution_pb2.OrderRequest(
                order_id=order['order_id'],
                strategy_name=order['strategy_name'],
                symbol=order['symbol'],
                side=order['side'],
                quantity=order['quantity'],
                price=order['price'],
                order_type=order['order_type'],
                exchange=order['exchange']
            )
            
            # Call gRPC service
            response = stub.SubmitOrder(request, timeout=10)
            
            return {
                'success': response.success,
                'order_id': response.order_id,
                'exchange_order_id': response.exchange_order_id,
                'status': response.status,
                'executed_price': response.executed_price,
                'executed_quantity': response.executed_quantity,
                'fees': response.fees,
                'error': response.error_message if not response.success else None
            }
        except Exception as e:
            print(f"gRPC call failed: {e}, falling back to HTTP")
            return self._submit_order_http(order)

    def _get_market_data_grpc(self, symbol: str, exchange: str) -> Dict:
        """Get market data via gRPC."""
        try:
            from grpc_generated import execution_pb2, execution_pb2_grpc
            
            # Create gRPC stub
            stub = execution_pb2_grpc.ExecutionServiceStub(self.grpc_channel)
            
            # Create request
            request = execution_pb2.MarketDataRequest(
                symbol=symbol,
                exchange=exchange
            )
            
            # Call gRPC service
            response = stub.GetMarketData(request, timeout=10)
            
            return {
                'symbol': response.symbol,
                'exchange': response.exchange,
                'price': response.price,
                'bid': response.bid,
                'ask': response.ask,
                'volume_24h': response.volume_24h,
                'high_24h': response.high_24h,
                'low_24h': response.low_24h,
                'price_change_24h': response.price_change_24h,
                'timestamp': response.timestamp.ToDatetime().isoformat() if response.timestamp else None
            }
        except Exception as e:
            print(f"gRPC call failed: {e}, falling back to HTTP")
            return self._get_market_data_http(symbol, exchange)

    def _get_balance_grpc(self, exchange: str) -> Dict:
        """Get balance via gRPC."""
        try:
            from grpc_generated import execution_pb2, execution_pb2_grpc
            
            # Create gRPC stub
            stub = execution_pb2_grpc.ExecutionServiceStub(self.grpc_channel)
            
            # Create request
            request = execution_pb2.BalanceRequest(
                exchange=exchange
            )
            
            # Call gRPC service
            response = stub.GetBalance(request, timeout=10)
            
            # Convert balances
            balances = {}
            for asset, balance in response.balances.items():
                balances[asset] = {
                    'free': balance.free,
                    'locked': balance.locked,
                    'total': balance.total,
                    'value_usd': balance.value_usd
                }
            
            return {
                'exchange': response.exchange,
                'balances': balances,
                'total_value_usd': response.total_value_usd,
                'timestamp': response.timestamp.ToDatetime().isoformat() if response.timestamp else None
            }
        except Exception as e:
            print(f"gRPC call failed: {e}, falling back to HTTP")
            return self._get_balance_http(exchange)

    def close(self):
        """Close gRPC channel."""
        if self.grpc_channel:
            self.grpc_channel.close()


# Global client instance
_execution_client = None

def get_execution_client() -> ExecutionClient:
    """Get or create global execution client instance."""
    global _execution_client
    if _execution_client is None:
        _execution_client = ExecutionClient()
    return _execution_client
