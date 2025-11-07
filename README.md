# Algo Trading Battle Royale

Multi-agent algorithmic trading system where strategies compete using real-world event probabilities from prediction markets, not just price data.

---

## Core Differentiator

This system integrates prediction market APIs (Kalshi, Polymarket) to let agents trade based on crowd-sourced probabilities for Fed decisions, elections, and macro events. When Fed hike odds jump from 40% to 75%, that's actionable signal before price fully reflects it.

This is how institutional funds use alternative data. Almost no open-source trading repos do this.

---

## What's Inside

**Prediction Market Integration**
- Kalshi adapter for US macro events (Fed rates, economic data)
- Polymarket adapter for broader coverage (crypto, politics, culture)
- Unified feed that enriches standard market data with event probabilities
- Fallback to mock data for offline development

**Meta-Agent with Thompson Sampling**
- Bayesian bandit that learns which sub-agent to trust per regime
- Adaptive weighting based on realized performance
- Visualizes selection confidence over time

**Full Explainability**
- Every trade decision includes human-readable rationale
- Event attribution showing which factors drove each signal
- Optional LLM explanations via Gemini (with rule-based fallback)

**Adversarial Testing**
- Stress test agents with volatility spikes, flash crashes, rate shocks
- Inject historical event probability shifts
- Reports which strategies break and which adapt

**Production Architecture**
- Python for agents, ML, and research
- Go for order execution and APIs
- Kubernetes deployment configs with Helm charts
- REST/WebSocket endpoints ready

---

## Quick Start

```
git clone https://github.com/McMerger/algo-trading-battle-royale.git
cd algo-trading-battle-royale
pip install -r requirements.txt

# Run with mock event data
cd python-strategy-engine
python strategy-engine.py --epochs 30

# Run with real prediction markets
export KALSHI_API_KEY="your_key"
python strategy-engine.py --epochs 30 --use-events
```

---

## Example: Event-Driven Agent

```
from agents.event_driven_agent import EventDrivenAgent

agent = EventDrivenAgent(
    name="FedWatcher",
    fed_threshold=0.70,      # Sell when Fed hike probability > 70%
    shift_threshold=0.15     # Trade on 15%+ probability shifts
)

# Agent receives both price data and event probabilities
signal = agent.generate_signal(market_data, event_data)
```

---

## Comparison

| Feature | QuantConnect | Freqtrade | This Repo |
|---------|--------------|-----------|-----------|
| Prediction market integration | No | No | Yes (core) |
| Meta-agent selection | No | Limited | Thompson Sampling |
| Event attribution | No | No | Yes (SHAP-ready) |
| User agent upload | Limited | No | Sandboxed runtime |
| Adversarial stress testing | No | No | Yes |
| Cloud-native deployment | Yes | No | Kubernetes + Helm |

---

## Structure

```
python-strategy-engine/
├── agents/
│   ├── base_agent.py              # Base class (accepts event_data)
│   ├── event_driven_agent.py      # Trades on prediction market odds
│   ├── meta_bandit_agent.py       # Adaptive agent selection
│   ├── fed_hike_agent.py          # Specialized Fed watcher
│   ├── trend_follower.py          # Classic baseline
│   └── mean_reversion.py          # Classic baseline
├── market_data/
│   └── prediction_market_adapter.py  # Kalshi + Polymarket APIs
├── orchestrator/
│   └── battle_manager.py          # Competition runner with event integration
├── scenario_injector.py           # Regime and event stress testing
└── strategy-engine.py             # Main demo script

go-execution-core/
└── (order routing, risk checks, APIs)

k8s-deploy/
└── helm/                          # Kubernetes deployment configs
```

---

## Architecture Flow

```
Prediction Markets (Kalshi, Polymarket)
    ↓
Event Data Feed (enriches market data)
    ↓
Agent Pool (event-driven + classic strategies)
    ↓
Battle Manager (runs competition, logs rationale)
    ↓
Go Execution Core (optional, for live trading)
```

---

## Use Cases

**Research**
- Test event-driven strategies vs classic technicals
- Backtest with historical event probability data
- Validate robustness across market regimes

**Portfolio/Resume**
- Demonstrate modern alt-data integration
- Show end-to-end system design
- Prove ability to build explainable, production-ready code

**Production**
- Rapid strategy prototyping with event context
- Framework for testing prediction market alpha
- Deployment configs included

---

## Adding Your Own Agent

Create a new file in `agents/`:

```
from agents.base_agent import BaseAgent, Signal

class MyAgent(BaseAgent):
    def generate_signal(self, market_data, event_data=None):
        # Your logic here
        # event_data format:
        # {
        #     'fed_hike': {'yes_probability': 0.72, 'source': 'kalshi'},
        #     'recession': {'yes_probability': 0.30, 'source': 'polymarket'}
        # }
        
        if event_data and 'fed_hike' in event_data:
            fed_prob = event_data['fed_hike']['yes_probability']
            if fed_prob > 0.70:
                return Signal(
                    timestamp=market_data['timestamp'],
                    symbol=market_data['symbol'],
                    action='SELL',
                    confidence=fed_prob,
                    size=100,
                    reason=f"Fed hike probability at {fed_prob:.1%}",
                    agent_name=self.name,
                    price=market_data['price']
                )
        return None
```

Add to competition:
```
from agents.my_agent import MyAgent

agents = [
    EventDrivenAgent("EventDriven"),
    MyAgent("MyStrategy"),
    TrendFollower("Trend")
]
```

---

## Documentation

- [Getting Started](docs/onboarding.md)
- [Prediction Markets Guide](docs/PREDICTION_MARKETS.md)
- [Agent Development](docs/starter_pack/)
- [Kubernetes Deployment](k8s-deploy/README.md)

---

## Roadmap

- Web interface for agent upload and testing
- SHAP/LIME explainability dashboard
- Historical event data replays
- Multi-asset support (stocks, crypto, futures)
- Real-time streaming via WebSocket

---

## Why This Matters

Most open-source trading systems only see prices and volume. Real funds use alternative data: news sentiment, social signals, and prediction markets. This repo shows you can build that too—modular, explainable, and production-ready.

---

## License

MIT
```

***
