#!/bin/bash
# SignalOps Docker Build and Test Script
# This script builds and tests the SignalOps backend integration

set -e

echo "========================================"
echo "SignalOps Backend Integration Test"
echo "========================================"
echo ""

# Check if Docker is available
echo "Checking Docker availability..."
if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    echo "✓ Docker found: $docker_version"
else
    echo "✗ Docker not found. Please install Docker."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

echo ""
echo "========================================"
echo "Step 1: Building Docker Images"
echo "========================================"
echo ""

# Build Python strategy engine
echo "Building Python Strategy Engine..."
docker-compose build python-strategy
echo "✓ Python Strategy Engine built successfully"

echo ""

# Build Go execution engine (this will generate protobuf code)
echo "Building Go Execution Engine (generating protobuf code)..."
docker-compose build go-execution
echo "✓ Go Execution Engine built successfully"

echo ""
echo "========================================"
echo "Step 2: Starting Services"
echo "========================================"
echo ""

# Start all services
echo "Starting all services..."
docker-compose up -d

echo "✓ Services started"
echo ""

# Wait for services to be ready
echo "Waiting for services to initialize (30 seconds)..."
sleep 30

echo ""
echo "========================================"
echo "Step 3: Service Health Checks"
echo "========================================"
echo ""

# Check PostgreSQL
echo "Checking PostgreSQL..."
if docker-compose ps postgres | grep -q "healthy"; then
    echo "✓ PostgreSQL is healthy"
else
    echo "✗ PostgreSQL is not healthy"
fi

# Check Redis
echo "Checking Redis..."
if docker-compose ps redis | grep -q "healthy"; then
    echo "✓ Redis is healthy"
else
    echo "✗ Redis is not healthy"
fi

# Check Python service
echo "Checking Python Strategy Engine..."
if docker-compose ps python-strategy | grep -q "Up"; then
    echo "✓ Python Strategy Engine is running"
else
    echo "✗ Python Strategy Engine is not running"
fi

# Check Go service
echo "Checking Go Execution Engine..."
if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✓ Go Execution Engine is healthy"
else
    echo "✗ Go Execution Engine health check failed"
fi

echo ""
echo "========================================"
echo "Step 4: Integration Tests"
echo "========================================"
echo ""

# Test Go REST API
echo "Testing Go REST API..."
if response=$(curl -s http://localhost:8080/api/v1/market/binance/BTCUSDT 2>/dev/null); then
    echo "✓ Market data endpoint working"
    echo "$response" | grep -o '"symbol":"[^"]*"' | head -1
    echo "$response" | grep -o '"price":[0-9.]*' | head -1
else
    echo "✗ Market data endpoint failed"
fi

echo ""

# Test order submission
echo "Testing order submission..."
order_id="test-$(date +%s)"
order_json=$(cat <<EOF
{
    "order_id": "$order_id",
    "strategy_name": "GrahamDefensive",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.001,
    "order_type": "MARKET",
    "exchange": "binance"
}
EOF
)

if response=$(curl -s -X POST http://localhost:8080/api/v1/orders \
    -H "Content-Type: application/json" \
    -d "$order_json" 2>/dev/null); then
    echo "✓ Order submission endpoint working"
    echo "$response" | grep -o '"order_id":"[^"]*"' | head -1
    echo "$response" | grep -o '"status":"[^"]*"' | head -1
else
    echo "✗ Order submission failed"
fi

echo ""
echo "========================================"
echo "Step 5: View Logs"
echo "========================================"
echo ""

echo "Python Strategy Engine logs:"
docker-compose logs --tail=20 python-strategy

echo ""
echo "Go Execution Engine logs:"
docker-compose logs --tail=20 go-execution

echo ""
echo "========================================"
echo "Test Complete!"
echo "========================================"
echo ""
echo "Services are running. Access points:"
echo "  - Go REST API: http://localhost:8080"
echo "  - Go gRPC: localhost:50050"
echo "  - Python gRPC: localhost:50051"
echo "  - Streamlit Dashboard: http://localhost:8501"
echo ""
echo "To view logs: docker-compose logs -f [service-name]"
echo "To stop: docker-compose down"
echo ""
