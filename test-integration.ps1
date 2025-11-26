# SignalOps Docker Build and Test Script
# This script builds and tests the SignalOps backend integration

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SignalOps Backend Integration Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is available
Write-Host "Checking Docker availability..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 1: Building Docker Images" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Build Python strategy engine
Write-Host "Building Python Strategy Engine..." -ForegroundColor Yellow
docker-compose build python-strategy
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Python build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python Strategy Engine built successfully" -ForegroundColor Green

Write-Host ""

# Build Go execution engine (this will generate protobuf code)
Write-Host "Building Go Execution Engine (generating protobuf code)..." -ForegroundColor Yellow
docker-compose build go-execution
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Go build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Go Execution Engine built successfully" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 2: Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start all services
Write-Host "Starting all services..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start services!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Services started" -ForegroundColor Green
Write-Host ""

# Wait for services to be ready
Write-Host "Waiting for services to initialize (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 3: Service Health Checks" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check PostgreSQL
Write-Host "Checking PostgreSQL..." -ForegroundColor Yellow
$pgStatus = docker-compose ps postgres | Select-String "healthy"
if ($pgStatus) {
    Write-Host "✓ PostgreSQL is healthy" -ForegroundColor Green
}
else {
    Write-Host "✗ PostgreSQL is not healthy" -ForegroundColor Red
}

# Check Redis
Write-Host "Checking Redis..." -ForegroundColor Yellow
$redisStatus = docker-compose ps redis | Select-String "healthy"
if ($redisStatus) {
    Write-Host "✓ Redis is healthy" -ForegroundColor Green
}
else {
    Write-Host "✗ Redis is not healthy" -ForegroundColor Red
}

# Check Python service
Write-Host "Checking Python Strategy Engine..." -ForegroundColor Yellow
$pythonStatus = docker-compose ps python-strategy | Select-String "Up"
if ($pythonStatus) {
    Write-Host "✓ Python Strategy Engine is running" -ForegroundColor Green
}
else {
    Write-Host "✗ Python Strategy Engine is not running" -ForegroundColor Red
}

# Check Go service
Write-Host "Checking Go Execution Engine..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Go Execution Engine is healthy" -ForegroundColor Green
    }
}
catch {
    Write-Host "✗ Go Execution Engine health check failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 4: Integration Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test Go REST API
Write-Host "Testing Go REST API..." -ForegroundColor Yellow
try {
    $marketData = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/market-data?symbol=BTCUSDT&exchange=binance" -Method Get
    Write-Host "✓ Market data endpoint working" -ForegroundColor Green
    Write-Host "  Symbol: $($marketData.symbol)" -ForegroundColor Gray
    Write-Host "  Price: $($marketData.price)" -ForegroundColor Gray
}
catch {
    Write-Host "✗ Market data endpoint failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test order submission
Write-Host "Testing order submission..." -ForegroundColor Yellow
try {
    $orderRequest = @{
        order_id      = "test-$(Get-Date -Format 'yyyyMMddHHmmss')"
        strategy_name = "GrahamDefensive"
        symbol        = "BTCUSDT"
        side          = "BUY"
        quantity      = 0.001
        order_type    = "MARKET"
        exchange      = "binance"
    } | ConvertTo-Json

    $orderResponse = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/orders" -Method Post -Body $orderRequest -ContentType "application/json"
    Write-Host "✓ Order submission endpoint working" -ForegroundColor Green
    Write-Host "  Order ID: $($orderResponse.order_id)" -ForegroundColor Gray
    Write-Host "  Status: $($orderResponse.status)" -ForegroundColor Gray
}
catch {
    Write-Host "✗ Order submission failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 5: View Logs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Python Strategy Engine logs:" -ForegroundColor Yellow
docker-compose logs --tail=20 python-strategy

Write-Host ""
Write-Host "Go Execution Engine logs:" -ForegroundColor Yellow
docker-compose logs --tail=20 go-execution

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services are running. Access points:" -ForegroundColor Green
Write-Host "  - Go REST API: http://localhost:8080" -ForegroundColor Cyan
Write-Host "  - Go gRPC: localhost:50050" -ForegroundColor Cyan
Write-Host "  - Python gRPC: localhost:50051" -ForegroundColor Cyan
Write-Host "  - Streamlit Dashboard: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "To view logs: docker-compose logs -f [service-name]" -ForegroundColor Yellow
Write-Host "To stop: docker-compose down" -ForegroundColor Yellow
Write-Host ""
