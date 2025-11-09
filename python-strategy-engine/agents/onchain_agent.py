"""
On-chain agent that trades based on capital flows.

Strategy:
- Monitor stablecoin inflows to exchanges (dry powder for buying)
- Track DeFi TVL changes (capital rotation)
- React to large capital movements (>$100M threshold)
"""

from typing import Dict, Optional
from agents.base_agent import BaseAgent, Signal


class OnChainAgent(BaseAgent):
    """
    Trades on on-chain capital flow signals.

    Logic:
    - Large stablecoin inflows to exchanges = bullish (buying power)
    - Outflows from exchanges = bearish (moving to cold storage)
    - Rising DeFi TVL = risk-on sentiment
    - Falling TVL = risk-off, capital fleeing
    """

    def __init__(self, name="OnChainAgent",
                 inflow_threshold=400_000_000,  # $400M threshold
                 tvl_change_threshold=5.0):      # 5% TVL change
        super().__init__(name)

        self.inflow_threshold = inflow_threshold
        self.tvl_change_threshold = tvl_change_threshold

        # Track previous values for change detection
        self.prev_tvl = None
        self.prev_inflows = None

    def generate_signal(self, market_data, event_data=None):
        """
        Generate signal based on on-chain metrics.

        Expected event_data format:
        {
            'onchain': {
                'total_exchange_inflows': 770000000,
                'total_defi_tvl': 85000000000,
                'change_24h': 1200000000,
                'exchange_flows': {...},
                'protocol_tvls': {...}
            }
        }
        """
        if not event_data or 'onchain' not in event_data:
            return None

        onchain = event_data['onchain']

        action = 'HOLD'
        confidence = 0.5
        reason = "No significant on-chain signals"

        # Extract key metrics
        total_inflows = onchain.get('total_exchange_inflows', 0)
        defi_tvl = onchain.get('total_defi_tvl', 0)
        stablecoin_data = onchain.get('stablecoin_supply', {})
        stablecoin_change = stablecoin_data.get('change_24h_usd', 0)

        # Signal 1: Large exchange inflows (bullish - dry powder)
        if total_inflows > self.inflow_threshold:
            action = 'BUY'
            confidence = min(0.85, 0.6 + (total_inflows / 1e9) * 0.05)
            reason = (f"${total_inflows / 1e6:.0f}M stablecoin inflows to exchanges. "
                     f"High buying power accumulation. Threshold: ${self.inflow_threshold / 1e6:.0f}M")

        # Signal 2: Stablecoin supply increase (capital entering crypto)
        elif stablecoin_change > 500_000_000:  # $500M+ increase
            action = 'BUY'
            confidence = 0.7
            reason = (f"${stablecoin_change / 1e6:.0f}M stablecoin supply increase. "
                     f"Capital flowing into crypto ecosystem")

        # Signal 3: TVL changes (risk sentiment indicator)
        if self.prev_tvl and defi_tvl > 0:
            tvl_change_pct = ((defi_tvl - self.prev_tvl) / self.prev_tvl) * 100

            if tvl_change_pct > self.tvl_change_threshold:
                # Rising TVL = risk-on
                if action == 'BUY':
                    confidence = min(0.9, confidence + 0.1)
                    reason += f" | DeFi TVL +{tvl_change_pct:.1f}% (risk-on confirmation)"
                else:
                    action = 'BUY'
                    confidence = 0.72
                    reason = f"DeFi TVL surging +{tvl_change_pct:.1f}% (${defi_tvl / 1e9:.1f}B). Risk-on sentiment"

            elif tvl_change_pct < -self.tvl_change_threshold:
                # Falling TVL = risk-off
                action = 'SELL'
                confidence = 0.75
                reason = f"DeFi TVL declining {tvl_change_pct:.1f}% (${defi_tvl / 1e9:.1f}B). Capital flight detected"

        # Signal 4: Stablecoin outflows (bearish - capital leaving)
        if stablecoin_change < -300_000_000:  # $300M+ decrease
            action = 'SELL'
            confidence = 0.73
            reason = (f"${abs(stablecoin_change) / 1e6:.0f}M stablecoin supply decrease. "
                     f"Capital exiting crypto")

        # Update tracking
        self.prev_tvl = defi_tvl
        self.prev_inflows = total_inflows

        if action == 'HOLD':
            return None

        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'BTC'),
            action=action,
            confidence=confidence,
            size=100,
            reason=reason,
            agent_name=self.name,
            price=market_data.get('price', 0)
        )


class FlowWatcherAgent(BaseAgent):
    """
    Specialized agent focused purely on exchange flows.
    Simpler, more reactive than general on-chain agent.
    """

    def __init__(self, name="FlowWatcherAgent",
                 flow_threshold=200_000_000):
        super().__init__(name)
        self.flow_threshold = flow_threshold

    def generate_signal(self, market_data, event_data=None):
        """
        Trade based purely on exchange stablecoin flows.

        Inflows > threshold = BUY (capital positioning)
        Outflows > threshold = SELL (capital leaving)
        """
        if not event_data or 'onchain' not in event_data:
            return None

        onchain = event_data['onchain']
        flows = onchain.get('exchange_flows', {})

        total_usdc = 0
        total_usdt = 0

        # Sum across all tracked exchanges
        for exchange, flow_data in flows.items():
            total_usdc += flow_data.get('usdc', 0)
            total_usdt += flow_data.get('usdt', 0)

        total_inflows = total_usdc + total_usdt

        if total_inflows > self.flow_threshold:
            return Signal(
                timestamp=market_data.get('timestamp', 0),
                symbol=market_data.get('symbol', 'BTC'),
                action='BUY',
                confidence=min(0.85, 0.65 + (total_inflows / 1e9) * 0.05),
                size=100,
                reason=(f"${total_inflows / 1e6:.0f}M stablecoin exchange inflows "
                       f"(USDC: ${total_usdc / 1e6:.0f}M, USDT: ${total_usdt / 1e6:.0f}M). "
                       f"Capital ready to deploy"),
                agent_name=self.name,
                price=market_data.get('price', 0)
            )

        # Note: Outflow detection would require negative values
        # Current implementation uses absolute inflows only

        return None
