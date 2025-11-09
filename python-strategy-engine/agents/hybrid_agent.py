"""
Hybrid multi-source agent requiring 2/3 confirmation.

The core innovation: Only trade when multiple independent sources agree.
This reduces false positives and increases conviction.
"""

from typing import Dict, Optional, List
from agents.base_agent import BaseAgent, Signal


class HybridAgent(BaseAgent):
    """
    Multi-source fusion agent.

    Strategy:
    - Checks 3 independent sources: Polymarket, on-chain, news
    - Requires at least 2/3 to agree on direction
    - Confidence compounds when all 3 align
    - When sources conflict, that's a signal itself (avoid trading)

    Example:
        Polymarket: 68% BTC $100k (bullish)
        On-chain: $450M inflows (bullish)
        News: Fed dovish (bullish)
        → 3/3 sources = HIGH confidence BUY

        vs.

        Polymarket: 72% Fed hike (bearish)
        On-chain: $400M inflows (bullish)
        News: No events (neutral)
        → Sources conflict = NO TRADE
    """

    def __init__(self, name="HybridAgent",
                 confirmation_threshold=2,  # Require 2/3 sources
                 polymarket_threshold=0.65,
                 onchain_threshold=300_000_000,
                 news_impact_threshold=2.0):
        super().__init__(name)

        self.confirmation_threshold = confirmation_threshold
        self.polymarket_threshold = polymarket_threshold
        self.onchain_threshold = onchain_threshold
        self.news_impact_threshold = news_impact_threshold

        # Track previous values for change detection
        self.prev_poly_prob = {}
        self.prev_onchain_flows = None
        self.seen_news = set()

    def _check_polymarket_signal(self, event_data: Dict) -> Optional[str]:
        """
        Check Polymarket probabilities for directional signal.

        Returns: 'BUY', 'SELL', or None
        """
        if 'polymarket' not in event_data:
            return None

        poly = event_data['polymarket']

        # Check BTC price markets (bullish if high probability)
        for key in ['btc_100k', 'btc_above_100k', 'bitcoin_100k']:
            if key in poly:
                prob = poly[key].get('yes_probability', 0.5)
                if prob > self.polymarket_threshold:
                    return 'BUY'
                elif prob < (1 - self.polymarket_threshold):
                    return 'SELL'

        # Check Fed hike markets (bearish if high hike probability)
        for key in ['fed_hike', 'fed_rate_hike', 'rate_hike']:
            if key in poly:
                prob = poly[key].get('yes_probability', 0.5)
                if prob > self.polymarket_threshold:
                    return 'SELL'  # Hikes = risk-off
                elif prob < (1 - self.polymarket_threshold):
                    return 'BUY'   # No hikes = risk-on

        # Check recession markets (bearish if high probability)
        for key in ['recession', 'us_recession', 'recession_2025']:
            if key in poly:
                prob = poly[key].get('yes_probability', 0.5)
                if prob > self.polymarket_threshold:
                    return 'SELL'
                elif prob < (1 - self.polymarket_threshold):
                    return 'BUY'

        return None

    def _check_onchain_signal(self, event_data: Dict) -> Optional[str]:
        """
        Check on-chain metrics for directional signal.

        Returns: 'BUY', 'SELL', or None
        """
        if 'onchain' not in event_data:
            return None

        onchain = event_data['onchain']

        # Large inflows = bullish
        total_inflows = onchain.get('total_exchange_inflows', 0)
        if total_inflows > self.onchain_threshold:
            return 'BUY'

        # Stablecoin supply increase = bullish
        stablecoin_data = onchain.get('stablecoin_supply', {})
        stablecoin_change = stablecoin_data.get('change_24h_usd', 0)
        if stablecoin_change > 400_000_000:  # $400M+
            return 'BUY'
        elif stablecoin_change < -300_000_000:  # $300M- outflow
            return 'SELL'

        # TVL decline = bearish
        defi_tvl = onchain.get('total_defi_tvl', 0)
        if self.prev_onchain_flows and defi_tvl > 0:
            tvl_change_pct = ((defi_tvl - self.prev_onchain_flows) / self.prev_onchain_flows) * 100
            if tvl_change_pct < -5:  # 5% decline
                return 'SELL'
            elif tvl_change_pct > 5:  # 5% increase
                return 'BUY'

        self.prev_onchain_flows = defi_tvl
        return None

    def _check_news_signal(self, event_data: Dict) -> Optional[str]:
        """
        Check news events for directional signal.

        Returns: 'BUY', 'SELL', or None
        """
        if 'news_events' not in event_data:
            return None

        news = event_data['news_events']
        events = news.get('events', [])

        if not events:
            return None

        # Find highest impact unseen event
        best_event = None
        best_impact = 0

        for event in events:
            event_id = f"{event['source']}_{event['title'][:50]}"
            if event_id in self.seen_news:
                continue

            impact = event.get('impact_score', 0)
            if impact > best_impact and impact >= self.news_impact_threshold:
                best_impact = impact
                best_event = event
                self.seen_news.add(event_id)

        if not best_event:
            return None

        sentiment = best_event.get('sentiment', 'neutral')

        if sentiment == 'bullish':
            return 'BUY'
        elif sentiment == 'bearish':
            return 'SELL'

        # Source-specific fallbacks
        source = best_event.get('source')
        title = best_event.get('title', '').lower()

        if source == 'fed':
            if 'hike' in title or 'hawkish' in title:
                return 'SELL'
            elif 'cut' in title or 'dovish' in title:
                return 'BUY'

        if source == 'sec' and 'etf' in title:
            if 'approve' in title:
                return 'BUY'
            elif 'reject' in title:
                return 'SELL'

        return None

    def generate_signal(self, market_data, event_data=None):
        """
        Generate signal only if 2+ sources confirm.

        This is the key innovation: multi-source confirmation
        reduces false positives.
        """
        if not event_data:
            return None

        # Check all three sources
        poly_signal = self._check_polymarket_signal(event_data)
        onchain_signal = self._check_onchain_signal(event_data)
        news_signal = self._check_news_signal(event_data)

        # Count confirmations
        signals = [s for s in [poly_signal, onchain_signal, news_signal] if s is not None]

        if len(signals) < self.confirmation_threshold:
            # Not enough sources have opinion
            return None

        # Count votes for each direction
        buy_votes = sum(1 for s in signals if s == 'BUY')
        sell_votes = sum(1 for s in signals if s == 'SELL')

        # Require majority agreement
        if buy_votes >= self.confirmation_threshold:
            action = 'BUY'
            confidence = 0.70 + (buy_votes * 0.07)  # 77%, 84%, 91% for 2/3/3 votes
        elif sell_votes >= self.confirmation_threshold:
            action = 'SELL'
            confidence = 0.70 + (sell_votes * 0.07)
        else:
            # Sources conflict - this is valuable information!
            return None

        # Build detailed reason showing all sources
        source_details = []
        if poly_signal:
            source_details.append(f"Polymarket: {poly_signal}")
        if onchain_signal:
            source_details.append(f"On-chain: {onchain_signal}")
        if news_signal:
            source_details.append(f"News: {news_signal}")

        confirmation_count = len(signals)
        agreement = buy_votes if action == 'BUY' else sell_votes

        reason = (f"{agreement}/{confirmation_count} sources confirm {action} | "
                 f"{' + '.join(source_details)} | "
                 f"Multi-source conviction: {confidence:.0%}")

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


class StrictHybridAgent(BaseAgent):
    """
    Even stricter version: Requires ALL 3 sources to agree.
    Trades less frequently but with maximum conviction.
    """

    def __init__(self, name="StrictHybridAgent"):
        super().__init__(name)
        # Reuse HybridAgent logic but require 3/3 confirmation
        self.hybrid = HybridAgent(name=name, confirmation_threshold=3)

    def generate_signal(self, market_data, event_data=None):
        """
        Only trade when all three sources align.
        Highest conviction, lowest frequency.
        """
        return self.hybrid.generate_signal(market_data, event_data)
