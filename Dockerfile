# AI Evaluation Engine - Main Application Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
COPY README.md ./

# Install the package and dependencies
RUN pip install --no-cache-dir -e ".[dev,api,testing,tasks]"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/results /app/logs /app/cache

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8000 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import lm_eval; import evaluation_engine; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "lm_eval", "--help"]