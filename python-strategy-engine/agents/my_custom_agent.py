from agents.base_agent import BaseAgent, Signal

class MyCustomAgent(BaseAgent):
    def generate_signal(self, market_data):
        # Example: implements a random walk agent
        import random
        action = random.choice(['BUY', 'SELL', 'HOLD'])
        return Signal(
            timestamp=market_data.get("timestamp", 0),
            symbol=market_data.get("symbol", "UNKNOWN"),
            action=action,
            confidence=0.7,
            size=100,
            reason="Random walk test",
            agent_name=self.name,
            price=market_data.get("price", 0)
        )
