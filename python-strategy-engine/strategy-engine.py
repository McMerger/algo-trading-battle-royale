# Main script for live trading agent competition.
# Handles agent registration, scoring, and competitive selection using modular agent classes.

import asyncio
import numpy as np
import time
import os

# Modular agent imports
from agents.trend_follower import TrendFollower
from agents.mean_reversion import MeanReversion
from orchestrator.battle_manager import BattleManager

def generate_mock_market_data(step: int, base_price: float = 100.0):
    """Produce simple synthetic market data for test runs."""
    trend = 0.01 * np.sin(step / 10)
    noise = np.random.normal(0, 0.5)
    price = base_price + trend + noise
    return {
        'symbol': 'AAPL',
        'price': price,
        'volume': np.random.randint(1000, 10000),
        'timestamp': time.time(),
        'bid': price - 0.01,
        'ask': price + 0.01,
        'open': price - 0.5,
        'high': price + 0.5,
        'low': price - 0.5,
        'close': price
    }

async def run_competition(num_epochs: int = 20, use_gemini: bool = False):
    print("-" * 60)
    print("Trading Agent Competition Demo")
    if use_gemini:
        print("LLM explanations are enabled (Google Gemini).")
    print("-" * 60)

    # Define agents for the competition
    agents = [
        TrendFollower(name="Trend Follower Fast", fast_period=5, slow_period=15),
        TrendFollower(name="Trend Follower Slow", fast_period=10, slow_period=30),
        MeanReversion(name="Mean Reversion Tight", period=15, std_dev=1.5),
        MeanReversion(name="Mean Reversion Wide", period=20, std_dev=2.5),
    ]

    gemini_key = os.getenv('GEMINI_API_KEY')
    battle_manager = BattleManager(agents=agents, llm_enabled=use_gemini, gemini_api_key=gemini_key)

    for epoch in range(num_epochs):
        market_data = generate_mock_market_data(epoch)
        result = await battle_manager.run_battle(market_data)

        # Simulate execution and scoring for the winning agent
        if result['winning_signal']:
            winner_signal = result['winning_signal']
            simulated_pnl = np.random.normal(10, 50)
            agent = next(a for a in agents if a.name == winner_signal.agent_name)
            from agents.base_agent import Trade
            trade = Trade(
                signal=winner_signal,
                execution_price=market_data['price'],
                execution_time=time.time(),
                pnl=simulated_pnl,
                slippage=0.01
            )
            agent.update_performance(trade)

        # Print summary every 5 epochs
        if (epoch + 1) % 5 == 0:
            battle_manager.print_leaderboard()

        await asyncio.sleep(0.1)

    print("\nCompetition finished.")
    battle_manager.print_leaderboard()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run trading agent competition demo')
    parser.add_argument('--epochs', type=int, default=30, help='Number of epochs to run')
    parser.add_argument('--gemini', action='store_true', help='Enable Google Gemini explanations')
    args = parser.parse_args()
    asyncio.run(run_competition(num_epochs=args.epochs, use_gemini=args.gemini))
