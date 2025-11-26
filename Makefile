.PHONY: proto docker-build docker-up docker-down test clean help

# Generate gRPC code from protobuf definitions
proto:
	@echo "Generating gRPC code..."
	cd proto && ./generate.sh

# Build all Docker images
docker-build:
	@echo "Building Docker images..."
	docker-compose build

# Start all services
docker-up:
	@echo "Starting SignalOps services..."
	docker-compose up -d
	@echo "Services running:"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Go API: http://localhost:8080"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"

# Stop all services
docker-down:
	@echo "Stopping services..."
	docker-compose down

# Stop and remove volumes
docker-clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v

# Run Python tests
test-python:
	cd python-strategy-engine && python -m pytest tests/

# Run Go tests
test-go:
	cd go-execution-core && go test ./...

# Run all tests
test: test-python test-go

# Clean generated files
clean:
	rm -rf python-strategy-engine/grpc_generated
	rm -rf go-execution-core/pb
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Install Python dependencies
install-python:
	pip install -r requirements.txt

# Install Go dependencies
install-go:
	cd go-execution-core && go mod download

# Full setup
setup: install-python install-go proto
	@echo "Setup complete!"

# Show logs
logs:
	docker-compose logs -f

# Show logs for specific service
logs-python:
	docker-compose logs -f python-strategy

logs-go:
	docker-compose logs -f go-execution

logs-postgres:
	docker-compose logs -f postgres

# Help
help:
	@echo "SignalOps Makefile Commands:"
	@echo ""
	@echo "  make proto          - Generate gRPC code from protobuf"
	@echo "  make docker-build   - Build all Docker images"
	@echo "  make docker-up      - Start all services"
	@echo "  make docker-down    - Stop all services"
	@echo "  make docker-clean   - Stop and remove all volumes"
	@echo "  make test           - Run all tests"
	@echo "  make setup          - Install dependencies and generate code"
	@echo "  make logs           - Show all logs"
	@echo "  make clean          - Clean generated files"
	@echo "  make help           - Show this help message"
