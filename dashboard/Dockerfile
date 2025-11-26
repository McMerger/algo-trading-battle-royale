FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    streamlit==1.30.0 \
    pandas==2.1.4 \
    requests==2.31.0 \
    plotly==5.18.0 \
    psycopg2-binary==2.9.9 \
    streamlit-autorefresh==1.0.1 \
    feedparser==6.0.10

# Copy dashboard code
COPY dashboard/ /app/

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
