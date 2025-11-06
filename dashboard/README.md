# Dashboard

## Live Trading Battle Interface

This module provides a real-time web interface for visualizing and managing the agentic trading competition system.

### Key Features

- **Real-time Agent Leaderboard**: Live win/loss ratios and performance metrics
- **Strategy Explanations**: LLM-powered trade decision summaries
- **Market Regime Detection**: Automatic strategy adaptation visualization
- **Performance Analytics**: Sharpe ratios, drawdowns, and risk metrics
- **Agent Management**: Interactive strategy hot-swapping controls
- **Live Trading Feed**: Real-time order and execution monitoring

### Dashboard Components

#### Agent Battle Arena
- Live competition visualization with real-time rankings
- Strategy performance heatmaps and comparison charts
- Win/loss streaks and confidence intervals
- Dynamic agent lifecycle management

#### Performance Analytics
- Real-time P&L tracking and portfolio metrics
- Risk management dashboards with exposure limits
- Backtesting comparison with live performance
- Market impact and execution quality analysis

#### Strategy Explanations
- Instant LLM-generated trade rationale
- Confidence scoring and model attribution
- Market condition context and regime classification
- Decision tree visualization for complex strategies

#### Control Panel
- Runtime agent deployment and configuration
- Emergency stop and risk limit controls
- Market data feed monitoring and health checks
- System performance and resource utilization

### Technology Stack

- **Frontend**: Streamlit with real-time WebSocket updates
- **Visualization**: Plotly for interactive charts and graphs
- **Real-time Updates**: WebSocket connections to Go execution engine
- **Data Processing**: Pandas for performance analytics
- **Styling**: Custom CSS for trading-focused UI/UX

### Quick Start

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

### Environment Variables

```bash
export EXECUTION_ENGINE_URL="http://localhost:8080"
export STRATEGY_ENGINE_URL="http://localhost:5000"
export DASHBOARD_PORT="8501"
export UPDATE_INTERVAL_MS="100"
```

### Features Demo

- **Agent Battles**: Watch strategies compete in real-time
- **Explanations**: "TrendFollower won this trade because momentum indicators showed strong bullish divergence with 87% confidence"
- **Hot-Swapping**: Add/remove agents without system restart
- **Regime Detection**: Automatic strategy switching based on market conditions
