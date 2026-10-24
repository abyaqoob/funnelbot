# Multi-stage, zero-budget, lightweight Dockerfile
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_DIR=/app

WORKDIR ${APP_DIR}

# Install system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create a non-privileged system user for secure production execution
RUN groupadd -r appuser && useradd -r -g appuser -d ${APP_DIR} -s /sbin/nologin appuser

# Copy application files and seed data
COPY app/ app/
COPY scripts/ scripts/
COPY pyproject.toml .

# Create database and logs directories with correct permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose standard web service port
EXPOSE 8000

# Container healthcheck targeting the FastAPI /health diagnostic endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch production ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
