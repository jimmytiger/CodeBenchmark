#!/bin/bash
set -e

# Docker entrypoint script for Multi-Turn Evaluation Engine

# Default values
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_WORKERS="4"
DEFAULT_LOG_LEVEL="info"

# Use environment variables or defaults
HOST=${HOST:-$DEFAULT_HOST}
PORT=${PORT:-$DEFAULT_PORT}
WORKERS=${WORKERS:-$DEFAULT_WORKERS}
LOG_LEVEL=${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}

# Function to wait for database
wait_for_db() {
    echo "Waiting for database connection..."
    
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
        while ! nc -z "$DB_HOST" "$DB_PORT"; do
            echo "Database is unavailable - sleeping"
            sleep 1
        done
        echo "Database is up - continuing"
    else
        echo "No database configuration found - skipping database check"
    fi
}

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis connection..."
    
    if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
        while ! nc -z "$REDIS_HOST" "$REDIS_PORT"; do
            echo "Redis is unavailable - sleeping"
            sleep 1
        done
        echo "Redis is up - continuing"
    else
        echo "No Redis configuration found - skipping Redis check"
    fi
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    python -m EvaluationEngineV1_0.scripts.migrate_db || {
        echo "Database migration failed"
        exit 1
    }
}

# Function to initialize application
initialize_app() {
    echo "Initializing application..."
    
    # Create necessary directories
    mkdir -p /app/results /app/logs /app/cache
    
    # Set permissions
    chmod 755 /app/results /app/logs /app/cache
    
    # Initialize configuration if needed
    if [ ! -f "/app/config/production.yaml" ]; then
        echo "Creating default production configuration..."
        python -c "
from EvaluationEngineV1_0.deployment.production_config import config_manager
config_manager.create_default_config_file('/app/config/production.yaml')
"
    fi
}

# Function to validate configuration
validate_config() {
    echo "Validating configuration..."
    python -c "
from EvaluationEngineV1_0.deployment.production_config import config_manager
try:
    config = config_manager.load_config('/app/config/production.yaml')
    print(f'Configuration valid for environment: {config.environment.value}')
except Exception as e:
    print(f'Configuration validation failed: {e}')
    exit(1)
" || exit 1
}

# Function to start the application server
start_server() {
    echo "Starting Multi-Turn Evaluation Engine server..."
    echo "Host: $HOST"
    echo "Port: $PORT"
    echo "Workers: $WORKERS"
    echo "Log Level: $LOG_LEVEL"
    
    # Start with uvicorn
    exec uvicorn EvaluationEngineV1_0.api.server:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level "$LOG_LEVEL" \
        --access-log \
        --loop uvloop \
        --http httptools
}

# Function to start worker process
start_worker() {
    echo "Starting evaluation worker..."
    exec python -m EvaluationEngineV1_0.cli.worker
}

# Function to start CLI
start_cli() {
    echo "Starting CLI interface..."
    exec python -m EvaluationEngineV1_0.cli.multi_turn_cli "$@"
}

# Function to run tests
run_tests() {
    echo "Running tests..."
    exec python -m pytest EvaluationEngineV1_0/tests/ -v
}

# Function to run benchmarks
run_benchmarks() {
    echo "Running performance benchmarks..."
    exec python EvaluationEngineV1_0/scripts/performance_benchmark.py "$@"
}

# Function to show help
show_help() {
    cat << EOF
Multi-Turn Evaluation Engine Docker Container

Usage: docker run [OPTIONS] IMAGE [COMMAND] [ARGS...]

Commands:
  server          Start the API server (default)
  worker          Start an evaluation worker
  cli             Start the CLI interface
  test            Run the test suite
  benchmark       Run performance benchmarks
  migrate         Run database migrations
  shell           Start an interactive shell
  help            Show this help message

Environment Variables:
  HOST            Server host (default: 0.0.0.0)
  PORT            Server port (default: 8000)
  WORKERS         Number of worker processes (default: 4)
  LOG_LEVEL       Logging level (default: info)
  ENVIRONMENT     Environment (development, staging, production)
  DB_HOST         Database host
  DB_PORT         Database port
  DB_NAME         Database name
  DB_USER         Database username
  DB_PASSWORD     Database password
  REDIS_HOST      Redis host
  REDIS_PORT      Redis port
  SECRET_KEY      Application secret key
  JWT_SECRET      JWT secret key

Examples:
  # Start server
  docker run -p 8000:8000 evaluation-engine

  # Start with custom configuration
  docker run -e HOST=0.0.0.0 -e PORT=9000 -p 9000:9000 evaluation-engine

  # Run CLI
  docker run -it evaluation-engine cli --help

  # Run tests
  docker run evaluation-engine test

  # Run benchmarks
  docker run evaluation-engine benchmark --verbose
EOF
}

# Main execution logic
main() {
    # Parse command
    COMMAND=${1:-server}
    shift || true
    
    case "$COMMAND" in
        server)
            wait_for_db
            wait_for_redis
            initialize_app
            validate_config
            run_migrations
            start_server
            ;;
        worker)
            wait_for_db
            wait_for_redis
            initialize_app
            validate_config
            start_worker
            ;;
        cli)
            initialize_app
            validate_config
            start_cli "$@"
            ;;
        test)
            initialize_app
            run_tests
            ;;
        benchmark)
            initialize_app
            validate_config
            run_benchmarks "$@"
            ;;
        migrate)
            wait_for_db
            initialize_app
            validate_config
            run_migrations
            ;;
        shell)
            exec /bin/bash
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "Unknown command: $COMMAND"
            echo "Run 'help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"