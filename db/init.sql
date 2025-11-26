-- SignalOps Database Schema
-- PostgreSQL initialization script

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Trades table: Complete execution history with audit trail
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) UNIQUE NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    executed_price DECIMAL(20, 8),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    exchange VARCHAR(50),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMPTZ,
    pnl DECIMAL(20, 8),
    fees DECIMAL(20, 8) DEFAULT 0,
    slippage DECIMAL(20, 8),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trades_strategy ON trades(strategy_name);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_timestamp ON trades(timestamp DESC);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_metadata ON trades USING GIN(metadata);

-- Positions table: Current holdings and unrealized PnL
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    strategy_name VARCHAR(100) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    average_entry_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_strategy ON positions(strategy_name);

-- Strategies table: Configuration and status
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_executed_at TIMESTAMPTZ,
    total_pnl DECIMAL(20, 8) DEFAULT 0,
    win_rate DECIMAL(5, 4),
    total_trades INTEGER DEFAULT 0,
    metadata JSONB
);

CREATE INDEX idx_strategies_name ON strategies(name);
CREATE INDEX idx_strategies_active ON strategies(is_active);
CREATE INDEX idx_strategies_config ON strategies USING GIN(config);

-- Decision logs table: Full audit trail for every trading decision
CREATE TABLE IF NOT EXISTS decision_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(5, 4),
    triggers_met JSONB NOT NULL,
    market_data JSONB,
    event_data JSONB,
    fundamental_data JSONB,
    onchain_data JSONB,
    news_data JSONB,
    execution_status VARCHAR(20) DEFAULT 'APPROVED',
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_decision_logs_timestamp ON decision_logs(timestamp DESC);
CREATE INDEX idx_decision_logs_strategy ON decision_logs(strategy_name);
CREATE INDEX idx_decision_logs_symbol ON decision_logs(symbol);
CREATE INDEX idx_decision_logs_decision ON decision_logs(decision);
CREATE INDEX idx_decision_logs_triggers ON decision_logs USING GIN(triggers_met);

-- Market data snapshots table: Time-series for backtesting
CREATE TABLE IF NOT EXISTS market_data_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    source VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_market_snapshots_symbol_time ON market_data_snapshots(symbol, timestamp DESC);
CREATE INDEX idx_market_snapshots_source ON market_data_snapshots(source);
CREATE INDEX idx_market_snapshots_data ON market_data_snapshots USING GIN(data);

-- Risk events table: Track risk manager decisions
CREATE TABLE IF NOT EXISTS risk_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    strategy_name VARCHAR(100),
    symbol VARCHAR(20),
    description TEXT NOT NULL,
    data JSONB,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_risk_events_timestamp ON risk_events(timestamp DESC);
CREATE INDEX idx_risk_events_severity ON risk_events(severity);
CREATE INDEX idx_risk_events_resolved ON risk_events(resolved);

-- Performance metrics table: Aggregated strategy performance
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_name VARCHAR(100) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    total_pnl DECIMAL(20, 8) NOT NULL,
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    win_rate DECIMAL(5, 4),
    total_trades INTEGER NOT NULL,
    avg_trade_duration INTERVAL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_perf_metrics_strategy ON performance_metrics(strategy_name);
CREATE INDEX idx_perf_metrics_period ON performance_metrics(period_start, period_end);

-- API keys table: Encrypted storage for exchange credentials
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange VARCHAR(50) NOT NULL,
    key_name VARCHAR(100) NOT NULL,
    encrypted_key TEXT NOT NULL,
    encrypted_secret TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    UNIQUE(exchange, key_name)
);

CREATE INDEX idx_api_keys_exchange ON api_keys(exchange);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample strategy for testing
INSERT INTO strategies (name, description, config, is_active) VALUES (
    'GrahamDefensive',
    'Graham Value + Event Filter: Buy undervalued stocks when macro risk is low',
    '{
        "rules": [
            {
                "id": "value_screen",
                "source": "fundamental",
                "conditions": [
                    {"metric": "price_to_book", "operator": "<", "threshold": 1.5},
                    {"metric": "ncav_ratio", "operator": "<", "threshold": 0.67}
                ]
            },
            {
                "id": "macro_filter",
                "source": "polymarket",
                "conditions": [
                    {"market": "us_recession_2025", "operator": "<", "threshold": 0.25},
                    {"market": "major_conflict_2025", "operator": "<", "threshold": 0.15}
                ]
            },
            {
                "id": "technical_confirm",
                "source": "technical",
                "conditions": [
                    {"metric": "rsi_14", "operator": "<", "threshold": 35}
                ]
            }
        ],
        "execution": {
            "require_confirmations": 2,
            "position_size": 0.02,
            "action_mode": "notify"
        }
    }'::jsonb,
    true
) ON CONFLICT (name) DO NOTHING;

-- Grant permissions (for development)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO signalops;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO signalops;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'SignalOps database schema initialized successfully';
END $$;
