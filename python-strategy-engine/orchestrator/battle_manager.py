"""
Battle manager orchestrates agent competitions.
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
        
        # Select winner (epsilon-greedy with performance weighting)
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
        """
        Epsilon-greedy selection with performance weighting.
        15% explore, 85% exploit best performer.
        """
        if np.random.random() < epsilon:
            winner = np.random.choice(signals)
            print(f"[Explore] Randomly selected {winner.agent_name}")
            return winner
        else:
            scores = []
            for signal in signals:
                agent = next(a for a in self.agents if a.name == signal.agent_name)
                
                # Score = confidence + historical performance
                win_rate = getattr(agent, 'win_rate', 0.5)
                epoch_wins = self.epoch_wins[signal.agent_name] / max(self.current_epoch, 1)
                
                score = (signal.confidence * 0.5) + (win_rate * 0.3) + (epoch_wins * 0.2)
                scores.append((signal, score))
            
            winner = max(scores, key=lambda x: x[1])[0]
            print(f"[Exploit] Selected top performer {winner.agent_name}")
            return winner
    
    async def _generate_explanation(self, winner, all_signals, market_data, event_data):
        """Generate human explanation for the trade decision."""
        if not self.llm_enabled:
            return self._rule_based_explanation(winner, all_signals, market_data, event_data)
        
        try:
            prompt = self._build_explanation_prompt(winner, all_signals, market_data, event_data)
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"LLM explanation failed: {e}")
            return self._rule_based_explanation(winner, all_signals, market_data, event_data)
    
    def _rule_based_explanation(self, winner, all_signals, market_data, event_data):
        """Fallback explanation without LLM."""
        explanation = (f"{winner.agent_name} selected with {winner.confidence:.0%} confidence. "
                      f"{winner.reason}")
        
        if event_data:
            event_summary = ", ".join([f"{k}: {v.get('yes_probability', 0):.1%}" 
                                      for k, v in event_data.items()])
            explanation += f" Event context: {event_summary}."
        
        return explanation
    
    def _build_explanation_prompt(self, winner, all_signals, market_data, event_data):
        """Build prompt for LLM explanation."""
        prompt = f"""Trading competition round {self.current_epoch}.

Market: {market_data.get('symbol')} @ ${market_data.get('price', 0):.2f}
Volume: {market_data.get('volume', 0):,}

"""
        
        if event_data:
            prompt += "Event Probabilities:\n"
            for name, data in event_data.items():
                prob = data.get('yes_probability', 0)
                prompt += f"- {name}: {prob:.1%
