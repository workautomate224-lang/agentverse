#!/bin/bash
set -e

echo "=== AgentVerse Celery Worker Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Boot ID will be registered on worker_ready signal"

# Start the Celery worker with embedded Beat scheduler
# -B enables beat for periodic tasks (heartbeat, cleanup, etc.)
# Listen on all queues: default, runs, maintenance, legacy
exec celery -A app.worker worker \
    --loglevel=info \
    --concurrency=${CELERY_CONCURRENCY:-4} \
    --queues=celery,default,runs,maintenance,legacy \
    -B
