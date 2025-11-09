"""
Test multi-source signal fusion.

Demonstrates the three data sources working together:
1. Polymarket (prediction markets)
2. DeFiLlama (on-chain flows)
3. RSS feeds (breaking news)
"""

import time
from datetime import datetime

# Data adapters
from market_data.prediction_market_adapter import PredictionMarketFeed
from market_data.onchain import OnChainDataFeed
from market_data.events import EventDataFeed

# Agents
from agents.event_driven_agent import EventDrivenAgent
from agents.onchain_agent import OnChainAgent
from agents.news_agent import NewsAgent
from agents.hybrid_agent import HybridAgent, StrictHybridAgent


def test_data_sources():
    """Test that all three data sources work."""
    print("=" * 70)
    print("TESTING MULTI-SOURCE DATA FEEDS")
    print("=" * 70)

    # Test Polymarket
    print("\n1. Testing Polymarket (Prediction Markets)...")
    poly_feed = PredictionMarketFeed(use_mock=False)  # Try live first

    event_config = {
        'btc_100k': 'will-bitcoin-hit-100k-in-2024',
        'fed_rate': 'fed-raises-rates-july-2024'
    }

    poly_data = poly_feed.get_events(event_config)
    print(f"   Found {len(poly_data)} Polymarket markets")
    for event_name, data in poly_data.items():
        prob = data.get('yes_probability', 0)
        source = data.get('source', 'unknown')
        print(f"   - {event_name}: {prob:.1%} probability ({source})")

    # Test DeFiLlama
    print("\n2. Testing DeFiLlama (On-Chain Data)...")
    onchain_feed = OnChainDataFeed(use_mock=False)  # Try live

    onchain_config = {
        'exchanges': ['binance'],
        'protocols': ['aave', 'uniswap'],
        'chains': ['Ethereum']
    }

    onchain_data = onchain_feed.get_onchain_metrics(onchain_config)
    print(f"   Total exchange inflows: ${onchain_data.get('total_exchange_inflows', 0) / 1e6:.1f}M")
    print(f"   Total DeFi TVL: ${onchain_data.get('total_defi_tvl', 0) / 1e9:.2f}B")

    # Test News/Events
    print("\n3. Testing RSS News Feeds...")
    news_feed = EventDataFeed(use_mock=False)  # Try live

    news_sources = ['coindesk']  # Start with crypto news (most reliable)
    news_data = news_feed.get_events(news_sources, minutes=60)

    print(f"   Found {news_data['count']} high-impact events")
    if news_data['events']:
        for event in news_data['events'][:3]:  # Show top 3
            print(f"   - [{event['source']}] {event['title'][:60]}...")
            print(f"     Impact: {event['impact_score']:.1f}, Sentiment: {event['sentiment']}")

    print("\n✓ All data sources tested\n")


def test_agent_signals():
    """Test each agent type with combined data."""
    print("=" * 70)
    print("TESTING AGENT SIGNAL GENERATION")
    print("=" * 70)

    # Create mock market data
    market_data = {
        'symbol': 'BTC',
        'price': 95000,
        'volume': 1_000_000,
        'timestamp': time.time()
    }

    # Create event data with all three sources
    event_data = {
        # Polymarket
        'polymarket': {
            'btc_100k': {
                'yes_probability': 0.68,
                'source': 'polymarket',
                'title': 'Bitcoin above $100k by 2025'
            },
            'fed_hike': {
                'yes_probability': 0.35,  # Low hike odds = bullish
                'source': 'polymarket',
                'title': 'Fed hikes in Q1 2025'
            }
        },

        # On-chain
        'onchain': {
            'total_exchange_inflows': 450_000_000,  # $450M
            'total_defi_tvl': 85_000_000_000,       # $85B
            'stablecoin_supply': {
                'total_stablecoins_usd': 150_000_000_000,
                'change_24h_usd': 500_000_000  # $500M increase
            }
        },

        # News
        'news_events': {
            'events': [
                {
                    'source': 'fed',
                    'title': 'Fed signals dovish stance in surprise statement',
                    'summary': 'Potential rate pause',
                    'impact_score': 3.5,
                    'sentiment': 'bullish',
                    'matched_keywords': ['rate decision', 'dovish']
                }
            ],
            'count': 1,
            'highest_impact': 3.5
        }
    }

    # Test each agent
    agents = [
        EventDrivenAgent(name="Polymarket Agent"),
        OnChainAgent(name="On-Chain Agent"),
        NewsAgent(name="News Agent"),
        HybridAgent(name="Hybrid 2/3"),
        StrictHybridAgent(name="Hybrid 3/3")
    ]

    print("\nScenario: Bullish alignment across all sources")
    print(f"  Polymarket: 68% BTC $100k, 35% Fed hike (bullish)")
    print(f"  On-chain: $450M inflows, $500M stablecoin increase")
    print(f"  News: Fed dovish signal (impact 3.5, bullish)\n")

    for agent in agents:
        signal = agent.generate_signal(market_data, event_data)

        if signal:
            print(f"\n{agent.name}:")
            print(f"  Action: {signal.action}")
            print(f"  Confidence: {signal.confidence:.1%}")
            print(f"  Reason: {signal.reason}")
        else:
            print(f"\n{agent.name}:")
            print(f"  No signal generated")

    print("\n✓ All agents tested\n")


def test_conflicting_sources():
    """Test what happens when sources disagree."""
    print("=" * 70)
    print("TESTING CONFLICTING SOURCES")
    print("=" * 70)

    market_data = {
        'symbol': 'BTC',
        'price': 95000,
        'timestamp': time.time()
    }

    # Create CONFLICTING signals
    event_data = {
        # Polymarket says bearish (Fed hike likely)
        'polymarket': {
            'fed_hike': {
                'yes_probability': 0.78,  # High hike odds = bearish
                'source': 'polymarket'
            }
        },

        # On-chain says bullish (big inflows)
        'onchain': {
            'total_exchange_inflows': 600_000_000,  # $600M inflows = bullish
            'total_defi_tvl': 85_000_000_000
        },

        # News is neutral/absent
        'news_events': {
            'events': [],
            'count': 0
        }
    }

    print("\nScenario: Sources CONFLICT")
    print("  Polymarket: 78% Fed hike (BEARISH)")
    print("  On-chain: $600M inflows (BULLISH)")
    print("  News: No events (NEUTRAL)\n")

    hybrid = HybridAgent(name="Hybrid 2/3")
    signal = hybrid.generate_signal(market_data, event_data)

    if signal:
        print(f"Hybrid Agent Decision:")
        print(f"  Action: {signal.action}")
        print(f"  Confidence: {signal.confidence:.1%}")
        print(f"  Reason: {signal.reason}")
    else:
        print("Hybrid Agent Decision:")
        print("  NO TRADE - Sources conflict!")
        print("  This is the key feature: avoid trading when signals disagree")

    print("\n✓ Conflict handling tested\n")


def run_live_demo():
    """
    Run a live demo with real data sources.
    Shows how the system works end-to-end.
    """
    print("=" * 70)
    print("LIVE MULTI-SOURCE DEMO")
    print("=" * 70)
    print("\nFetching live data from all three sources...\n")

    # Initialize feeds (try live, fall back to mock)
    poly_feed = PredictionMarketFeed(use_mock=False)
    onchain_feed = OnChainDataFeed(use_mock=False)
    news_feed = EventDataFeed(use_mock=False)

    # Fetch live data
    poly_data = poly_feed.get_events({
        'btc_100k': 'will-bitcoin-hit-100k-in-2024'
    })

    onchain_data = onchain_feed.get_onchain_metrics({
        'exchanges': ['binance'],
        'protocols': ['aave']
    })

    news_data = news_feed.get_events(['coindesk'], minutes=120)

    # Combine into event_data
    event_data = {
        'polymarket': poly_data,
        'onchain': onchain_data,
        'news_events': news_data
    }

    market_data = {
        'symbol': 'BTC',
        'price': 95000,
        'timestamp': time.time()
    }

    # Run hybrid agent
    hybrid = HybridAgent(name="Live Hybrid Agent")
    signal = hybrid.generate_signal(market_data, event_data)

    print("LIVE SIGNAL RESULT:")
    print("-" * 70)
    if signal:
        print(f"Action: {signal.action}")
        print(f"Confidence: {signal.confidence:.1%}")
        print(f"Reason: {signal.reason}")
    else:
        print("No signal generated (insufficient confirmation or conflicting sources)")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("MULTI-SOURCE SIGNAL FUSION TEST SUITE")
    print("=" * 70)
    print()

    try:
        # Test 1: Data sources
        test_data_sources()
        time.sleep(1)

        # Test 2: Agent signals
        test_agent_signals()
        time.sleep(1)

        # Test 3: Conflict handling
        test_conflicting_sources()
        time.sleep(1)

        # Test 4: Live demo (optional)
        print("=" * 70)
        print("OPTIONAL: Run live demo? (y/n)")
        # Auto-run for CI
        run_live_demo()

        print("=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
