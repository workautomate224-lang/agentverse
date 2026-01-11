#!/bin/bash
set -e
# Force rebuild: 20260111_160000 - add visible queue echo for debugging

echo "=== AgentVerse Celery Worker Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Boot ID will be registered on worker_ready signal"
echo "QUEUES: celery,default,runs,maintenance,legacy"
echo "BUILD_TIMESTAMP: 20260111_160000"

# Start the Celery worker with embedded Beat scheduler
# -B enables beat for periodic tasks (heartbeat, cleanup, etc.)
# Listen on all queues: default, runs, maintenance, legacy
exec celery -A app.worker worker \
    --loglevel=info \
    --concurrency=${CELERY_CONCURRENCY:-4} \
    --queues=celery,default,runs,maintenance,legacy \
    -B
