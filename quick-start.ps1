# SignalOps Quick Start Guide
# Run this script to get started with SignalOps

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SignalOps Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "This script will help you get SignalOps running." -ForegroundColor Yellow
Write-Host ""

# Check Docker
Write-Host "Step 1: Checking Docker..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Docker Desktop:" -ForegroundColor Yellow
    Write-Host "https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "After installing Docker, run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Check environment file
Write-Host "Step 2: Checking environment configuration..." -ForegroundColor Cyan
if (Test-Path ".env") {
    Write-Host "✓ .env file exists" -ForegroundColor Green
}
else {
    Write-Host "! .env file not found, copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ Created .env file" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Edit .env and add your API keys:" -ForegroundColor Yellow
    Write-Host "  - BINANCE_API_KEY" -ForegroundColor Cyan
    Write-Host "  - BINANCE_SECRET_KEY" -ForegroundColor Cyan
    Write-Host "  - GEMINI_API_KEY (optional)" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "Press Enter to continue or Ctrl+C to exit and edit .env first"
}

Write-Host ""

# Build services
Write-Host "Step 3: Building Docker images..." -ForegroundColor Cyan
Write-Host "This may take 5-10 minutes on first run..." -ForegroundColor Yellow
Write-Host ""

docker-compose build

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Build complete!" -ForegroundColor Green
Write-Host ""

# Start services
Write-Host "Step 4: Starting services..." -ForegroundColor Cyan
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start services!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Services started!" -ForegroundColor Green
Write-Host ""

# Wait for initialization
Write-Host "Waiting for services to initialize (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SignalOps is Ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Access Points:" -ForegroundColor Yellow
Write-Host "  • Go REST API:        http://localhost:8080" -ForegroundColor Cyan
Write-Host "  • Go Health Check:    http://localhost:8080/health" -ForegroundColor Cyan
Write-Host "  • Streamlit Dashboard: http://localhost:8501" -ForegroundColor Cyan
Write-Host "  • Python gRPC:        localhost:50051" -ForegroundColor Cyan
Write-Host "  • Go gRPC:            localhost:50050" -ForegroundColor Cyan
Write-Host ""

Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "  • View logs:          docker-compose logs -f [service-name]" -ForegroundColor Cyan
Write-Host "  • Stop services:      docker-compose down" -ForegroundColor Cyan
Write-Host "  • Restart services:   docker-compose restart" -ForegroundColor Cyan
Write-Host "  • Run tests:          .\test-integration.ps1" -ForegroundColor Cyan
Write-Host "  • Check database:     .\verify-database.ps1" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:8080/health to verify Go service" -ForegroundColor Cyan
Write-Host "  2. Run .\test-integration.ps1 to test the system" -ForegroundColor Cyan
Write-Host "  3. Check logs: docker-compose logs -f python-strategy" -ForegroundColor Cyan
Write-Host ""

# Quick health check
Write-Host "Quick Health Check:" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -TimeoutSec 5
    Write-Host "✓ Go Execution Engine: $($health.status)" -ForegroundColor Green
}
catch {
    Write-Host "! Go service may still be starting..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Happy Trading! 🚀" -ForegroundColor Green
Write-Host ""
