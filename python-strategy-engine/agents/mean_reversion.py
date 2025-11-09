"""
Mean reversion strategy using Bollinger Bands.
Baseline strategy for comparison.
"""

from agents.base_agent import BaseAgent, Signal
import numpy as np


class MeanReversion(BaseAgent):
    """
    Bollinger Band mean reversion.
    Buy when price touches lower band, sell at upper band.
    """
    
    def __init__(self, name="MeanReversion", window=20, num_std=2.0):
        super().__init__(name)
        self.window = window
        self.num_std = num_std
        self.price_history = []
    
    def generate_signal(self, market_data, event_data=None):
        price = market_data.get('price', 0)
        self.price_history.append(price)
        
        # Need enough history
        if len(self.price_history) < self.window:
            return None
        
        # Keep bounded
        if len(self.price_history) > self.window + 10:
            self.price_history.pop(0)
        
        # Calculate Bollinger Bands
        recent_prices = self.price_history[-self.window:]
        mean_price = np.mean(recent_prices)
        std_price = np.std(recent_prices)
        
        upper_band = mean_price + self.num_std * std_price
        lower_band = mean_price - self.num_std * std_price
        
        # Check position relative to bands
        if price <= lower_band:
            # Oversold, buy
            action = 'BUY'
            distance = (lower_band - price) / lower_band
            confidence = min(0.5 + distance * 5, 0.9)
            reason = f"Price {price:.2f} at lower band {lower_band:.2f}"
        elif price >= upper_band:
            # Overbought, sell
            action = 'SELL'
            distance = (price - upper_band) / upper_band
            confidence = min(0.5 + distance * 5, 0.9)
            reason = f"Price {price:.2f} at upper band {upper_band:.2f}"
        else:
            return None
        
        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'UNKNOWN'),
            action=action,
            confidence=confidence,
            size=100,
            reason=reason,
            agent_name=self.name,
            price=price
        )
