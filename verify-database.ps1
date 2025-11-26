# Database Verification Script
# Queries the PostgreSQL database to verify order persistence

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SignalOps Database Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker services..." -ForegroundColor Yellow
$postgresRunning = docker-compose ps postgres | Select-String "Up"

if (-not $postgresRunning) {
    Write-Host "✗ PostgreSQL container is not running" -ForegroundColor Red
    Write-Host "Start services with: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ PostgreSQL is running" -ForegroundColor Green
Write-Host ""

# Query recent trades
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Recent Trades (Last 10)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$query = "SELECT order_id, strategy_name, symbol, side, quantity, executed_price, status, exchange, created_at FROM trades ORDER BY created_at DESC LIMIT 10;"

docker exec -it signalops-postgres psql -U signalops -d signalops -c $query

Write-Host ""

# Query trade statistics
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Trade Statistics" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$statsQuery = @"
SELECT 
    COUNT(*) as total_trades,
    COUNT(DISTINCT strategy_name) as strategies_used,
    COUNT(DISTINCT symbol) as symbols_traded,
    SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_orders,
    SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_orders,
    SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) as filled_orders
FROM trades;
"@

docker exec -it signalops-postgres psql -U signalops -d signalops -c $statsQuery

Write-Host ""

# Query by strategy
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Trades by Strategy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$strategyQuery = "SELECT strategy_name, COUNT(*) as trade_count, AVG(executed_price) as avg_price FROM trades GROUP BY strategy_name;"

docker exec -it signalops-postgres psql -U signalops -d signalops -c $strategyQuery

Write-Host ""

# Query by symbol
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Trades by Symbol" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$symbolQuery = "SELECT symbol, side, COUNT(*) as count, SUM(quantity) as total_quantity FROM trades GROUP BY symbol, side ORDER BY symbol, side;"

docker exec -it signalops-postgres psql -U signalops -d signalops -c $symbolQuery

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Database Check Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run custom queries:" -ForegroundColor Yellow
Write-Host "docker exec -it signalops-postgres psql -U signalops -d signalops" -ForegroundColor Cyan
Write-Host ""
