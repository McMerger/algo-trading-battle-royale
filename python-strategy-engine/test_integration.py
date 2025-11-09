"""
Quick integration test to verify all components work together.
Run this after setup to check everything is connected.
"""

import asyncio
from agents.trend_follower import TrendFollower
from agents.mean_reversion import MeanReversion
from agents.event_driven_agent import EventDrivenAgent
from agents.meta_bandit_agent import MetaBanditAgent
from market_data.prediction_market_adapter import PredictionMarketFeed
from orchestrator.battle_manager import BattleManager


async def test_basic_setup():
    """Test basic system setup."""
    print("Testing basic setup...")
    
    # Test agent creation
    try:
        trend = TrendFollower("Test_Trend")
        mean_rev = MeanReversion("Test_MeanRev")
        event = EventDrivenAgent("Test_Event")
        print("✓ Agents created successfully")
    except Exception as e:
        print(f"✗ Agent creation failed: {e}")
        return False
    
    # Test meta-agent
    try:
        meta = MetaBanditAgent([trend, mean_rev], "Test_Meta")
        print("✓ Meta-agent created successfully")
    except Exception as e:
        print(f"✗ Meta-agent creation failed: {e}")
        return False
    
    return True


async def test_polymarket_connection():
    """Test Polymarket API connection."""
    print("\nTesting Polymarket connection...")
    
    try:
        feed = PredictionMarketFeed(use_mock=False)
        
        # Try to fetch a known market
        test_slug = 'will-bitcoin-be-above-100000-on-january-1-2025'
        odds = feed.polymarket.get_market_odds(test_slug)
        
        if odds:
            print(f"✓ Polymarket connection successful")
            print(f"  Market: {odds['title'][:50]}...")
            print(f"  YES: {odds['yes_probability']:.1%}")
            return True
        else:
            print("✗ Polymarket connection failed (will use mock data)")
            return False
    except Exception as e:
        print(f"✗ Polymarket error: {e}")
        return False


async def test_battle_manager():
    """Test battle manager with mock data."""
    print("\nTesting battle manager...")
    
    try:
        agents = [
            TrendFollower("Trend"),
            EventDrivenAgent("Event")
        ]
        
        event_config = {'test': 'TEST-MOCK'}
        manager = BattleManager(agents, event_config=event_config)
        
        # Run one round with mock data
        market_data = {
            'timestamp': 1,
            'symbol': 'TEST',
            'price': 100,
            'volume': 1000,
            'volatility': 0.02
        }
        
        result = await manager.run_battle(market_data)
        
        print("✓ Battle manager working")
        return True
    except Exception as e:
        print(f"✗ Battle manager failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("="*60)
    print("INTEGRATION TEST")
    print("="*60)
    
    results = []
    
    results.append(await test_basic_setup())
    results.append(await test_polymarket_connection())
    results.append(await test_battle_manager())
    
    print("\n" + "="*60)
    if all(results):
        print("✓ ALL TESTS PASSED")
        print("System is ready to use!")
    else:
        print("✗ SOME TESTS FAILED")
        print("Check errors above and verify setup")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
