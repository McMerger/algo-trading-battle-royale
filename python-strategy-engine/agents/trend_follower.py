"""
Classic trend-following agent using moving average crossover.
Baseline strategy for comparison against event-driven agents.
"""

from agents.base_agent import BaseAgent, Signal
import numpy as np


class TrendFollower(BaseAgent):
    """
    Moving average crossover strategy.
    Buy when fast MA crosses above slow MA, sell on opposite.
    """
    
    def __init__(self, name="TrendFollower", fast_period=5, slow_period=15):
        super().__init__(name)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.price_history = []
    
    def generate_signal(self, market_data, event_data=None):
        price = market_data.get('price', 0)
        self.price_history.append(price)
        
        # Need enough history
        if len(self.price_history) < self.slow_period:
            return None
        
        # Keep history bounded
        if len(self.price_history) > self.slow_period + 10:
            self.price_history.pop(0)
        
        # Calculate MAs
        fast_ma = np.mean(self.price_history[-self.fast_period:])
        slow_ma = np.mean(self.price_history[-self.slow_period:])
        
        # Previous MAs for crossover detection
        if len(self.price_history) > self.slow_period:
            prev_fast = np.mean(self.price_history[-self.fast_period-1:-1])
            prev_slow = np.mean(self.price_history[-self.slow_period-1:-1])
        else:
            return None
        
        # Detect crossover
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            # Bullish crossover
            action = 'BUY'
            confidence = min((fast_ma - slow_ma) / slow_ma * 10, 0.9)
            reason = f"MA crossover: fast {fast_ma:.2f} > slow {slow_ma:.2f}"
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            # Bearish crossover
            action = 'SELL'
            confidence = min((slow_ma - fast_ma) / slow_ma * 10, 0.9)
            reason = f"MA crossover: fast {fast_ma:.2f} < slow {slow_ma:.2f}"
        else:
            return None
        
        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'UNKNOWN'),
            action=action,
            confidence=max(confidence, 0.5),
            size=100,
            reason=reason,
            agent_name=self.name,
            price=price
        )
