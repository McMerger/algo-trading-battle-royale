import asyncio
from typing import List, Dict
from agents.base_agent import BaseAgent, Signal
import openai
from datetime import datetime

class BattleManager:
    """Orchestrates live agent competitions and selects winning strategies"""
    
    def __init__(self, agents: List[BaseAgent], llm_api_key: str):
        self.agents = agents
        self.current_epoch = 0
        self.epoch_duration = 300  # 5 minutes per epoch
        self.agent_scores = {agent.name: 0 for agent in agents}
        self.llm_client = openai.OpenAI(api_key=llm_api_key)
        
    async def run_battle(self, market_data_stream):
        """Run continuous agent battle with live data"""
        print(f"🏆 Starting Trading Battle Royale - Epoch {self.current_epoch}")
        
        signals = []
        for agent in self.agents:
            signal = agent.generate_signal(market_data_stream)
            if signal:
                signals.append(signal)
        
        # Multi-armed bandit selection: epsilon-greedy
        winner = self._select_winner(signals)
        
        # Generate LLM explanation
        explanation = await self._generate_llm_summary(winner, signals, market_data_stream)
        
        return {
            'winning_signal': winner,
            'all_signals': signals,
            'explanation': explanation,
            'epoch': self.current_epoch,
            'timestamp': datetime.now().isoformat()
        }
    
    def _select_winner(self, signals: List[Signal]) -> Signal:
        """Epsilon-greedy multi-armed bandit selection"""
        epsilon = 0.1
        
        if np.random.random() < epsilon:
            # Explore: random selection
            return np.random.choice(signals)
        else:
            # Exploit: select best performing agent
            agent_scores = [(s, self.agent_scores[s.agent_name]) for s in signals]
            return max(agent_scores, key=lambda x: x[1])[0]
    
    async def _generate_llm_summary(self, winner: Signal, all_signals: List[Signal], market_data: Dict) -> str:
        """Generate human-readable trade explanation using LLM"""
        
        prompt = f"""
        Trading Battle Royale - Epoch {self.current_epoch}
        
        Market Context:
        - Price: ${market_data['price']:.2f}
        - Volume: {market_data['volume']}
        - Volatility: {market_data['volatility']:.2%}
        
        Competing Agents:
        {self._format_signals(all_signals)}
        
        WINNER: {winner.agent_name}
        Action: {winner.action} {winner.size} shares
        Confidence: {winner.confidence:.1%}
        Reason: {winner.reason}
        
        Explain in 2-3 sentences:
        1. Why this agent won the battle
        2. Market conditions that favored this strategy
        3. Expected outcome and risk assessment
        """
        
        response = self.llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        
        return response.choices[0].message.content
    
    def _format_signals(self, signals: List[Signal]) -> str:
        return "\n".join([
            f"- {s.agent_name}: {s.action} (confidence: {s.confidence:.1%})"
            for s in signals
        ])
