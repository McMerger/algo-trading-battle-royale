"""
Main demo script showcasing the full system:
- Prediction market integration (Polymarket live data)
- Meta-agent with Thompson Sampling
- Event-driven agents
- Adversarial testing
- Explainability
"""

import asyncio
import argparse
import numpy as np
from datetime import datetime

from agents.base_agent import BaseAgent
from agents.trend_follower import TrendFollower
from agents.mean_reversion import MeanReversion
from agents.event_driven_agent import EventDrivenAgent, FedHikeAgent
from agents.meta_bandit_agent import MetaBanditAgent
from orchestrator.battle_manager import BattleManager
from scenario_injector import ScenarioInjector
from market_data.prediction_market_adapter import PredictionMarketFeed


def generate_mock_market_data(epoch):
    """Generate synthetic market data for demo."""
    base_price = 100
    trend = 0.001 * epoch
    noise = np.random.randn() * 0.5
    
    return {
        'timestamp': datetime.now().timestamp(),
        'symbol': 'SPY',
        'price': base_price + trend + noise,
        'volume': int(1000000 + np.random.randn() * 100000),
        'volatility': max(0.01, 0.015 + np.random.randn() * 0.005),
        'bid': base_price + trend + noise - 0.1,
        'ask': base_price + trend + noise + 0.1
    }


def get_event_config(use_live=True):
    """
    Get event configuration for Polymarket markets.
    
    Returns dict mapping event names to Polymarket slugs.
    Set use_live=False to use mock data only.
    """
    if not use_live:
        return {
            'fed_rate': 'FED-MOCK',
            'btc_100k': 'BTC-MOCK',
            'recession': 'RECESSION-MOCK'
        }
    
    # Live Polymarket market slugs
    # Find current markets at https://polymarket.com
    return {
        'btc_100k': 'will-bitcoin-be-above-100000-on-january-1-2025',
        'trump_wins': 'presidential-election-winner-2024',
        'fed_rate_high': 'will-the-fed-funds-rate-be-above-500-on-december-31-2024',
        'recession': 'will-the-us-enter-a-recession-in-2025'
    }


async def run_basic_demo(epochs=30, use_live_events=True):
    """Basic demo: agents competing with Polymarket event data."""
    print("\n" + "="*70)
    print(f"BASIC DEMO: Agent Competition with {'Live Polymarket' if use_live_events else 'Mock'} Events")
    print("="*70)
    
    # Create agents
    agents = [
        TrendFollower("TrendFollower", fast_period=5, slow_period=15),
        MeanReversion("MeanReversion", window=20, num_std=2.0),
        EventDrivenAgent("EventDriven", fed_threshold=0.65, shift_threshold=0.15)
    ]
    
    # Event configuration
    event_config = get_event_config(use_live=use_live_events)
    
    # Create battle manager
    manager = BattleManager(agents, event_config=event_config)
    
    # Run competition
    for epoch in range(epochs):
        market_data = generate_mock_market_data(epoch)
        result = await manager.run_battle(market_data)
        
        # Simulate trade execution and update performance
        if result['winning_signal']:
            pnl = np.random.randn() * 10  # Mock PnL
            for agent in agents:
                if agent.name == result['winning_signal'].agent_name:
                    agent.update_performance({'pnl': pnl})
        
        # Small delay to be respectful to API
        if use_live_events and epoch % 5 == 0:
            await asyncio.sleep(1)
    
    # Print results
    manager.print_leaderboard()


async def run_meta_agent_demo(epochs=30, use_live_events=True):
    """Demo with meta-agent that learns which strategy to trust."""
    print("\n" + "="*70)
    print("META-AGENT DEMO: Adaptive Strategy Selection")
    print("="*70)
    
    # Create sub-agents
    sub_agents = [
        TrendFollower("TrendFollower", fast_period=5, slow_period=15),
        MeanReversion("MeanReversion", window=20, num_std=2.0),
        EventDrivenAgent("EventDriven", fed_threshold=0.65),
        FedHikeAgent("FedHikeAgent", hike_threshold=0.70)
    ]
    
    # Create meta-agent
    meta = MetaBanditAgent(sub_agents, name="MetaBandit")
    
    # All agents including meta
    all_agents = sub_agents + [meta]
    
    event_config = get_event_config(use_live=use_live_events)
    manager = BattleManager(all_agents, event_config=event_config)
    
    for epoch in range(epochs):
        market_data = generate_mock_market_data(epoch)
        result = await manager.run_battle(market_data)
        
        if result['winning_signal']:
            pnl = np.random.randn() * 10
            
            # Update meta-agent if it was selected
            if result['winning_signal'].agent_name == meta.name:
                if meta.selection_history:
                    last_selection = meta.selection_history[-1]
                    selected_agent_name = last_selection['agent']
                    meta.update_from_result(selected_agent_name, pnl)
            
            # Update agent performance
            for agent in all_agents:
                if agent.name == result['winning_signal'].agent_name:
                    agent.update_performance({'pnl': pnl})
        
        if use_live_events and epoch % 5 == 0:
            await asyncio.sleep(1)
    
    manager.print_leaderboard()
    meta.print_weights()


async def run_stress_test_demo(use_live_events=True):
    """Demo adversarial testing."""
    print("\n" + "="*70)
    print("STRESS TEST DEMO: Adversarial Scenarios")
    print("="*70)
    
    agents = [
        TrendFollower("TrendFollower", fast_period=5, slow_period=15),
        MeanReversion("MeanReversion", window=20, num_std=2.0),
        EventDrivenAgent("EventDriven", fed_threshold=0.65)
    ]
    
    injector = ScenarioInjector()
    market_data = generate_mock_market_data(0)
    
    # Add event data
    if use_live_events:
        feed = PredictionMarketFeed()
        event_config = get_event_config(use_live=True)
        market_data['events'] = feed.get_events(event_config)
    else:
        market_data['events'] = {
            'fed_rate': {
                'source': 'mock',
                'yes_probability': 0.50,
                'title': 'Fed Rate Mock'
            }
        }
    
    results = injector.run_stress_test(agents, market_data)
    injector.print_stress_report(results)


async def discover_markets():
    """Helper to discover current Polymarket markets."""
    print("\n" + "="*70)
    print("DISCOVER POLYMARKET MARKETS")
    print("="*70)
    
    feed = PredictionMarketFeed()
    
    print("\nSearching for relevant markets...\n")
    keywords = ['bitcoin', 'trump', 'fed', 'recession', 'ethereum']
    
    for keyword in keywords:
        print(f"Keyword: {keyword}")
        markets = feed.polymarket.search_markets(query=keyword, limit=3)
        
        if markets:
            for m in markets:
                slug = m.get('slug', 'N/A')
                title = m.get('question', 'N/A')[:60]
                print(f"  - {slug}")
                print(f"    {title}...\n")
        else:
            print("  No markets found\n")
    
    print("\nTrending markets:")
    trending = feed.polymarket.get_trending_markets(limit=5)
    for i, m in enumerate(trending, 1):
        print(f"{i}. {m['title'][:60]}...")
        print(f"   Slug: {m['slug']}")
        print(f"   YES: {m['yes_prob']:.1%}, Volume: ${m['volume']:,.0f}\n")
    
    print("="*70 + "\n")


async def test_connection():
    """Test Polymarket API connection."""
    print("\n" + "="*70)
    print("TESTING POLYMARKET CONNECTION")
    print("="*70)
    
    feed = PredictionMarketFeed()
    
    # Test a known market
    test_slug = 'will-bitcoin-be-above-100000-on-january-1-2025'
    print(f"\nFetching: {test_slug}")
    
    odds = feed.polymarket.get_market_odds(test_slug)
    
    if odds:
        print(f"\n✓ Connection successful!")
        print(f"  Market: {odds['title']}")
        print(f"  YES probability: {odds['yes_probability']:.1%}")
        print(f"  NO probability: {odds['no_probability']:.1%}")
        print(f"  Volume: ${odds['volume']:,.0f}")
        print(f"  Active: {odds['active']}")
    else:
        print("\n✗ Connection failed. Using mock data fallback.")
    
    print("\n" + "="*70 + "\n")


async def main():
    parser = argparse.ArgumentParser(description='Algo Trading Battle Royale Demo')
    parser.add_argument('--mode', type=str, default='basic',
                       choices=['basic', 'meta', 'stress', 'discover', 'test', 'all'],
                       help='Demo mode to run')
    parser.add_argument('--epochs', type=int, default=30,
                       help='Number of epochs to run')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock event data instead of live Polymarket')
    
    args = parser.parse_args()
    
    use_live = not args.mock
    
    print("\n" + "="*70)
    print("ALGO TRADING BATTLE ROYALE")
    print("Prediction Market Integration + Adaptive Meta-Agent")
    if use_live:
        print("Using LIVE Polymarket data")
    else:
        print("Using MOCK event data")
    print("="*70)
    
    if args.mode == 'test':
        await test_connection()
        return
    
    if args.mode == 'discover':
        await discover_markets()
        return
    
    if args.mode == 'basic' or args.mode == 'all':
        await run_basic_demo(args.epochs, use_live_events=use_live)
    
    if args.mode == 'meta' or args.mode == 'all':
        await run_meta_agent_demo(args.epochs, use_live_events=use_live)
    
    if args.mode == 'stress' or args.mode == 'all':
        await run_stress_test_demo(use_live_events=use_live)
    
    print("\n" + "="*70)
    print("Demo complete. Check docs/ for guides on adding your own agents.")
    print("="*70 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
