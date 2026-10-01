# Production Dockerfile for Nova Voice Assistant Backend
FROM python:3.11-slim

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    NOVA_DATA_DIR=/app/server/data \
    PORT=8000

# Install system dependencies (ALSA, libsndfile, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libasound2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and install
COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/server/requirements.txt

# Copy server application code
COPY server/ /app/server/

# Create persistent data directory
RUN mkdir -p /app/server/data

EXPOSE 8000

# Healthcheck targeting /health/ready
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/ready || exit 1

# Controlled worker count (1-2) to ensure SQLite WAL safety with busy_timeout
CMD ["sh", "-c", "python -m uvicorn server.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
