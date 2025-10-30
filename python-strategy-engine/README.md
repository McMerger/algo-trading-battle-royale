# Python Strategy Engine

## Research & Strategy Layer

This module contains the core trading strategies and machine learning components for the agentic trading competition system.

### Key Components

- **Multi-Agent Competition Framework**: Live ranking and strategy battles
- **Modular Trading Strategies**: Trend following, arbitrage, momentum
- **ML Models**: Market prediction and feature engineering
- **News NLP Processing**: Sentiment analysis and market impact
- **Order Book Analysis**: Imbalance detection and microstructure
- **Agent Performance Tracking**: Dynamic selection algorithms

### Features

- Real-time strategy performance monitoring
- Multi-armed bandit selection algorithms
- Runtime hot-swapping of trading agents
- Explainable AI trade decisions
- Market regime detection and adaptation

### Quick Start

```bash
cd python-strategy-engine
pip install -r requirements.txt
python run_demo.py
```

### Architecture

The engine supports multiple concurrent trading agents that compete in real-time using live market data. Winners are selected dynamically based on performance metrics and market conditions.
