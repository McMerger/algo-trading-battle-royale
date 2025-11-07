"""
Event-driven trading agent using prediction market probabilities.
"""

from typing import Dict, Optional
from agents.base_agent import BaseAgent, Signal


class EventDrivenAgent(BaseAgent):
    """
    Strategy:
    - Monitor key event markets (Fed rates, elections, macro)
    - Detect probability shifts (regime changes)
    - Execute trades when odds cross thresholds
    """
    
    def __init__(self, name="EventDrivenAgent", 
                 fed_threshold=0.70,
                 shift_threshold=0.15):
        super().__init__(name)
        
        # Decision thresholds
        self.fed_threshold = fed_threshold  # 70% Fed hike odds = risk-off
        self.shift_threshold = shift_threshold  # 15% probability shift = regime change
        
        # Track previous probabilities to detect shifts
        self.prev_probs = {}
    
    def generate_signal(self, market_data, event_data=None):
        """
        Generate signal using both market and event data.
        
        event_data format:
        {
            'fed_hike': {
                'yes_probability': 0.72,
                'source': 'kalshi',
                'title': 'Fed Rate Hike Dec 2025'
            },
            ...
        }
        """
        if not event_data:
            return None
        
        action = 'HOLD'
        confidence = 0.5
        reason = "No significant event triggers"
        
        # Check Fed hike probability
        if 'fed_hike' in event_data:
            fed = event_data['fed_hike']
            prob = fed.get('yes_probability', 0.5)
            prev_prob = self.prev_probs.get('fed_hike', prob)
            shift = abs(prob - prev_prob)
            
            # High probability = risk off
            if prob > self.fed_threshold:
                action = 'SELL'
                confidence = prob
                reason = (f"Fed hike at {prob:.1%} (threshold {self.fed_threshold:.1%}). "
                         f"Rate-sensitive positioning. Source: {fed.get('source', 'unknown')}")
            
            # Large probability shift = regime change
            elif shift > self.shift_threshold:
                action = 'SELL' if prob > prev_prob else 'BUY'
                confidence = 0.6 + shift
                reason = (f"Fed odds shifted {shift:.1%} "
                         f"({prev_prob:.1%} → {prob:.1%}). Regime change detected.")
            
            self.prev_probs['fed_hike'] = prob
        
        # Check other events for regime shifts
        for event_name, event in event_data.items():
            if event_name == 'fed_hike':
                continue
            
            prob = event.get('yes_probability', 0.5)
            prev = self.prev_probs.get(event_name, prob)
            shift = abs(prob - prev)
            
            if shift > self.shift_threshold:
                # Override action if shift is significant
                action = 'BUY' if prob > prev else 'SELL'
                confidence = max(confidence, 0.7)
                reason += f" | {event_name}: {shift:.1%} shift"
            
            self.prev_probs[event_name] = prob
        
        if action == 'HOLD':
            return None
        
        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'UNKNOWN'),
            action=action,
            confidence=confidence,
            size=100,
            reason=reason,
            agent_name=self.name,
            price=market_data.get('price', 0)
        )


class FedHikeAgent(BaseAgent):
    """
    Specialized agent focused only on Fed rate decisions.
    Simpler, more focused strategy than general event-driven.
    """
    
    def __init__(self, name="FedHikeAgent", hike_threshold=0.65):
        super().__init__(name)
        self.hike_threshold = hike_threshold
        self.last_prob = 0.5
    
    def generate_signal(self, market_data, event_data=None):
        """Trade based purely on Fed hike odds."""
        if not event_data or 'fed_hike' not in event_data:
            return None
        
        fed = event_data['fed_hike']
        prob = fed.get('yes_probability', 0.5)
        
        # Simple logic: high probability = sell, low = buy
        if prob > self.hike_threshold and self.last_prob <= self.hike_threshold:
            # Crossed threshold upward
            action = 'SELL'
            confidence = prob
            reason = f"Fed hike odds crossed {self.hike_threshold:.1%} threshold (now {prob:.1%})"
        elif prob < self.hike_threshold and self.last_prob >= self.hike_threshold:
            # Crossed threshold downward
            action = 'BUY'
            confidence = 1 - prob
            reason = f"Fed hike odds fell below {self.hike_threshold:.1%} (now {prob:.1%})"
        else:
            self.last_prob = prob
            return None
        
        self.last_prob = prob
        
        return Signal(
            timestamp=market_data.get('timestamp', 0),
            symbol=market_data.get('symbol', 'UNKNOWN'),
            action=action,
            confidence=confidence,
            size=100,
            reason=reason,
            agent_name=self.name,
            price=market_data.get('price', 0)
        )
