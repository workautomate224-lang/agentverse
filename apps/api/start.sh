#!/bin/bash
set -e

echo "=== AgentVerse API Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Running database migrations..."

# Run migrations
alembic upgrade head

echo "Migrations complete. Starting API server..."

# Start the API
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
