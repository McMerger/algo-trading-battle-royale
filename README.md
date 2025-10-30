# Algo Trading Battle Royale

A multi-agent algorithmic trading system that runs multiple strategies against each other using live market data. The system picks the best-performing strategies in real time and can swap them out without restarting.

## How It Works

This project is built around the idea of having multiple trading strategies compete head-to-head:

- Multiple strategies run at the same time against real market feeds
- A reinforcement learning algorithm tracks performance and picks which strategies to use
- Strategies can be hot-swapped at runtime without taking the system down
- Each trade comes with an explanation of why the strategy made that decision, including confidence levels and relevant market conditions

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Python Strategy │───▶│   Go Execution   │───▶│ K8s Cloud Deploy│
│    Engine       │    │      Core        │    │   (AWS EKS)     │
│                 │    │                  │    │                 │
│ • ML Models     │    │ • Real-time API  │    │ • Auto-scaling  │
│ • Agent Battles │    │ • Order Engine   │    │ • Failover      │
│ • NLP Features  │    │ • Live Feeds     │    │ • Monitoring    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

The system has three main parts:
- Python handles the strategy logic and machine learning
- Go handles order execution and market data feeds
- Kubernetes handles deployment on AWS with auto-scaling

## Repository Structure

### `/python-strategy-engine/`

The strategy and research code:
- Different trading strategies (trend following, arbitrage, momentum-based)
- Framework for running multiple agents and tracking their performance
- ML models for predicting market movements
- News processing and order book analysis
- Performance tracking and strategy selection logic

### `/go-execution-core/`

The execution engine:
- Fast order execution written in Go
- REST and gRPC APIs for connecting to Python strategies
- Market data ingestion using goroutines
- Simulated latency and realistic order fills for testing
- Order management and risk limits

### `/k8s-deploy/`

Deployment configuration:
- Helm charts for deploying services
- AWS EKS setup with auto-scaling policies
- Service mesh configuration
- Monitoring and logging setup
- CI/CD pipelines

### `/dashboard/`

Visualization interface:
- Real-time view of strategy competition
- Performance metrics and win/loss records
