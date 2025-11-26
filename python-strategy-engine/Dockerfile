FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for production
RUN pip install --no-cache-dir \
    grpcio==1.60.0 \
    grpcio-tools==1.60.0 \
    psycopg2-binary==2.9.9 \
    redis==5.0.1 \
    pyyaml==6.0.1

# Copy application code
COPY python-strategy-engine/ /app/

# Create logs directory
RUN mkdir -p /app/logs

# Expose gRPC and REST ports
EXPOSE 50051 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command (can be overridden)
# Note: Currently runs demo in test mode. TODO: Implement proper gRPC server
CMD ["python", "strategy-engine.py", "--mode", "test", "--mock"]
