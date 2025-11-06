"""Battle manager orchestrates agent competition with Google Gemini explanations"""
import asyncio
from typing import List, Dict, Optional
import numpy as np
from agents.base_agent import BaseAgent, Signal
from datetime import datetime
import os

# Google Gemini import - NEW SDK
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("  Google Gemini not installed. Install with: pip install google-genai")

class BattleManager:
    """Orchestrates live agent competitions and selects winning strategies"""
    
    def __init__(self, agents: List[BaseAgent], llm_enabled: bool = False, gemini_api_key: Optional[str] = None):
        self.agents = agents
        self.current_epoch = 0
        self.epoch_wins = {agent.name: 0 for agent in agents}
        self.llm_enabled = llm_enabled and GEMINI_AVAILABLE
        self.battle_history = []
        
        # Initialize Gemini if enabled
        if self.llm_enabled:
            api_key = gemini_api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if not api_key:
                print("  No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
                self.llm_enabled = False
            else:
                # Create client with API key
                self.gemini_client = genai.Client(api_key=api_key)
                self.gemini_model = 'gemini-2.0-flash'  # Updated model name
                print(" Google Gemini initialized successfully")
        
    async def run_battle(self, market_data: Dict) -> Dict:
        """Run one battle epoch with current market data"""
        self.current_epoch += 1
        
        print(f"\n EPOCH {self.current_epoch} - Battle Starting...")
        print(f"Market: {market_data.get('symbol')} @ ${market_data.get('price', 0):.2f}")
        
        # Collect signals from all agents
        signals = []
        for agent in self.agents:
            signal = agent.generate_signal(market_data)
            if signal and signal.action != 'HOLD':
                signals.append(signal)
                print(f" {agent.name}: {signal.action} {signal.size:.0f} shares ({signal.confidence:.1%} confidence)")
        
        if not signals:
            print("  No actionable signals this epoch")
            return {
                'winning_signal': None,
                'all_signals': [],
                'explanation': 'No agents generated actionable signals',
                'epoch': self.current_epoch,
                'timestamp': datetime.now().isoformat()
            }
        
        # Select winner using epsilon-greedy multi-armed bandit
        winner = self._select_winner(signals)
        self.epoch_wins[winner.agent_name] += 1
        
        # Generate explanation
        explanation = await self._generate_explanation(winner, signals, market_data)
        
        result = {
            'winning_signal': winner,
            'all_signals': signals,
            'explanation': explanation,
            'epoch': self.current_epoch,
            'timestamp': datetime.now().isoformat(),
            'leaderboard': self.get_leaderboard()
        }
        
        self.battle_history.append(result)
        
        print(f"\n WINNER: {winner.agent_name}")
        print(f" {explanation}\n")
        
        return result
    
    def _select_winner(self, signals: List[Signal], epsilon: float = 0.15) -> Signal:
        """Epsilon-greedy multi-armed bandit selection"""
        
        if np.random.random() < epsilon:
            # Explore: random selection
            winner = np.random.choice(signals)
            print(f" Exploration: Randomly selected {winner.agent_name}")
            return winner
        else:
            # Exploit: select best performing agent
            signal_scores = []
            for signal in signals:
                # Score based on: confidence + win rate + recent performance
                agent = next(a for a in self.agents if a.name == signal.agent_name)
                win_rate_bonus = agent.win_rate if hasattr(agent, 'win_rate') else 0.5
                epoch_win_bonus = self.epoch_wins[signal.agent_name] / max(self.current_epoch, 1)
                
                score = (signal.confidence * 0.5) + (win_rate_bonus * 0.3) + (epoch_win_bonus * 0.2)
                signal_scores.append((signal, score))
            
            winner = max(signal_scores, key=lambda x: x[1])[0]
            print(f" Exploitation: Selected best performer {winner.agent_name}")
            return winner
    
    async def _generate_explanation(self, winner: Signal, all_signals: List[Signal], market_data: Dict) -> str:
        """Generate human-readable trade explanation using Google Gemini"""
        
        if not self.llm_enabled:
            # Fallback to rule-based explanation
            return self._generate_rule_based_explanation(winner, all_signals, market_data)
        
        try:
            # Build prompt for Gemini
            prompt = self._build_gemini_prompt(winner, all_signals, market_data)
            
            # Generate response using NEW Gemini SDK
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"  Gemini API error: {e}. Using fallback explanation.")
            return self._generate_rule_based_explanation(winner, all_signals, market_data)
    
    def _build_gemini_prompt(self, winner: Signal, all_signals: List[Signal], market_data: Dict) -> str:
        """Build prompt for Gemini API"""
        
        prompt = f"""You are an expert trading analyst explaining the results of an AI trading agent competition.

Trading Battle Royale - Epoch {self.current_epoch}

MARKET CONTEXT:
- Symbol: {market_data.get('symbol', 'UNKNOWN')}
- Current Price: ${market_data.get('price', 0):.2f}
- Volume: {market_data.get('volume', 0):,}
- Bid: ${market_data.get('bid', 0):.2f}
- Ask: ${market_data.get('ask', 0):.2f}

COMPETING AGENTS:
{self._format_signals_for_prompt(all_signals)}

BATTLE WINNER:
- Agent: {winner.agent_name}
- Action: {winner.action}
- Size: {winner.size:.0f} shares
- Confidence: {winner.confidence:.1%}
- Strategy Reason: {winner.reason}

AGENT PERFORMANCE HISTORY:
{self._format_agent_history(winner.agent_name)}

Provide a concise 2-3 sentence explanation covering:
1. Why this agent won the battle (based on its strategy and confidence)
2. How current market conditions favor this approach
3. Expected outcome and risk assessment

Keep it professional but engaging. Focus on actionable insights."""
        
        return prompt
    
    def _format_signals_for_prompt(self, signals: List[Signal]) -> str:
        """Format signals for the prompt"""
        lines = []
        for i, signal in enumerate(signals, 1):
            lines.append(
                f"{i}. {signal.agent_name}: {signal.action} {signal.size:.0f} shares "
                f"(confidence: {signal.confidence:.1%}) - {signal.reason}"
            )
        return "\n".join(lines)
    
    def _format_agent_history(self, agent_name: str) -> str:
        """Format agent performance history"""
        agent = next((a for a in self.agents if a.name == agent_name), None)
        if not agent:
            return "No history available"
        
        stats = agent.get_stats()
        return (
            f"- Total PnL: ${stats['pnl']:.2f}\n"
            f"- Win Rate: {stats['win_rate']:.1%}\n"
            f"- Total Trades: {stats['total_trades']}\n"
            f"- Sharpe Ratio: {stats['sharpe']:.2f}\n"
            f"- Epochs Won: {self.epoch_wins[agent_name]}"
        )
    
    def _generate_rule_based_explanation(self, winner: Signal, all_signals: List[Signal], market_data: Dict) -> str:
        """Fallback rule-based explanation when LLM is unavailable"""
        
        explanation = (
            f"The {winner.agent_name} agent secured victory with {winner.confidence:.0%} confidence. "
            f"Strategy: {winner.reason}. "
            f"Market conditions: Price ${market_data.get('price', 0):.2f}, "
            f"competing against {len(all_signals) - 1} other strategies. "
            f"Expected outcome: {winner.action} {winner.size:.0f} shares."
        )
        
        return explanation
    
    def get_leaderboard(self) -> List[Dict]:
        """Get current agent leaderboard"""
        leaderboard = []
        for agent in self.agents:
            stats = agent.get_stats()
            stats['epoch_wins'] = self.epoch_wins[agent.name]
            leaderboard.append(stats)
        
        return sorted(leaderboard, key=lambda x: x['pnl'], reverse=True)
    
    def print_leaderboard(self):
        """Print formatted leaderboard"""
        print("\n" + "="*70)
        print("AGENT LEADERBOARD")
        print("="*70)
        print(f"{'Agent':<20} {'PnL':>10} {'Win Rate':>10} {'Trades':>8} {'Sharpe':>8} {'Epochs Won':>12}")
        print("-"*70)
        
        for agent_stats in self.get_leaderboard():
            print(f"{agent_stats['name']:<20} "
                  f"${agent_stats['pnl']:>9.2f} "
                  f"{agent_stats['win_rate']:>9.1%} "
                  f"{agent_stats['total_trades']:>8} "
                  f"{agent_stats['sharpe']:>8.2f} "
                  f"{agent_stats['epoch_wins']:>12}")
        
        print("="*70 + "\n")
