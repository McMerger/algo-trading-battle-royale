#!/bin/bash
# SignalOps Quick Start Guide
# Run this script to get started with SignalOps

set -e

echo "========================================"
echo "SignalOps Quick Start"
echo "========================================"
echo ""

echo "This script will help you get SignalOps running."
echo ""

# Check Docker
echo "Step 1: Checking Docker..."
if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    echo "✓ Docker found: $docker_version"
else
    echo "✗ Docker not found!"
    echo ""
    echo "Please install Docker:"
    echo "https://docs.docker.com/get-docker/"
    echo ""
    echo "After installing Docker, run this script again."
    exit 1
fi

echo ""

# Check environment file
echo "Step 2: Checking environment configuration..."
if [ -f ".env" ]; then
    echo "✓ .env file exists"
else
    echo "! .env file not found, copying from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "IMPORTANT: Edit .env and add your API keys:"
    echo "  - BINANCE_API_KEY"
    echo "  - BINANCE_SECRET_KEY"
    echo "  - GEMINI_API_KEY (optional)"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit and edit .env first"
fi

echo ""

# Build services
echo "Step 3: Building Docker images..."
echo "This may take 5-10 minutes on first run..."
echo ""

docker-compose build

echo "✓ Build complete!"
echo ""

# Start services
echo "Step 4: Starting services..."
docker-compose up -d

echo "✓ Services started!"
echo ""

# Wait for initialization
echo "Waiting for services to initialize (30 seconds)..."
sleep 30

echo ""
echo "========================================"
echo "SignalOps is Ready!"
echo "========================================"
echo ""

echo "Access Points:"
echo "  • Go REST API:         http://localhost:8080"
echo "  • Go Health Check:     http://localhost:8080/health"
echo "  • Streamlit Dashboard: http://localhost:8501"
echo "  • Python gRPC:         localhost:50051"
echo "  • Go gRPC:             localhost:50050"
echo ""

echo "Useful Commands:"
echo "  • View logs:          docker-compose logs -f [service-name]"
echo "  • Stop services:      docker-compose down"
echo "  • Restart services:   docker-compose restart"
echo "  • Run tests:          ./test-integration.sh"
echo "  • Check database:     ./verify-database.sh"
echo ""

echo "Next Steps:"
echo "  1. Open http://localhost:8080/health to verify Go service"
echo "  2. Run ./test-integration.sh to test the system"
echo "  3. Check logs: docker-compose logs -f python-strategy"
echo ""

# Quick health check
echo "Quick Health Check:"
if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✓ Go Execution Engine is healthy"
else
    echo "! Go service may still be starting..."
fi

echo ""
echo "Happy Trading! 🚀"
echo ""
