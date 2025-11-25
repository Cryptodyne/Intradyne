#!/bin/bash
# Docker entrypoint script

set -e

echo "🚀 Starting Intradyne Trading System"
echo "===================================="

# Create directories if they don't exist
mkdir -p data/logs data/cache config

# Check environment
echo "Environment: ${ENVIRONMENT:-development}"
echo "Exchange: ${EXCHANGE_NAME:-bitget}"

# Wait for dependencies
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis..."
    until nc -z "$REDIS_HOST" 6379; do
        sleep 1
    done
    echo "✅ Redis ready"
fi

if [ -n "$POSTGRES_HOST" ]; then
    echo "Waiting for PostgreSQL..."
    until nc -z "$POSTGRES_HOST" 5432; do
        sleep 1
    done
    echo "✅ PostgreSQL ready"
fi

# Run database migrations if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    # Add migration commands here
fi

# Start application
echo "Starting application..."
exec "$@"
