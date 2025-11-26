"""
On-chain data adapter for DeFiLlama and exchange flow metrics.

DeFiLlama provides free, open APIs for:
- Total Value Locked (TVL) across protocols
- Chain statistics
- DEX volumes
- Protocol revenue

This data helps identify capital flows before they hit exchanges.
"""

import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import time


class DeFiLlamaAdapter:
    """
    DeFiLlama API adapter for on-chain metrics.

    Docs: https://defillama.com/docs/api
    Free tier, no API key required for most endpoints.
    """

    def __init__(self):
        self.base_url = "https://api.llama.fi"
        self.coins_url = "https://coins.llama.fi"
        self.session = requests.Session()
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    def get_protocol_tvl(self, protocol_slug: str) -> Optional[Dict]:
        """
        Get Total Value Locked for a specific protocol.

        Args:
            protocol_slug: Protocol identifier (e.g., 'uniswap', 'aave', 'curve')

        Returns:
            Dict with TVL history and current value
        """
        cache_key = f"protocol_tvl_{protocol_slug}"
        if self._check_cache(cache_key):
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/protocol/{protocol_slug}"
            resp = self.session.get(url, timeout=10)

            if not resp.ok:
                print(f"DeFiLlama error {resp.status_code} for {protocol_slug}")
                return None

            data = resp.json()

            result = {
                'source': 'defillama',
                'protocol': data.get('name', protocol_slug),
                'slug': protocol_slug,
                'current_tvl': float(data.get('tvl', [{}])[-1].get('totalLiquidityUSD', 0)) if data.get('tvl') else 0,
                'chain_tvls': data.get('chainTvls', {}),
                'change_1d': self._calculate_change(data.get('tvl', []), days=1),
                'change_7d': self._calculate_change(data.get('tvl', []), days=7),
                'updated_at': datetime.now().isoformat()
            }

            self.cache[cache_key] = result
            return result

        except Exception as e:
            print(f"Failed to fetch DeFiLlama protocol {protocol_slug}: {e}")
            return None

    def get_chain_tvl(self, chain: str = 'Ethereum') -> Optional[Dict]:
        """Get TVL for an entire blockchain."""
        cache_key = f"chain_tvl_{chain}"
        if self._check_cache(cache_key):
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/v2/historicalChainTvl/{chain}"
            resp = self.session.get(url, timeout=10)

            if not resp.ok:
                return None

            data = resp.json()
            if not data:
                return None

            current = data[-1] if data else {}

            result = {
                'source': 'defillama',
                'chain': chain,
                'current_tvl': float(current.get('tvl', 0)),
                'change_1d': self._calculate_tvl_change(data, days=1),
                'updated_at': datetime.now().isoformat()
            }

            self.cache[cache_key] = result
            return result

        except Exception as e:
            print(f"Failed to fetch chain TVL for {chain}: {e}")
            return None

    def _calculate_change(self, tvl_history: List[Dict], days: int) -> float:
        """Calculate TVL percentage change."""
        if not tvl_history or len(tvl_history) < 2:
            return 0.0

        try:
            current = float(tvl_history[-1].get('totalLiquidityUSD', 0))
            target_timestamp = time.time() - (days * 86400)

            for entry in reversed(tvl_history[:-1]):
                if entry.get('date', 0) <= target_timestamp:
                    past = float(entry.get('totalLiquidityUSD', 0))
                    if past > 0:
                        return ((current - past) / past) * 100
                    break
        except Exception:
            pass

        return 0.0

    def _calculate_tvl_change(self, history: List[Dict], days: int) -> float:
        """Calculate TVL change for chain data."""
        if not history or len(history) < days:
            return 0.0

        try:
            current = float(history[-1].get('tvl', 0))
            past = float(history[-(days + 1)].get('tvl', 0))
            if past > 0:
                return ((current - past) / past) * 100
        except Exception:
            pass

        return 0.0

    def _check_cache(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self.cache:
            return False

        entry = self.cache[key]
        if 'updated_at' not in entry:
            return False

        age = (datetime.now() - datetime.fromisoformat(entry['updated_at'])).seconds
        return age < self.cache_ttl


class OnChainDataFeed:
    """
    Unified interface for on-chain metrics.
    """

    def __init__(self, use_mock=False):
        self.defillama = DeFiLlamaAdapter()
        self.use_mock = use_mock

    def get_crypto_market_health(self, symbol: str = 'BTC') -> Dict:
        """
        Aggregate on-chain health indicators.

        Returns:
        - DeFi TVL trends (capital flowing in/out)
        - Chain health metrics
        """
        if self.use_mock:
            return {
                'source': 'mock_onchain',
                'tvl_change_1d': -2.3,
                'sentiment': 'NEUTRAL'
            }

        chain_tvl = self.defillama.get_chain_tvl('Ethereum')

        return {
            'source': 'onchain',
            'symbol': symbol,
            'chain_tvl': chain_tvl,
            'interpretation': self._interpret(chain_tvl),
            'updated_at': datetime.now().isoformat()
        }

    def _interpret(self, tvl_data: Optional[Dict]) -> Dict:
        """Translate on-chain metrics into trading signals."""
        if not tvl_data:
            return {'sentiment': 'NEUTRAL', 'confidence': 0.5}

        tvl_change = tvl_data.get('change_1d', 0)

        if tvl_change > 5:
            return {
                'sentiment': 'BULLISH',
                'confidence': 0.7,
                'reason': f'TVL up {tvl_change:.1f}%'
            }
        elif tvl_change < -5:
            return {
                'sentiment': 'BEARISH',
                'confidence': 0.7,
                'reason': f'TVL down {tvl_change:.1f}%'
            }

        return {'sentiment': 'NEUTRAL', 'confidence': 0.5}
