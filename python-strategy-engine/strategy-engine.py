# Main class for live trading agent competition.
# Handles agent registration, real-time scoring, and bandit-based selection.

import random
from typing import Dict, Callable, List

class TradingAgent:
    def __init__(self, name, strategy_func: Callable, params: dict=None):
        self.name = name
        self.strategy_func = strategy_func
        self.params = params if params else {}
        self.total_score = 0
        self.recent_scores = []

    def run(self, market_data):
        result = self.strategy_func(market_data, **self.params)
        score = result.get("score", 0)
        self.recent_scores.append(score)
        if len(self.recent_scores) > 100:
            self.recent_scores.pop(0)
        self.total_score += score
        return result

class BanditSelector:
    def __init__(self):
        self.agents: Dict[str, TradingAgent] = {}
        self.agent_order: List[str] = []
    
    def add_agent(self, name: str, agent: TradingAgent):
        if name in self.agents:
            raise ValueError(f"Agent '{name}' already registered.")
        self.agents[name] = agent
        self.agent_order.append(name)

    def remove_agent(self, name: str):
        if name in self.agents:
            del self.agents[name]
            self.agent_order.remove(name)

    def select_winner(self, market_data):
        if not self.agents:
            return None, "No agents available."
        scores = {}
        for name, agent in self.agents.items():
            result = agent.run(market_data)
            scores[name] = result.get("score", 0)
        # Simple epsilon-greedy bandit logic (high performer, sometimes explore)
        epsilon = 0.1
        if random.random() < epsilon:
            winner = random.choice(self.agent_order)
        else:
            winner = max(scores, key=scores.get)
        reason = f"Selected '{winner}' (score={scores[winner]})"
        return winner, reason

    def get_scores(self):
        return {name: ag.total_score for name, ag in self.agents.items()}
