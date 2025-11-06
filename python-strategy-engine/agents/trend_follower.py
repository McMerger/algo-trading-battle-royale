import numpy as np
from agents.base_agent import BaseAgent, Signal

class TrendFollower(BaseAgent):
    def __init__(self, name="Trend Follower", fast_period=10, slow_period=30):
        super().__init__(name)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.price_history = []

    def generate_signal(self, market_data):
        price = market_data.get('price')
        if price is None:
            return None
        self.price_history.append(price)
        if len(self.price_history) < self.slow_period:
            return None
        fast_ma = np.mean(self.price_history[-self.fast_period:])
        slow_ma = np.mean(self.price_history[-self.slow_period:])
        if fast_ma > slow_ma:
            action = 'BUY'
            confidence = min(0.5 + (fast_ma - slow_ma) / slow_ma, 0.95)
        elif fast_ma < slow_ma:
            action = 'SELL'
            confidence = min(0.5 + (slow_ma - fast_ma) / slow_ma, 0.95)
        else:
            action = 'HOLD'
            confidence = 0.5
        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'UNKNOWN'),
            action=action,
            confidence=confidence,
            size=100 * confidence,
            reason=f"MA crossover: fast({fast_ma:.2f}), slow({slow_ma:.2f})",
            agent_name=self.name,
            price=price
        )
