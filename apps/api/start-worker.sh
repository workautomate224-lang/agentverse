#!/bin/bash
set -e

echo "=== AgentVerse Celery Worker Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Boot ID will be registered on worker_ready signal"

# Start the Celery worker
exec celery -A app.worker worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-4}
