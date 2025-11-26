#!/bin/bash
# Database Verification Script
# Queries the PostgreSQL database to verify order persistence

echo "========================================"
echo "SignalOps Database Verification"
echo "========================================"
echo ""

# Check if Docker is running
echo "Checking Docker services..."
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "✗ PostgreSQL container is not running"
    echo "Start services with: docker-compose up -d"
    exit 1
fi

echo "✓ PostgreSQL is running"
echo ""

# Query recent trades
echo "========================================"
echo "Recent Trades (Last 10)"
echo "========================================"
echo ""

docker exec -it signalops-postgres psql -U signalops -d signalops -c \
"SELECT order_id, strategy_name, symbol, side, quantity, executed_price, status, exchange, created_at 
FROM trades 
ORDER BY created_at DESC 
LIMIT 10;"

echo ""

# Query trade statistics
echo "========================================"
echo "Trade Statistics"
echo "========================================"
echo ""

docker exec -it signalops-postgres psql -U signalops -d signalops -c \
"SELECT 
    COUNT(*) as total_trades,
    COUNT(DISTINCT strategy_name) as strategies_used,
    COUNT(DISTINCT symbol) as symbols_traded,
    SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_orders,
    SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_orders,
    SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) as filled_orders
FROM trades;"

echo ""

# Query by strategy
echo "========================================"
echo "Trades by Strategy"
echo "========================================"
echo ""

docker exec -it signalops-postgres psql -U signalops -d signalops -c \
"SELECT strategy_name, COUNT(*) as trade_count, AVG(executed_price) as avg_price 
FROM trades 
GROUP BY strategy_name;"

echo ""

# Query by symbol
echo "========================================"
echo "Trades by Symbol"
echo "========================================"
echo ""

docker exec -it signalops-postgres psql -U signalops -d signalops -c \
"SELECT symbol, side, COUNT(*) as count, SUM(quantity) as total_quantity 
FROM trades 
GROUP BY symbol, side 
ORDER BY symbol, side;"

echo ""
echo "========================================"
echo "Database Check Complete"
echo "========================================"
echo ""
echo "To run custom queries:"
echo "docker exec -it signalops-postgres psql -U signalops -d signalops"
echo ""
