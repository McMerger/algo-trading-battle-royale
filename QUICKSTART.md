# SignalOps Quick Start Guide

Get SignalOps running in under 5 minutes with Docker Compose.

> **📢 Note:** We are actively migrating to a production-grade Next.js frontend (see [implementation_plan.md](implementation_plan.md)). The current Streamlit dashboard is fully functional and production-ready.

## Prerequisites

- **Docker** & **Docker Compose** installed ([Get Docker](https://docs.docker.com/get-docker/))
- **Python 3.11+** (for local development)
- **Go 1.21+** (optional, for Go development)

## 🚀 One-Command Startup (Recommended)

```bash
# Clone the repository
git clone https://github.com/McMerger/signal-ops.git
cd signal-ops

# Copy environment template
cp .env.example .env

# Start all services
docker-compose up --build
```

**That's it!** SignalOps is now running with:
- PostgreSQL (port 5432) - Trade history database
- Redis (port 6379) - Real-time cache
- Python Strategy Engine (port 50051) - Multi-source intelligence
- Go Execution Engine (port 8080) - Order routing
- Streamlit Dashboard (port 8501) - Web UI

## Access the Services

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:8501 | Real-time trade feed and leaderboard |
| **Go API** | http://localhost:8080 | REST API for order submission |
| **Python gRPC** | localhost:50051 | Strategy evaluation service |
| **PostgreSQL** | localhost:5432 | Database (user: signalops, pass: signalops_dev_password) |
| **Redis** | localhost:6379 | Cache and pub/sub |

## 📊 Run Your First Strategy

### Option 1: Test Polymarket Integration

```bash
cd python-strategy-engine
python strategy-engine.py --mode test
```

Expected output:
```
✓ Connection successful!
Market: Bitcoin above $100k by Jan 1, 2025
YES probability: 45.2%
```

### Option 2: Run Multi-Source Strategy

```bash
# Run Graham Defensive strategy with live Polymarket data
python strategy-engine.py --mode basic --epochs 30
```

This demonstrates the multi-source fusion:
- **Fundamentals**: P/B ratio, NCAV from Yahoo Finance
- **Prediction Markets**: Recession/crisis odds from Polymarket
- **Technical**: RSI, momentum indicators
- **On-Chain**: TVL flows from DeFiLlama

### Option 3: Discover Current Prediction Markets

```bash
python strategy-engine.py --mode discover
```

Find trending Polymarket events you can trade on.

## 🔧 Configuration

### Add Your API Keys (Optional but Recommended)

Edit `.env` file:

```bash
# For live trading (when ready)
BINANCE_API_KEY=your_key_here
COINBASE_API_KEY=your_key_here

# For LLM explanations (optional)
GEMINI_API_KEY=your_gemini_key

# For advanced on-chain data (optional)
DUNE_API_KEY=your_dune_key
```

### Paper Trading Mode (Default)

SignalOps starts in **paper trading mode** by default - no real money at risk.

To enable live trading (when you're ready):
```bash
# In .env
ENABLE_LIVE_TRADING=true
ENABLE_PAPER_TRADING=false
```

## 📈 View Results

### Dashboard

Open http://localhost:8501 to see:
- Live agent leaderboard
- Recent trade decisions
- Multi-source signal explanations

### Database Queries

```bash
# Connect to PostgreSQL
docker exec -it signalops-postgres psql -U signalops

# View recent trades
SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;

# View decision logs (audit trail)
SELECT * FROM decision_logs ORDER BY timestamp DESC LIMIT 5;
```

## 🧪 Test the Multi-Source Intelligence

Run the stress test to see how strategies handle adversarial scenarios:

```bash
python strategy-engine.py --mode stress
```

This tests:
- **Volatility spikes** - Does your strategy panic sell?
- **Flash crashes** - Does it buy into falling knives?
- **Macro shocks** - Does it respect prediction market warnings?

## 📚 Next Steps

### 1. Create Your Own Strategy

Copy the template:

```bash
cp python-strategy-engine/agents/base_agent.py \
   python-strategy-engine/agents/my_strategy.py
```

Edit `my_strategy.py`:

```python
from agents.base_agent import BaseAgent, Signal

class MyStrategy(BaseAgent):
    def generate_signal(self, market_data, event_data=None):
        unified = market_data.get('unified')

        # Access all 5 data sources
        fundamentals = unified.get('fundamentals')
        events = unified.get('events')
        onchain = unified.get('onchain')
        technical = unified.get('technical')

        # Your logic here
        if fundamentals.get('graham_score', 0) > 70:
            return Signal(
                timestamp=market_data['timestamp'],
                symbol=market_data['symbol'],
                action='BUY',
                confidence=0.8,
                size=10000,
                reason="High Graham score",
                agent_name=self.name,
                price=market_data['price']
            )

        return None
```

### 2. Backtest Your Strategy

```bash
# Coming soon: Backtrader integration
python backtest.py --strategy MyStrategy --start 2023-01-01 --end 2024-01-01
```

### 3. Deploy to Production (AWS EKS)

```bash
# Create EKS cluster
eksctl create cluster -f k8s-deploy/cluster-config.yaml

# Deploy services
kubectl apply -f k8s-deploy/

# Verify
kubectl get pods -n signalops
```

## 🐛 Troubleshooting

### Docker Build Fails

```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Port Already in Use

Edit `docker-compose.yml` to change ports:

```yaml
ports:
  - "8501:8501"  # Change first number to different port
```

### Python Dependencies Issue

```bash
# Rebuild Python container
docker-compose build python-strategy
docker-compose up python-strategy
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres
```

## 📖 Documentation

- [Full README](README.md) - Architecture and vision
- [Strategy Guide](docs/strategies.md) - Writing custom strategies
- [API Documentation](docs/api.md) - REST and gRPC endpoints
- [Deployment Guide](docs/deployment.md) - AWS EKS production setup

## 🤝 Community

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Strategy ideas and Q&A
- **Discord**: Coming soon

## ⚠️ Risk Warning

Trading involves risk of loss. SignalOps is provided "as-is" for educational and research purposes. Always start with paper trading and understand the risks before trading with real capital.

---

**Next**: Read the [full README](README.md) to understand the architecture and multi-source intelligence approach.
