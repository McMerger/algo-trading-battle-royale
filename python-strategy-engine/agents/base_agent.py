from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np

@dataclass
class Signal:
    timestamp: float
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    size: float
    reason: str
    agent_name: str

class BaseAgent(ABC):
    """Base class for all trading agents in the battle royale"""
    
    def __init__(self, name: str, initial_capital: float = 100000):
        self.name = name
        self.capital = initial_capital
        self.positions = {}
        self.pnl = 0.0
        self.win_rate = 0.0
        self.trades = []
        
    @abstractmethod
    def generate_signal(self, market_data: Dict) -> Optional[Signal]:
        """Generate trading signal based on market data"""
        pass
    
    def update_performance(self, trade_result: Dict):
        """Update agent performance metrics"""
        self.trades.append(trade_result)
        self.pnl += trade_result['pnl']
        winning_trades = sum(1 for t in self.trades if t['pnl'] > 0)
        self.win_rate = winning_trades / len(self.trades) if self.trades else 0
    
    def get_stats(self) -> Dict:
        return {
            'name': self.name,
            'pnl': self.pnl,
            'win_rate': self.win_rate,
            'total_trades': len(self.trades),
            'sharpe': self._calculate_sharpe()
        }
    
    def _calculate_sharpe(self) -> float:
        if not self.trades:
            return 0.0
        returns = [t['pnl'] for t in self.trades]
        return np.mean(returns) / (np.std(returns) + 1e-6) * np.sqrt(252)
