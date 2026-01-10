#!/bin/bash

echo "=== AgentVerse API Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"

# Run migrations if SKIP_MIGRATIONS is not set
if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    echo "Running database migrations..."
    if alembic upgrade head; then
        echo "Migrations completed successfully."
    else
        echo "WARNING: Migrations failed. Check logs for details."
        echo "Continuing with API startup..."
    fi
else
    echo "Skipping migrations (SKIP_MIGRATIONS=true)"
fi

echo "Starting API server..."

# Start the API
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
