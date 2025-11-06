import numpy as np
from agents.base_agent import BaseAgent, Signal

class MeanReversion(BaseAgent):
    def __init__(self, name="Mean Reversion", period=20, std_dev=2.0):
        super().__init__(name)
        self.period = period
        self.std_dev = std_dev
        self.price_history = []

    def generate_signal(self, market_data):
        price = market_data.get('price')
        if price is None:
            return None
        self.price_history.append(price)
        if len(self.price_history) < self.period:
            return None
        window = np.array(self.price_history[-self.period:])
        ma = np.mean(window)
        std = np.std(window)
        upper = ma + self.std_dev * std
        lower = ma - self.std_dev * std
        if price <= lower:
            action = 'BUY'
            confidence = min(0.6 + abs(price - lower) / ma, 0.95)
        elif price >= upper:
            action = 'SELL'
            confidence = min(0.6 + abs(price - upper) / ma, 0.95)
        else:
            action = 'HOLD'
            confidence = 0.5
        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'UNKNOWN'),
            action=action,
            confidence=confidence,
            size=100 * confidence,
            reason=f"Bollinger Bands: lower({lower:.2f}), upper({upper:.2f})",
            agent_name=self.name,
            price=price
        )
