# Algo Trading Battle Royale

Multi-agent trading system where strategies compete using real-world event probabilities from prediction markets.

***

## What's Different Here

Most trading systems react to price movements. This one also uses prediction market data from Polymarket—things like Fed rate decision odds, election probabilities, and macro event forecasts.

When Fed hike odds shift from 40% to 75%, that's information worth trading on. This system gives agents access to those probabilities alongside standard market data.

***

## Key Components

**Prediction Market Integration**
- Polymarket adapter for live event probabilities
- Public API, no authentication needed
- Covers Fed decisions, elections, crypto events, macro indicators
- Mock data fallback for offline development

**Meta-Agent Selection**
- Thompson Sampling to learn which agent works best per regime
- Adapts weightings based on realized performance
- Tracks selection history and confidence

**Explainability**
- Every trade includes rationale
- Shows which factors drove each decision
- Event probabilities visible in context
- Optional LLM explanations via Gemini

**Stress Testing**
- Inject volatility spikes, rate shocks, market crashes
- Test agents with shifting event probabilities
- Reports which strategies hold up under pressure

**Tech Stack**
- Python for strategy logic and research
- Go for execution and APIs
- Kubernetes deployment configs
- REST endpoints ready

***

## Quick Start

```bash
git clone https://github.com/McMerger/algo-trading-battle-royale.git
cd algo-trading-battle-royale
pip install -r requirements.txt

cd python-strategy-engine

# Test Polymarket connection
python strategy-engine.py --mode test

# Find current markets
python strategy-engine.py --mode discover

# Run with live data
python strategy-engine.py --mode basic --epochs 30
```

***

## Example Agent

```python
from agents.event_driven_agent import EventDrivenAgent

agent = EventDrivenAgent(
    name="FedWatcher",
    fed_threshold=0.70,
    shift_threshold=0.15
)

signal = agent.generate_signal(market_data, event_data)
# Returns: SELL (72% confidence) - Fed hike probability at 72%
```

***

## Comparison

| Feature | QuantConnect | Freqtrade | This Repo |
|---------|--------------|-----------|-----------|
| Prediction market data | No | No | Yes |
| Meta-agent selection | No | Limited | Thompson Sampling |
| Event attribution | No | No | Yes |
| User agent sandbox | Limited | No | Yes |
| Stress testing | No | No | Yes |
| K8s deployment | Proprietary | No | Helm charts |

***

## Structure

```
python-strategy-engine/
├── agents/                        # Strategy implementations
├── market_data/                   # Polymarket adapter
├── orchestrator/                  # Competition engine
├── scenario_injector.py           # Stress testing
└── strategy-engine.py             # Main script

go-execution-core/                 # Order execution (optional)
k8s-deploy/helm/                   # Kubernetes configs
```

***

## Use Cases

**Research**
- Test event-driven strategies
- Compare against technical analysis baselines
- Validate robustness across market conditions

**Portfolio**
- Show alternative data integration
- Demonstrate system design
- Working code for interviews

**Development**
- Prototype strategies with event context
- Test prediction market signals
- Deploy with included configs

***

## Adding Agents

```python
from agents.base_agent import BaseAgent, Signal

class MyAgent(BaseAgent):
    def generate_signal(self, market_data, event_data=None):
        if event_data and 'btc_100k' in event_data:
            odds = event_data['btc_100k']['yes_probability']
            
            if odds > 0.75:
                return Signal(
                    timestamp=market_data['timestamp'],
                    symbol=market_data['symbol'],
                    action='BUY',
                    confidence=odds,
                    size=100,
                    reason=f"BTC odds at {odds:.1%}",
                    agent_name=self.name,
                    price=market_data['price']
                )
        return None
```

***

## Roadmap

- Web interface for agent testing
- SHAP/LIME explainability
- Historical event data replays
- Multi-asset support
- WebSocket streaming

***

## License

MIT
