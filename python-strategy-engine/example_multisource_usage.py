"""
Example demonstrating the exact multi-source pattern from README.

This shows how to build a custom agent using all three data sources
exactly as specified in the documentation.
"""

from agents.base_agent import BaseAgent, Signal
from market_data.prediction_market_adapter import PredictionMarketFeed
from market_data.onchain import DeFiLlamaAdapter, OnChainDataFeed
from market_data.events import NewsAdapter, EventDataFeed
import time


class MyMultiSourceAgent(BaseAgent):
    """
    Example from README: Using all three data sources.
    """

    def generate_signal(self, market_data, event_data):
        """
        Access all three data sources as shown in README.

        event_data format matches README specification:
        {
            'polymarket': {
                'btc_100k': {'yes_probability': 0.68, ...},
                'fed_hike': {'yes_probability': 0.72, ...}
            },
            'onchain': {
                'usdc_inflows': 450000000,
                'defi_tvl': 85000000000
            },
            'news_events': {
                'events': [...],
                'count': 1
            }
        }
        """
        if not event_data:
            return None

        # Access Polymarket (as per README example)
        polymarket = event_data.get('polymarket', {})
        fed_hike_market = polymarket.get('fed_hike', {})
        fed_hike_odds = fed_hike_market.get('yes_probability', 0.5)

        # Access on-chain flows (as per README example)
        onchain = event_data.get('onchain', {})

        # Handle different on-chain data structures
        if 'exchange_flows' in onchain:
            # If detailed exchange flow data exists
            binance_flows = onchain['exchange_flows'].get('binance', {})
            binance_inflows = binance_flows.get('total_usd', 0)
        elif 'total_exchange_inflows' in onchain:
            # If aggregated total exists
            binance_inflows = onchain['total_exchange_inflows']
        else:
            # Fallback
            binance_inflows = onchain.get('usdc_inflows', 0)

        # Multi-source logic (exact pattern from README)
        if fed_hike_odds > 0.70 and binance_inflows > 300e6:
            return Signal(
                timestamp=market_data['timestamp'],
                symbol=market_data['symbol'],
                action='SELL',  # Hike fears + capital flight
                confidence=fed_hike_odds,
                size=100,
                reason=f"Fed hike {fed_hike_odds:.0%} + ${binance_inflows/1e6:.0f}M outflows",
                agent_name=self.name,
                price=market_data['price']
            )

        return None


def example_1_individual_adapters():
    """
    Example 1: Using individual adapters (README pattern).
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Individual Adapter Usage (README Pattern)")
    print("="*70)

    # Polymarket adapter (README example)
    print("\n1. Polymarket - Crowd Forecasts:")
    from market_data.prediction_market_adapter import PolymarketAdapter

    adapter = PolymarketAdapter()
    odds = adapter.get_market_odds('will-bitcoin-be-above-100000-on-january-1-2025')

    if odds:
        print(f"   Market: {odds['title']}")
        print(f"   YES probability: {odds['yes_probability']:.1%}")
        print(f"   Volume: ${odds['volume']:,.0f}")
    else:
        print("   (Using mock data)")

    # DeFiLlama adapter (README example)
    print("\n2. DeFiLlama - On-Chain Reality:")
    from market_data.onchain import DeFiLlamaAdapter

    adapter = DeFiLlamaAdapter()
    inflows = adapter.get_exchange_inflows('binance', timeframe='24h')

    print(f"   Exchange: {inflows['exchange']}")
    print(f"   USDC: ${inflows['usdc']:,}")
    print(f"   USDT: ${inflows['usdt']:,}")
    print(f"   Total: ${inflows['total_usd']:,}")

    # News adapter (README example)
    print("\n3. RSS/News - Event Catalysts:")
    from market_data.events import NewsAdapter

    adapter = NewsAdapter()
    events = adapter.get_recent(['fed', 'sec', 'treasury'], minutes=60)

    print(f"   Found {len(events)} events in last 60 minutes")
    if events:
        for event in events[:2]:
            print(f"   - [{event['source']}] {event['title'][:60]}...")


def example_2_building_custom_agent():
    """
    Example 2: Building a custom agent (README pattern).
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Building Custom Agent (README Pattern)")
    print("="*70)

    # Create agent
    agent = MyMultiSourceAgent("MyAgent")

    # Market data
    market_data = {
        'symbol': 'BTC',
        'price': 95000,
        'volume': 1000000,
        'timestamp': time.time()
    }

    # Event data (matches README spec exactly)
    event_data = {
        'polymarket': {
            'btc_100k': {
                'yes_probability': 0.68,
                'volume': 500000
            },
            'fed_hike': {
                'yes_probability': 0.72,
                'volume': 250000
            }
        },
        'onchain': {
            'usdc_inflows': 450_000_000,
            'defi_tvl': 85_000_000_000
        },
        'news_events': {
            'events': [
                {
                    'source': 'fed',
                    'title': 'Rate decision in 2 hours',
                    'impact_score': 3.0
                }
            ]
        }
    }

    print("\nInputs:")
    print(f"  Market: BTC @ ${market_data['price']:,}")
    print(f"  Polymarket: {event_data['polymarket']['btc_100k']['yes_probability']:.0%} BTC $100k odds")
    print(f"  On-chain: ${event_data['onchain']['usdc_inflows']/1e6:.0f}M inflows")
    print(f"  News: {len(event_data['news_events']['events'])} events")

    # Generate signal
    signal = agent.generate_signal(market_data, event_data)

    print("\nOutput:")
    if signal:
        print(f"  Action: {signal.action}")
        print(f"  Confidence: {signal.confidence:.0%}")
        print(f"  Reason: {signal.reason}")
    else:
        print("  No signal generated")


def example_3_full_integration():
    """
    Example 3: Full integration with all three feeds.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Full Integration (All Three Sources)")
    print("="*70)

    # Initialize all feeds
    poly_feed = PredictionMarketFeed(use_mock=True)  # Use mock for demo
    onchain_feed = OnChainDataFeed(use_mock=True)
    news_feed = EventDataFeed(use_mock=True)

    # Configuration
    poly_config = {
        'btc_100k': 'will-bitcoin-hit-100k-in-2024',
        'fed_hike': 'fed-raises-rates'
    }

    onchain_config = {
        'exchanges': ['binance'],
        'protocols': ['aave'],
        'chains': ['Ethereum']
    }

    news_sources = ['fed', 'sec']

    # Fetch data
    print("\nFetching data from all sources...")
    poly_data = poly_feed.get_events(poly_config)
    onchain_data = onchain_feed.get_onchain_metrics(onchain_config)
    news_data = news_feed.get_events(news_sources, minutes=60)

    # Combine
    event_data = {
        'polymarket': poly_data,
        'onchain': onchain_data,
        'news_events': news_data
    }

    print("\nData fetched successfully:")
    print(f"  Polymarket: {len(poly_data)} markets")
    print(f"  On-chain: ${onchain_data.get('total_exchange_inflows', 0)/1e6:.0f}M inflows")
    print(f"  News: {news_data['count']} events")

    # Use with agent
    market_data = {
        'symbol': 'BTC',
        'price': 95000,
        'timestamp': time.time()
    }

    agent = MyMultiSourceAgent("MyAgent")
    signal = agent.generate_signal(market_data, event_data)

    print("\nAgent signal:")
    if signal:
        print(f"  {signal.action} @ {signal.confidence:.0%}")
        print(f"  {signal.reason}")
    else:
        print("  No signal (sources don't confirm)")


def example_4_hybrid_confirmation():
    """
    Example 4: Using HybridAgent for multi-source confirmation.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Hybrid Agent (2/3 Confirmation)")
    print("="*70)

    from agents.hybrid_agent import HybridAgent

    # Create hybrid agent
    hybrid = HybridAgent("Hybrid-2of3", confirmation_threshold=2)

    # Scenario: All 3 sources agree (bullish)
    market_data = {
        'symbol': 'BTC',
        'price': 95000,
        'timestamp': time.time()
    }

    event_data_aligned = {
        'polymarket': {
            'btc_100k': {'yes_probability': 0.68}  # Bullish
        },
        'onchain': {
            'total_exchange_inflows': 450_000_000  # Bullish (big inflows)
        },
        'news_events': {
            'events': [
                {
                    'source': 'fed',
                    'title': 'Fed signals dovish stance',
                    'impact_score': 3.5,
                    'sentiment': 'bullish'
                }
            ],
            'count': 1
        }
    }

    print("\nScenario 1: All 3 sources ALIGN (bullish)")
    print("  Polymarket: 68% BTC $100k (bullish)")
    print("  On-chain: $450M inflows (bullish)")
    print("  News: Fed dovish (bullish)")

    signal = hybrid.generate_signal(market_data, event_data_aligned)

    if signal:
        print(f"\n  Result: {signal.action} @ {signal.confidence:.0%}")
        print(f"  Reason: {signal.reason}")
    else:
        print("\n  Result: No trade")

    # Scenario: Sources conflict
    event_data_conflict = {
        'polymarket': {
            'fed_hike': {'yes_probability': 0.78}  # Bearish (high hike odds)
        },
        'onchain': {
            'total_exchange_inflows': 600_000_000  # Bullish (big inflows)
        },
        'news_events': {
            'events': [],
            'count': 0
        }
    }

    print("\n\nScenario 2: Sources CONFLICT")
    print("  Polymarket: 78% Fed hike (bearish)")
    print("  On-chain: $600M inflows (bullish)")
    print("  News: No events (neutral)")

    signal = hybrid.generate_signal(market_data, event_data_conflict)

    if signal:
        print(f"\n  Result: {signal.action} @ {signal.confidence:.0%}")
    else:
        print("\n  Result: NO TRADE - Sources conflict!")
        print("  Key insight: System avoids false signals when sources disagree")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MULTI-SOURCE TRADING SYSTEM - USAGE EXAMPLES")
    print("Demonstrating patterns from README.md")
    print("="*70)

    # Run all examples
    example_1_individual_adapters()
    example_2_building_custom_agent()
    example_3_full_integration()
    example_4_hybrid_confirmation()

    print("\n" + "="*70)
    print("All examples completed!")
    print("\nNext steps:")
    print("  - Run: python test_multisource.py for comprehensive tests")
    print("  - Run: python strategy-engine.py --mode multisource")
    print("  - Build your own agent following MyMultiSourceAgent pattern")
    print("="*70 + "\n")
