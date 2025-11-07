"""
Battle manager orchestrates agent competitions.

Key update: now fetches event data from prediction markets and passes it
to all agents each round. Rationale output includes event context.
"""

import asyncio
from typing import List, Dict, Optional
import numpy as np
from agents.base_agent import BaseAgent, Signal
from datetime import datetime
from market_data.prediction_market_adapter import PredictionMarketFeed
import os

# Gemini for explanations (optional)
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class BattleManager:
    """
    Runs agent competitions with prediction market event integration.
    """
    
    def __init__(self, agents, event_config=None, llm_enabled=False, gemini_api_key=None):
        self.agents = agents
        self.current_epoch = 0
        self.epoch_wins = {agent.name: 0 for agent in agents}
        self.battle_history = []
        
        # Event configuration: map event names to market IDs
        self.event_config = event_config or {}
        self.event_feed = PredictionMarketFeed(use_mock=not event_config)
        
        # LLM for explanations
        self.llm_enabled = llm_enabled and GEMINI_AVAILABLE
        if self.llm_enabled:
            api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("No Gemini API key found. Explanations will be rule-based.")
                self.llm_enabled = False
            else:
                self.gemini_client = genai.Client(api_key=api_key)
                self.gemini_model = 'gemini-2.0-flash'
    
    async def run_battle(self, market_data):
        """Run one competition round with current market and event data."""
        self.current_epoch += 1
        
        print(f"\nEpoch {self.current_epoch}")
        print(f"Market: {market_data.get('symbol')} @ ${market_data.get('price', 0):.2f}")
        
        # Fetch event data if configured
        event_data = None
        if self.event_config:
            event_data = self.event_feed.get_events(self.event_config)
            if event_data:
                print("Event probabilities:")
                for name, data in event_data.items():
                    prob = data.get('yes_probability', 0)
                    print(f"  {name}: {prob:.1%}")
        
        # Collect signals from all agents
        signals = []
        for agent in self.agents:
            signal = agent.generate_signal(market_data, event_data)
            if signal and signal.action != 'HOLD':
                signals.append(signal)
                print(f"{agent.name}: {signal.action} {signal.size:.0f} @ {signal.confidence:.1%}")
        
        if not signals:
            print("No actionable signals this round")
            return {
                'winning_signal': None,
                'all_signals': [],
                'explanation': 'No agents produced signals',
                'epoch': self.current_epoch,
                'event_data': event_data
            }
        
        # Select winner
        winner = self._select_winner(signals)
        self.epoch_wins[winner.agent_name] += 1
        
        # Generate explanation
        explanation = await self._generate_explanation(winner, signals, market_data, event_data)
        
        result = {
            'winning_signal': winner,
            'all_signals': signals,
            'explanation': explanation,
            'epoch': self.current_epoch,
            'timestamp': datetime.now().isoformat(),
            'event_data': event_data,
            'leaderboard': self.get_leaderboard()
        }
        
        self.battle_history.append(result)
        
        print(f"\nWinner: {winner.agent_name}")
        print(f"Reason: {explanation}\n")
        
        return result
    
    def _select_winner(self, signals, epsilon=0.15):
        """Epsilon-greedy: 15% explore, 85% exploit."""
        if np.random.random() < epsilon:
            winner = np.random.choice(signals)
            print(f"[Explore] Random: {winner.agent_name}")
            return winner
        
        scores = []
        for signal in signals:
            agent = next(a for a in self.agents if a.name == signal.agent_name)
            win_rate = getattr(agent, 'win_rate', 0.5)
            epoch_wins = self.epoch_wins[signal.agent_name] / max(self.current_epoch, 1)
            score = (signal.confidence * 0.5) + (win_rate * 0.3) + (epoch_wins * 0.2)
            scores.append((signal, score))
        
        winner = max(scores, key=lambda x: x[1])[0]
        print(f"[Exploit] Best: {winner.agent_name}")
        return winner
    
    async def _generate_explanation(self, winner, all_signals, market_data, event_data):
        if not self.llm_enabled:
            return self._rule_based_explanation(winner, market_data, event_data)
        
        try:
            prompt = self._build_prompt(winner, all_signals, market_data, event_data)
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"LLM failed: {e}")
            return self._rule_based_explanation(winner, market_data, event_data)
    
    def _rule_based_explanation(self, winner, market_data, event_data):
        exp = f"{winner.agent_name} selected ({winner.confidence:.0%} confidence). {winner.reason}"
        if event_data:
            events = ", ".join([f"{k}: {v.get('yes_probability', 0):.1%}" for k, v in event_data.items()])
            exp += f" Event context: {events}."
        return exp
    
    def _build_prompt(self, winner, all_signals, market_data, event_data):
        lines = [f"Round {self.current_epoch} winner: {winner.agent_name}",
                 f"Market: {market_data.get('symbol')} @ ${market_data.get('price', 0):.2f}"]
        
        if event_data:
            lines.append("Events:")
            for k, v in event_data.items():
                lines.append(f"- {k}: {v.get('yes_probability', 0):.1%}")
        
        lines.append(f"\nWinner reason: {winner.reason}")
        lines.append("\nExplain this decision in 2-3 sentences.")
        return "\n".join(lines)
    
    def get_leaderboard(self):
        board = []
        for agent in self.agents:
            stats = agent.get_stats()
            stats['epoch_wins'] = self.epoch_wins[agent.name]
            board.append(stats)
        return sorted(board, key=lambda x: x['pnl'], reverse=True)
    
    def print_leaderboard(self):
        print("\n" + "="*70)
        print("LEADERBOARD")
        print("="*70)
        print(f"{'Agent':<25} {'PnL':>10} {'Win%':>8} {'Trades':>8} {'Sharpe':>8}")
        print("-"*70)
        for stats in self.get_leaderboard():
            print(f"{stats['name']:<25} ${stats['pnl']:>9.2f} {stats['win_rate']:>7.1%} "
                  f"{stats['total_trades']:>8} {stats['sharpe']:>8.2f}")
        print("="*70 + "\n")
