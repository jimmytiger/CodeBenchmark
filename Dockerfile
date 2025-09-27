# AI Evaluation Engine - Main Application Dockerfile
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
COPY README.md ./
COPY lm_eval/ ./lm_eval/
COPY evaluation_engine/ ./evaluation_engine/

# Install the package and dependencies
RUN pip install --no-cache-dir -e ".[evaluation_engine,security,api,testing]"

# Production stage
FROM python:3.11-slim as production

# Set metadata labels
LABEL maintainer="AI Evaluation Engine Team" \
      version="${VERSION}" \
      description="AI Evaluation Engine - Extended lm-evaluation-harness" \
      build-date="${BUILD_DATE}" \
      vcs-ref="${VCS_REF}"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/venv/bin:$PATH" \
    EVALUATION_ENGINE_HOME="/app" \
    RESULTS_DIR="/app/results" \
    LOGS_DIR="/app/logs" \
    CACHE_DIR="/app/cache"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Create application directories
RUN mkdir -p /app/results /app/logs /app/cache /app/data \
    && chown -R appuser:appuser /app

# Copy application from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Copy additional configuration files
COPY docker-compose.yml /app/
COPY .env.template /app/.env.template

# Set working directory
WORKDIR /app

# Switch to non-root user
USER appuser

# Create default configuration
RUN cp .env.template .env 2>/dev/null || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import lm_eval; import evaluation_engine; print('Health check passed')" || exit 1

# Expose ports
EXPOSE 8000 8080

# Default command
CMD ["python", "-m", "lm_eval", "--help"]