#!/bin/bash

echo "=== AgentVerse API Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"

# Function to wait for database to be ready
wait_for_db() {
    local max_attempts=30
    local attempt=1
    local wait_seconds=2

    echo "Waiting for database to be ready..."
    while [ $attempt -le $max_attempts ]; do
        # Try a simple connection using Python
        if python -c "
import os
import psycopg2
from urllib.parse import urlparse
url = os.environ.get('DATABASE_URL', '').replace('+asyncpg', '')
if not url:
    exit(1)
parsed = urlparse(url)
try:
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.path[1:],
        connect_timeout=5
    )
    conn.close()
    exit(0)
except Exception as e:
    print(f'DB not ready: {e}')
    exit(1)
" 2>/dev/null; then
            echo "Database is ready!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Database not ready, waiting ${wait_seconds}s..."
        sleep $wait_seconds
        attempt=$((attempt + 1))
    done

    echo "WARNING: Database did not become ready after $max_attempts attempts"
    return 1
}

# Run migrations if SKIP_MIGRATIONS is not set
if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    # Wait for database before running migrations
    if wait_for_db; then
        echo "Running database migrations..."
        if alembic upgrade head; then
            echo "Migrations completed successfully."
        else
            echo "WARNING: Migrations failed. Check logs for details."
            echo "Continuing with API startup..."
        fi
    else
        echo "WARNING: Skipping migrations - database not available"
    fi
else
    echo "Skipping migrations (SKIP_MIGRATIONS=true)"
fi

echo "Starting API server..."

# Start the API
# --proxy-headers and --forwarded-allow-ips are required for Railway's edge proxy
# so FastAPI generates correct HTTPS redirect URLs instead of HTTP
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
