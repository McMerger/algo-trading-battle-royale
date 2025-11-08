"""
Main demo script showcasing the full system:
- Prediction market integration
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
from explainability.explainability import SimpleExplainer


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


async def run_basic_demo(epochs=30):
    """Basic demo: agents competing with mock event data."""
    print("\n" + "="*70)
    print("BASIC DEMO: Agent Competition with Mock Events")
    print("="*70)
    
    # Create agents
    agents = [
        TrendFollower("TrendFollower", fast_period=5, slow_period=15),
        MeanReversion("MeanReversion", window=20, num_std=2.0),
        EventDrivenAgent("EventDriven", fed_threshold=0.65)
    ]
    
    # Event configuration (using mock data since no API keys)
    event_config = {
        'fed_hike': 'FED-MOCK',
        'recession': 'RECESSION-MOCK'
    }
    
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
    
    # Print results
    manager.print_leaderboard()


async def run_meta_agent_demo(epochs=30):
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
    
    event_config = {
        'fed_hike': 'FED-MOCK',
        'recession': 'RECESSION-MOCK'
    }
    
    manager = BattleManager(all_agents, event_config=event_config)
    
    for epoch in range(epochs):
        market_data = generate_mock_market_data(epoch)
        result = await manager.run_battle(market_data)
        
        if result['winning_signal']:
            pnl = np.random.randn() * 10
            
            # Update meta-agent if it was selected
            if result['winning_signal'].agent_name == meta.name:
                # Extract which sub-agent was actually chosen
                # (stored in selection_history)
                if meta.selection_history:
                    last_selection = meta.selection_history[-1]
                    selected_agent_name = last_selection['agent']
                    meta.update_from_result(selected_agent_name, pnl)
            
            # Update agent performance
            for agent in all_agents:
                if agent.name == result['winning_signal'].agent_name:
                    agent.update_performance({'pnl': pnl})
    
    manager.print_leaderboard()
    meta.print_weights()


async def run_stress_test_demo():
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
    
    # Add mock events for stress testing
    market_data['events'] = {
        'fed_hike': {
            'source': 'mock',
            'yes_probability': 0.50,
            'title': 'Fed Hike Mock'
        }
    }
    
    results = injector.run_stress_test(agents, market_data)
    injector.print_stress_report(results)


async def run_explainability_demo(epochs=10):
    """Demo feature attribution and explainability."""
    print("\n" + "="*70)
    print("EXPLAINABILITY DEMO: Feature Attribution")
    print("="*70)
    
    agents = [
        EventDrivenAgent("EventDriven", fed_threshold=0.65)
    ]
    
    event_config = {'fed_hike': 'FED-MOCK'}
    manager = BattleManager(agents, event_config=event_config)
    explainer = SimpleExplainer()
    
    for epoch in range(epochs):
        market_data = generate_mock_market_data(epoch)
        result = await manager.run_battle(market_data)
        
        if result['winning_signal']:
            explanation = explainer.explain_signal(
                result['winning_signal'],
                market_data,
                result.get('event_data')
            )
            
            if epoch < 3:  # Print first few for demo
                explainer.print_explanation(explanation)
    
    explainer.print_summary()


async def main():
    parser = argparse.ArgumentParser(description='Algo Trading Battle Royale Demo')
    parser.add_argument('--mode', type=str, default='basic',
                       choices=['basic', 'meta', 'stress', 'explain', 'all'],
                       help='Demo mode to run')
    parser.add_argument('--epochs', type=int, default=30,
                       help='Number of epochs to run')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("ALGO TRADING BATTLE ROYALE")
    print("Prediction Market Integration + Adaptive Meta-Agent")
    print("="*70)
    
    if args.mode == 'basic' or args.mode == 'all':
        await run_basic_demo(args.epochs)
    
    if args.mode == 'meta' or args.mode == 'all':
        await run_meta_agent_demo(args.epochs)
    
    if args.mode == 'stress' or args.mode == 'all':
        await run_stress_test_demo()
    
    if args.mode == 'explain' or args.mode == 'all':
        await run_explainability_demo(min(args.epochs, 10))
    
    print("\n" + "="*70)
    print("Demo complete. Check docs/ for guides on adding your own agents.")
    print("="*70 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
