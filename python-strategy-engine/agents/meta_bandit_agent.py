"""
Meta-agent using Thompson Sampling (multi-armed bandit).
"""

from typing import List, Dict, Optional
import numpy as np
from agents.base_agent import BaseAgent, Signal


class MetaBanditAgent(BaseAgent):
    """
    Meta-agent that adaptively selects sub-agents using Thompson Sampling.
    """
    
    def __init__(self, sub_agents, name="MetaBanditAgent"):
        super().__init__(name)
        self.sub_agents = sub_agents
        
        # Beta distribution parameters for each agent
        # Start with uniform prior: Beta(1, 1)
        self.alpha = np.ones(len(sub_agents))  # successes
        self.beta = np.ones(len(sub_agents))   # failures
        
        # History tracking
        self.selection_history = []
        self.agent_rewards = {agent.name: [] for agent in sub_agents}
    
    def generate_signal(self, market_data, event_data=None):
        """
        Pick best agent via Thompson Sampling, return its signal.
        """
        # Get signals from all sub-agents
        signals = []
        for agent in self.sub_agents:
            sig = agent.generate_signal(market_data, event_data)
            if sig and sig.action != 'HOLD':
                signals.append(sig)
        
        if not signals:
            return None
        
        # Thompson Sampling: sample from each agent's Beta distribution
        samples = np.random.beta(self.alpha, self.beta)
        
        # Pick agent with highest sample
        best_idx = np.argmax(samples)
        selected = signals[min(best_idx, len(signals)-1)]
        
        # Log this selection
        self.selection_history.append({
            'agent': selected.agent_name,
            'timestamp': market_data.get('timestamp', 0),
            'confidence': samples[best_idx],
            'all_samples': samples.tolist()
        })
        
        # Update signal to show meta-agent provenance
        selected.reason = (f"[META] Selected {selected.agent_name} "
                          f"(confidence {samples[best_idx]:.1%}). "
                          f"{selected.reason}")
        selected.agent_name = self.name
        
        return selected
    
    def update_from_result(self, agent_name, reward):
        """
        Update Beta distributions after a trade outcome.
        
        Call this with the selected agent name and PnL.
        Positive PnL = success, negative = failure.
        """
        idx = next((i for i, a in enumerate(self.sub_agents) if a.name == agent_name), None)
        if idx is None:
            return
        
        if reward > 0:
            self.alpha[idx] += 1
        else:
            self.beta[idx] += 1
        
        self.agent_rewards[agent_name].append(reward)
    
    def get_agent_stats(self):
        """Detailed stats about agent selection."""
        stats = {
            'meta_agent': self.name,
            'sub_agents': {},
            'selections': {},
            'confidence': {}
        }
        
        for i, agent in enumerate(self.sub_agents):
            name = agent.name
            count = sum(1 for h in self.selection_history if h['agent'] == name)
            
            # Mean of Beta(alpha, beta) is alpha / (alpha + beta)
            conf = self.alpha[i] / (self.alpha[i] + self.beta[i])
            
            stats['sub_agents'][name] = agent.get_stats()
            stats['selections'][name] = count
            stats['confidence'][name] = conf
        
        return stats
    
    def print_weights(self):
        """Human-readable visualization of agent selection confidence."""
        print("\n" + "="*60)
        print("META-AGENT SELECTION CONFIDENCE")
        print("="*60)
        
        for i, agent in enumerate(self.sub_agents):
            conf = self.alpha[i] / (self.alpha[i] + self.beta[i])
            bar_len = int(conf * 40)
            bar = '█' * bar_len + '░' * (40 - bar_len)
            print(f"{agent.name:25} [{bar}] {conf:.1%}")
        
        print("="*60 + "\n")
