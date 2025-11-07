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
    price: float

class BaseAgent(ABC):
    """
    Base class for all trading agents.
    
    Key change: generate_signal now accepts optional event_data parameter.
    This lets event-aware agents use prediction market odds without breaking
    backward compatibility for classic price-only agents.
    """
    
    def __init__(self, name, initial_capital=100000):
        self.name = name
        self.capital = initial_capital
        self.positions = {}
        self.pnl = 0.0
        self.win_rate = 0.0
        self.trades = []
    
    @abstractmethod
    def generate_signal(self, market_data, event_data=None):
        """
        Generate trading signal from market and event data.
        
        Args:
            market_data: Dict with price, volume, etc.
            event_data: Optional dict with prediction market probabilities.
                       Format: {'fed_hike': {'yes_probability': 0.72, ...}, ...}
        
        Returns:
            Signal object or None if no action.
        """
        pass
    
    def update_performance(self, trade_result):
        """Update metrics after a trade."""
        self.trades.append(trade_result)
        self.pnl += trade_result['pnl']
        
        winning = sum(1 for t in self.trades if t['pnl'] > 0)
        self.win_rate = winning / len(self.trades) if self.trades else 0
    
    def get_stats(self):
        """Return performance summary."""
        return {
            'name': self.name,
            'pnl': self.pnl,
            'win_rate': self.win_rate,
            'total_trades': len(self.trades),
            'sharpe': self._calculate_sharpe()
        }
    
    def _calculate_sharpe(self):
        """Annualized Sharpe ratio."""
        if not self.trades:
            return 0.0
        returns = [t['pnl'] for t in self.trades]
        return np.mean(returns) / (np.std(returns) + 1e-6) * np.sqrt(252)
