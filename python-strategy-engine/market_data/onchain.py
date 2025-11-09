"""
On-chain data adapter using DeFiLlama API.

Tracks capital flows (stablecoin inflows/outflows to exchanges),
TVL metrics, and chain-level liquidity.
"""

import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class DeFiLlamaAdapter:
    """
    DeFiLlama API adapter for on-chain metrics.

    Docs: https://defillama.com/docs/api
    Public API, rate-limited to 300 req/5min.
    """

    def __init__(self):
        self.base_url = "https://api.llama.fi"
        self.stablecoins_url = "https://stablecoins.llama.fi"
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    def get_protocol_tvl(self, protocol_slug: str) -> Optional[Dict]:
        """
        Get Total Value Locked for a specific protocol.

        Args:
            protocol_slug: Protocol identifier (e.g., 'aave', 'uniswap', 'compound')

        Returns:
            Dict with TVL data or None on failure
        """
        try:
            url = f"{self.base_url}/protocol/{protocol_slug}"
            resp = requests.get(url, timeout=10)

            if not resp.ok:
                print(f"DeFiLlama protocol error {resp.status_code} for {protocol_slug}")
                return None

            data = resp.json()

            # Get latest TVL
            tvl_usd = data.get('tvl', [{}])[-1].get('totalLiquidityUSD', 0) if data.get('tvl') else 0

            return {
                'source': 'defillama',
                'protocol': protocol_slug,
                'name': data.get('name', protocol_slug),
                'tvl_usd': float(tvl_usd),
                'chain': data.get('chain', 'multi-chain'),
                'category': data.get('category', 'unknown'),
                'updated_at': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Failed to fetch protocol TVL for {protocol_slug}: {e}")
            return None

    def get_chain_tvl(self, chain: str = 'Ethereum') -> Optional[Dict]:
        """
        Get TVL for an entire blockchain.

        Args:
            chain: Chain name (e.g., 'Ethereum', 'Solana', 'Arbitrum')
        """
        try:
            url = f"{self.base_url}/v2/historicalChainTvl/{chain}"
            resp = requests.get(url, timeout=10)

            if not resp.ok:
                print(f"DeFiLlama chain error {resp.status_code} for {chain}")
                return None

            data = resp.json()

            # Get latest TVL
            if data:
                latest = data[-1]
                return {
                    'source': 'defillama',
                    'chain': chain,
                    'tvl_usd': float(latest.get('tvl', 0)),
                    'timestamp': latest.get('date', 0),
                    'updated_at': datetime.now().isoformat()
                }

            return None

        except Exception as e:
            print(f"Failed to fetch chain TVL for {chain}: {e}")
            return None

    def get_stablecoin_flows(self, chain: str = 'ethereum') -> Optional[Dict]:
        """
        Get stablecoin supply on a specific chain.
        This is a proxy for capital positioning.

        High stablecoin inflows to exchanges = dry powder for buying.
        """
        try:
            # Note: DeFiLlama doesn't have direct exchange flow data
            # We use chain stablecoin supply as a proxy
            url = f"{self.stablecoins_url}/stablecoincharts/{chain}"
            resp = requests.get(url, timeout=10)

            if not resp.ok:
                print(f"Stablecoin data error {resp.status_code} for {chain}")
                return None

            data = resp.json()

            # Get latest data point
            if data:
                latest = data[-1]
                # Calculate 24h change if we have enough data
                prev_day = data[-2] if len(data) > 1 else latest

                current_supply = float(latest.get('totalCirculating', {}).get('peggedUSD', 0))
                prev_supply = float(prev_day.get('totalCirculating', {}).get('peggedUSD', 0))
                change_24h = current_supply - prev_supply

                return {
                    'source': 'defillama',
                    'chain': chain,
                    'total_stablecoins_usd': current_supply,
                    'change_24h_usd': change_24h,
                    'change_24h_pct': (change_24h / prev_supply * 100) if prev_supply > 0 else 0,
                    'updated_at': datetime.now().isoformat()
                }

            return None

        except Exception as e:
            print(f"Failed to fetch stablecoin flows for {chain}: {e}")
            return None

    def get_exchange_inflows(self, exchange: str = 'binance', timeframe: str = '24h') -> Dict:
        """
        Estimate exchange inflows (synthetic for now).

        Note: Real exchange flow data requires specialized APIs (Glassnode, etc).
        This is a placeholder that returns mock data for testing.

        In production, integrate with:
        - Glassnode API (paid)
        - CryptoQuant (paid)
        - Or derive from on-chain transaction data
        """
        # Mock data for testing - replace with real API
        # Format matches what agents expect
        mock_inflows = {
            'binance': {'usdc': 450_000_000, 'usdt': 320_000_000},
            'coinbase': {'usdc': 280_000_000, 'usdt': 150_000_000},
            'kraken': {'usdc': 120_000_000, 'usdt': 80_000_000}
        }

        inflows = mock_inflows.get(exchange.lower(), {'usdc': 0, 'usdt': 0})
        total = inflows['usdc'] + inflows['usdt']

        return {
            'source': 'defillama_mock',
            'exchange': exchange,
            'timeframe': timeframe,
            'usdc': inflows['usdc'],
            'usdt': inflows['usdt'],
            'total_usd': total,
            'updated_at': datetime.now().isoformat(),
            'note': 'Mock data - integrate Glassnode/CryptoQuant for production'
        }


class OnChainDataFeed:
    """
    Main interface for on-chain data.
    Aggregates multiple metrics into agent-friendly format.
    """

    def __init__(self, use_mock=False):
        self.defillama = DeFiLlamaAdapter()
        self.use_mock = use_mock
        self.cache = {}

        # Mock data for offline testing
        self.mock_data = {
            'usdc_inflows': 450_000_000,
            'usdt_inflows': 320_000_000,
            'total_inflows': 770_000_000,
            'defi_tvl': 85_000_000_000,
            'eth_tvl': 55_000_000_000,
            'change_24h': 1_200_000_000,
            'updated_at': datetime.now().isoformat()
        }

    def get_onchain_metrics(self, config: Optional[Dict] = None) -> Dict:
        """
        Fetch comprehensive on-chain metrics.

        Args:
            config: Optional configuration dict:
                {
                    'exchanges': ['binance', 'coinbase'],
                    'protocols': ['aave', 'uniswap'],
                    'chains': ['Ethereum', 'Solana']
                }

        Returns:
            Dict of on-chain metrics for agent consumption
        """
        if self.use_mock:
            return self.mock_data

        config = config or {}
        exchanges = config.get('exchanges', ['binance'])
        protocols = config.get('protocols', ['aave'])
        chains = config.get('chains', ['Ethereum'])

        metrics = {
            'exchange_flows': {},
            'protocol_tvls': {},
            'chain_tvls': {},
            'updated_at': datetime.now().isoformat()
        }

        # Get exchange inflows
        total_inflows = 0
        for exchange in exchanges:
            flows = self.defillama.get_exchange_inflows(exchange)
            if flows:
                metrics['exchange_flows'][exchange] = flows
                total_inflows += flows.get('total_usd', 0)

        metrics['total_exchange_inflows'] = total_inflows

        # Get protocol TVLs
        total_defi_tvl = 0
        for protocol in protocols:
            tvl = self.defillama.get_protocol_tvl(protocol)
            if tvl:
                metrics['protocol_tvls'][protocol] = tvl
                total_defi_tvl += tvl.get('tvl_usd', 0)

        metrics['total_defi_tvl'] = total_defi_tvl

        # Get chain TVLs
        for chain in chains:
            tvl = self.defillama.get_chain_tvl(chain)
            if tvl:
                metrics['chain_tvls'][chain] = tvl

        # Get stablecoin supply changes (proxy for capital flows)
        stables = self.defillama.get_stablecoin_flows('ethereum')
        if stables:
            metrics['stablecoin_supply'] = stables

        return metrics

    def add_onchain_to_market_data(self, market_data: Dict, config: Optional[Dict] = None) -> Dict:
        """
        Enrich market data with on-chain metrics.
        This is the key integration point for agents.
        """
        enriched = market_data.copy()
        enriched['onchain'] = self.get_onchain_metrics(config)
        return enriched
