"""
Quick test to verify Polymarket integration works.
Run this to discover active markets and test the adapter.
"""

from market_data.prediction_market_adapter import PredictionMarketFeed

def test_polymarket():
    feed = PredictionMarketFeed(use_mock=False)
    
    print("Testing Polymarket API Integration\n")
    print("="*60)
    
    # Discover markets
    print("\n1. Discovering relevant markets...")
    feed.discover_relevant_markets(['bitcoin', 'trump', 'fed', 'recession'])
    
    # Test specific market
    print("\n2. Testing specific market fetch...")
    test_slug = 'will-bitcoin-be-above-100k-by-december-31-2025'
    odds = feed.polymarket.get_market_odds(test_slug)
    
    if odds:
        print(f"✓ Successfully fetched: {odds['title']}")
        print(f"  YES probability: {odds['yes_probability']:.1%}")
        print(f"  Volume: ${odds['volume']:,.0f}")
    else:
        print("✗ Failed to fetch market")
    
    # Test trending
    print("\n3. Current trending markets...")
    trending = feed.polymarket.get_trending_markets(limit=5)
    for i, m in enumerate(trending, 1):
        print(f"{i}. {m['title']} ({m['yes_prob']:.1%})")
    
    print("\n" + "="*60)
    print("Polymarket integration ready!\n")

if __name__ == "__main__":
    test_polymarket()
